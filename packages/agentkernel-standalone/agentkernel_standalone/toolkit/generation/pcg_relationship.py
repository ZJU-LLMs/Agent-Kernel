"""Module for generating relationships between agents."""

import os
import json
import random
import itertools
import numpy as np
from typing import Any, Dict, List, Iterable, Tuple

from .sampling import sample
from ..logger import get_logger

logger = get_logger(__name__)


class RelationshipGenerator:
    """A class for generating relationships between agents."""

    def __init__(
        self,
        profile_path: str,
        relationship_config: Dict[str, Any],
        edge_output_path: str,
        node_output_path: str,
        seed: int | None = None,
    ):
        """
        Initialize the RelationshipGenerator.

        Args:
            profile_path (str): The path to the agent profiles file.
            relationship_config (Dict[str, Any]): The relationship configuration.
            edge_output_path (str): The path to the output file for relationship edges.
            node_output_path (str): The path to the output file for agent nodes.
            seed (Optional[int]): The random seed.
        """
        self.py_rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        self.profile_path = profile_path
        self.edge_output_path = edge_output_path
        self.node_output_path = node_output_path

        self.config = relationship_config
        self.intra_config = relationship_config["intra_relationship"]
        self.inter_config = relationship_config["inter_relationship"]

    def _sample(self, population: List[Any], k: int) -> List[Any]:
        """
        Sample k elements from a population.

        Args:
            population (List[Any]): The population to sample from.
            k (int): The number of elements to sample.

        Returns:
            List[Any]: A list of k sampled elements.
        """
        if k > len(population):
            raise ValueError("sample larger than population")
        population = list(population)
        self.py_rng.shuffle(population)
        return population[:k]

    def _make_edge(
        self, source: Dict[str, Any], target: Dict[str, Any], rel_type: str, is_directed: bool, strength: float
    ):
        """
        Create a directed or undirected edge between two agents.

        If `is_directed` is False, an undirected edge is represented as two
        directed edges in opposite directions.

        Args:
            source (Dict[str, Any]): The source agent.
            target (Dict[str, Any]): The target agent.
            rel_type (str): The type of the relationship.
            is_directed (bool): Whether the edge is directed.
            strength (float): The strength of the relationship.
        """
        forward_edge = {"target": target["id"], "type": rel_type, "strength": strength}
        source["relationships"].append(forward_edge)

        if not is_directed:
            backward_edge = {"target": source["id"], "type": rel_type, "strength": strength}
            target["relationships"].append(backward_edge)

    def _filter_agents(self, agents: List[Dict[str, Any]], cond: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter a list of agents based on a set of conditions.

        Args:
            agents (List[Dict[str, Any]]): The list of agents to filter.
            cond (Dict[str, Any]): The conditions to filter by.

        Returns:
            List[Dict[str, Any]]: A list of agents that match the conditions.
        """

        def _value_matches(v: Any, cond_value: Any) -> bool:
            if isinstance(cond_value, list):
                return v in cond_value
            else:
                return v == cond_value

        if not cond:
            return list(agents)
        results = []
        for agent in agents:
            ok = True
            for k, expected in cond.items():
                if expected == []:
                    continue
                if k not in agent or not _value_matches(agent.get(k), expected):
                    ok = False
                    break
            if ok:
                results.append(agent)
        return results

    def _group_by_fields(
        self, agents: List[Dict[str, Any]], fields: Iterable[str]
    ) -> Dict[Tuple[Any, ...], List[Dict[str, Any]]]:
        """
        Group agents by a set of fields.

        Args:
            agents (List[Dict[str, Any]]): The list of agents to group.
            fields (Iterable[str]): The fields to group by.

        Returns:
            Dict[Tuple[Any, ...], List[Dict[str, Any]]]: A dictionary mapping field
                values to lists of agents.
        """
        groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
        fields = list(fields)
        if not fields:
            groups[()] = list(agents)
            return groups

        for agent in agents:
            try:
                values_list = []
                for f in fields:
                    v = agent[f]
                    if isinstance(v, list):
                        values_list.append(v)
                    else:
                        values_list.append([v])
            except KeyError:
                continue

            for key in itertools.product(*values_list):
                groups.setdefault(key, []).append(agent)

        return groups

    def _generate_intra_relationship(self, agents: List[Dict[str, Any]]):
        """
        Generate intra-group relationships between agents.

        Args:
            agents (List[Dict[str, Any]]): The list of agents.
        """
        for relationship, rules in self.intra_config.items():
            for rule in rules:
                when = rule.get("when", {})
                proportion = rule.get("proportion", 1.0)
                conn = rule["connection"]
                strength_cfg = rule["strength"]
                group_size_cfg = rule["group_size"]

                filtered = self._filter_agents(agents, when)
                if len(filtered) < 2:
                    continue

                fields = list(when.keys())
                groups_by_key = self._group_by_fields(filtered, fields)

                for key, subgroup in groups_by_key.items():
                    if len(subgroup) < 2:
                        continue
                    n_agents = int(len(subgroup) * proportion)
                    if n_agents < 2:
                        continue
                    pool = self._sample(subgroup, n_agents)

                    remaining = n_agents
                    idx = 0
                    groups = []
                    while remaining > 0:
                        gsize = int(sample(group_size_cfg, py_rng=self.py_rng, np_rng=self.np_rng))
                        gsize = max(1, min(gsize, remaining))
                        groups.append(pool[idx : idx + gsize])
                        idx += gsize
                        remaining -= gsize

                    ctype = conn["type"]
                    if ctype == "clique":
                        for g in groups:
                            for i in range(len(g)):
                                for j in range(i + 1, len(g)):
                                    s = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                    self._make_edge(g[i], g[j], relationship, conn["directed"], s)
                    elif ctype == "random":
                        p_edge = conn.get("params", {}).get("p_edge", 0.1)
                        for g in groups:
                            for i in range(len(g)):
                                for j in range(i + 1, len(g)):
                                    if self.py_rng.random() < p_edge:
                                        s = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                        self._make_edge(g[i], g[j], relationship, conn["directed"], s)
                    elif ctype == "hybrid":
                        params = conn.get("params", {})
                        p_intra = params.get("p_intra", 0.01)
                        p_inter = params.get("p_inter", 0.01)
                        for g in groups:
                            for i in range(len(g)):
                                for j in range(i + 1, len(g)):
                                    if self.py_rng.random() < p_intra:
                                        s = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                        self._make_edge(g[i], g[j], relationship, conn["directed"], s)
                        for i in range(len(groups)):
                            for j in range(i + 1, len(groups)):
                                for a in groups[i]:
                                    for b in groups[j]:
                                        if self.py_rng.random() < p_inter:
                                            s = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                            self._make_edge(a, b, relationship, conn["directed"], s)
                    else:
                        raise ValueError(f"Unknown connection type: {ctype}")

    def _generate_inter_relationship(self, agents: List[Dict[str, Any]]):
        """
        Generate inter-group relationships between agents.

        Args:
            agents (List[Dict[str, Any]]): The list of agents.
        """
        for relationship, rules in self.inter_config.items():
            for rule in rules:
                when = rule.get("when", {})
                src_cond = when.get("source", {}) or {}
                tgt_cond = when.get("target", {}) or {}
                match_fields = list(set(src_cond.keys()).intersection(set(tgt_cond.keys())).difference({"role"}))

                source_pool = self._filter_agents(agents, src_cond)
                target_pool = self._filter_agents(agents, tgt_cond)
                if not source_pool or not target_pool:
                    continue

                proportion = rule.get("proportion", 1.0)
                conn = rule["connection"]
                strength_cfg = rule["strength"]
                group_size_cfg = rule["group_size"]

                if match_fields:
                    target_index = self._group_by_fields(target_pool, match_fields)
                    source_groups = self._group_by_fields(source_pool, match_fields)

                    for key, src_group in source_groups.items():
                        tgt_candidates = target_index.get(key, [])
                        if not tgt_candidates:
                            continue
                        n_src = max(1, int(len(src_group) * proportion))
                        sampled_src = self._sample(src_group, min(n_src, len(src_group)))

                        for s in sampled_src:
                            src_size = int(sample(group_size_cfg["source"], py_rng=self.py_rng, np_rng=self.np_rng))
                            tgt_size = int(sample(group_size_cfg["target"], py_rng=self.py_rng, np_rng=self.np_rng))
                            src_group_act = [s]
                            tgt_group_act = self._sample(tgt_candidates, min(tgt_size, len(tgt_candidates)))

                            ctype = conn["type"]
                            if ctype == "complete_bipartite":
                                for s_ in src_group_act:
                                    for t_ in tgt_group_act:
                                        st = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                        self._make_edge(s_, t_, relationship, conn["directed"], st)
                            elif ctype == "random":
                                p_edge = conn.get("params", {}).get("p_edge", 0.1)
                                for s_ in src_group_act:
                                    for t_ in tgt_group_act:
                                        if self.py_rng.random() < p_edge:
                                            st = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                            self._make_edge(s_, t_, relationship, conn["directed"], st)
                            else:
                                raise ValueError(f"Unknown connection type: {ctype}")
                else:
                    n_links = int(len(source_pool) * proportion)
                    for _ in range(max(1, n_links)):
                        src_size = sample(group_size_cfg["source"], py_rng=self.py_rng, np_rng=self.np_rng)
                        tgt_size = sample(group_size_cfg["target"], py_rng=self.py_rng, np_rng=self.np_rng)
                        src_group = self._sample(source_pool, min(src_size, len(source_pool)))
                        tgt_group = self._sample(target_pool, min(tgt_size, len(target_pool)))

                        ctype = conn["type"]
                        if ctype == "complete_bipartite":
                            for s in src_group:
                                for t in tgt_group:
                                    st = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                    self._make_edge(s, t, relationship, conn["directed"], st)
                        elif ctype == "random":
                            p_edge = conn.get("params", {}).get("p_edge", 0.1)
                            for s in src_group:
                                for t in tgt_group:
                                    if self.py_rng.random() < p_edge:
                                        st = sample(strength_cfg, py_rng=self.py_rng, np_rng=self.np_rng)
                                        self._make_edge(s, t, relationship, conn["directed"], st)
                        else:
                            raise ValueError(f"Unknown connection type: {ctype}")

    async def run(self):
        """Run the relationship generation process."""
        with open(self.profile_path, "r", encoding="utf-8") as f:
            agents = [json.loads(line) for line in f if line.strip()]

        for agent in agents:
            agent["relationships"] = []

        self._generate_intra_relationship(agents)
        self._generate_inter_relationship(agents)

        num_edges = 0
        os.makedirs(os.path.dirname(self.edge_output_path), exist_ok=True)
        with open(self.edge_output_path, "w", encoding="utf-8") as f:
            for agent in agents:
                for relationship in agent["relationships"]:
                    edge = {
                        "source_id": agent["id"],
                        "target_id": relationship["target"],
                        "properties": {k: v for k, v in relationship.items() if k != "target"},
                    }
                    f.write(json.dumps(edge, ensure_ascii=False) + "\n")
                    num_edges += 1

        with open(self.node_output_path, "w", encoding="utf-8") as f:
            for agent in agents:
                node_info = {"id": agent["id"], "role": agent["role"], "description": agent["compressed_description"]}
                f.write(json.dumps(node_info, ensure_ascii=False) + "\n")

        logger.info(f"Save {num_edges} edges to {self.edge_output_path}")
        logger.info(f"Save {len(agents)} nodes to {self.node_output_path}")
