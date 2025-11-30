import asyncio
import itertools
import json
import random
import numpy as np
import re
import os
import csv
from faker import Faker
from tqdm.asyncio import tqdm_asyncio
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque

from .sampling import sample
from ..models.async_router import AsyncModelRouter
from ..logger import get_logger

logger = get_logger(__name__)


class NameGenerator:
    """Abstract base class for name generation strategies."""

    def generate_name(self, gender: str, used_names: set, rng: random.Random) -> str:
        """
        Generate a unique name based on gender.

        Args:
            gender (str): The gender to generate a name for.
            used_names (set): A set of already used names.
            rng (random.Random): A random number generator instance.

        Returns:
            str: A unique name.
        """
        raise NotImplementedError


class PoolNameGenerator(NameGenerator):
    """A name generator that uses a predefined pool of names."""

    def __init__(self, name_pool_path: str):
        """
        Initialize the PoolNameGenerator.

        Args:
            name_pool_path (str): The path to the name pool CSV file.
        """
        self.name_pool = {"male": [], "female": []}
        self._load_name_pool(name_pool_path)

    def _load_name_pool(self, name_pool_path: str):
        """
        Load the name pool from a CSV file.

        The CSV file should have 'name' and 'gender' columns.

        Args:
            name_pool_path (str): The path to the name pool CSV file.
        """
        if not os.path.exists(name_pool_path):
            logger.warning(f"Name pool file {name_pool_path} not found.")
            return

        try:
            with open(name_pool_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("name", "").strip()
                    gender = row.get("gender", "").strip().lower()

                    if not name:
                        continue

                    if gender in ["male", "m", "男", "男性"]:
                        self.name_pool["male"].append(name)
                    elif gender in ["female", "f", "女", "女性"]:
                        self.name_pool["female"].append(name)

            logger.info(
                f"Loaded name pool: {len(self.name_pool['male'])} male names, {len(self.name_pool['female'])} female names"
            )

        except Exception as e:
            logger.warning(f"Failed to load name pool from {name_pool_path}: {e}")
            self.name_pool = {"male": [], "female": []}

    def generate_name(self, gender: str, used_names: set, rng: random.Random) -> str:
        """
        Generate a name from the loaded pool.

        Args:
            gender (str): The gender to generate a name for.
            used_names (set): A set of already used names.
            rng (random.Random): A random number generator instance.

        Returns:
            str: A unique name from the pool, or None if no unique name can be found.
        """
        available_names = []
        if gender == "male" and self.name_pool["male"]:
            available_names = [name for name in self.name_pool["male"] if name not in used_names]
        elif gender == "female" and self.name_pool["female"]:
            available_names = [name for name in self.name_pool["female"] if name not in used_names]
        elif not gender:
            available_names = [
                name for name in self.name_pool["male"] + self.name_pool["female"] if name not in used_names
            ]

        if available_names:
            return rng.choice(available_names)
        return None


class FakerNameGenerator(NameGenerator):
    """A name generator that uses the Faker library."""

    def __init__(self):
        """Initialize the FakerNameGenerator."""
        self.faker_cn = Faker("zh_CN")
        self.faker_en = Faker("en_US")

    def generate_name(self, gender: str, used_names: set, rng: random.Random) -> str:
        """
        Generate a name using the Faker library.

        Args:
            gender (str): The gender to generate a name for.
            used_names (set): A set of already used names.
            rng (random.Random): A random number generator instance.

        Returns:
            str: A unique name, or None if a unique name cannot be generated.
        """
        is_cn = any("\u4e00" <= ch <= "\u9fff" for ch in str(used_names))
        faker = self.faker_cn if is_cn else self.faker_en

        for _ in range(10000):
            if gender == "male":
                name = faker.name_male()
            elif gender == "female":
                name = faker.name_female()
            else:
                name = faker.name()
            if name not in used_names:
                return name
        return None


class AgentGenerator:
    """A class for generating agent profiles and states."""

    def __init__(
        self,
        llm: AsyncModelRouter,
        agent_config: Dict[str, Any],
        profile_output_path: str,
        state_output_path: str,
        name_pool_path: Optional[str] = None,
        is_incremental: bool = True,
        timeout: int = 60,
        seed: int | None = None,
    ):
        """
        Initialize the AgentGenerator.

        Args:
            llm (AsyncModelRouter): The language model router.
            agent_config (Dict[str, Any]): The agent configuration.
            profile_output_path (str): The path to the output file for agent profiles.
            state_output_path (str): The path to the output file for agent states.
            name_pool_path (Optional[str]): The path to the name pool CSV file.
            is_incremental (bool): Whether to generate agents incrementally.
            timeout (int): The timeout for language model requests.
            seed (Optional[int]): The random seed.
        """
        self.llm = llm
        self.timeout = timeout

        self.py_rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        self.config = agent_config
        self.profile_output_path = profile_output_path
        self.state_output_path = state_output_path
        self.name_pool_path = name_pool_path

        self.used_names = set()

        self._init_name_generator()

        if is_incremental:
            try:
                with open(self.profile_output_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    for line in lines:
                        agent = json.loads(line)
                        self.used_names.add(agent["id"])
                logger.info(
                    f"Load {len(lines)} agents from {self.profile_output_path}, will continue from agent {len(lines) + 1}."
                )
            except FileNotFoundError:
                logger.warning(
                    f"Profile output path {self.profile_output_path} does not exist, will create the new file and start from agent 1."
                )
        else:
            open(self.profile_output_path, "w").close()
            open(self.state_output_path, "w").close()
            logger.info(
                f"The file {self.profile_output_path} and {self.state_output_path} is cleaned, and will start from agent 1."
            )

        self._agent_id_counter = itertools.count(1)

        self.roles_cfg = self.config.get("roles", {})
        self.inter_relationship_cfg = self.config.get("inter_relationship", {})

        self.state = self.config.get("state", {})

    def _init_name_generator(self):
        """Initialize the name generator based on the configuration."""
        if self.name_pool_path and os.path.exists(self.name_pool_path):
            logger.info(f"Using name pool from {self.name_pool_path}")
            self.name_generator = PoolNameGenerator(self.name_pool_path)
        else:
            logger.info("No name pool specified, using Faker for name generation")
            self.name_generator = FakerNameGenerator()

    def _assign_next_agent_id(self):
        """Assign the next agent ID."""
        return f"CHARACTER_{next(self._agent_id_counter):05d}"

    def _topological_sort_attributes(self, profile_cfg: Dict[str, Any]) -> List[str]:
        """
        Return attribute names sorted by dependency order.

        Args:
            profile_cfg (Dict[str, Any]): The profile configuration.

        Returns:
            List[str]: A list of attribute names in topological order.

        Raises:
            ValueError: If a cyclic dependency is detected in the attributes.
        """
        graph = defaultdict(list)
        indegree = defaultdict(int)

        for attr_name in profile_cfg:
            indegree[attr_name] = 0

        for attr_name, cfg in profile_cfg.items():
            based_on = cfg.get("based_on")
            if based_on:
                if isinstance(based_on, str):
                    based_on = [based_on]
                for dep in based_on:
                    graph[dep].append(attr_name)
                    indegree[attr_name] += 1

        queue = deque([n for n, deg in indegree.items() if deg == 0])
        sorted_attrs = []

        while queue:
            node = queue.popleft()
            sorted_attrs.append(node)
            for nei in graph[node]:
                indegree[nei] -= 1
                if indegree[nei] == 0:
                    queue.append(nei)

        if len(sorted_attrs) < len(profile_cfg):
            logger.error(f"queue: {queue}")
            logger.error(f"sorted_attrs: {sorted_attrs}")
            raise ValueError("Cyclic dependency detected in profile attributes")

        return sorted_attrs

    def _initialize_agents(self) -> List[Dict[str, Any]]:
        """
        Initialize the agents based on the configuration.

        Returns:
            List[Dict[str, Any]]: A list of initialized agents.
        """
        agents = []

        for role, role_cfg in self.roles_cfg.items():
            n_agents = role_cfg.get("count", 0)
            if n_agents == 0:
                continue

            profile_cfg = role_cfg.get("profile", {})
            sorted_attr_names = self._topological_sort_attributes(profile_cfg)

            for _ in range(n_agents):
                attrs = {}
                for attr_name in sorted_attr_names:
                    attr_cfg = profile_cfg[attr_name]
                    attrs[attr_name] = sample(attr_cfg, attrs, py_rng=self.py_rng, np_rng=self.np_rng)

                state = {}
                for state_name, state_cfg in self.state.items():
                    state[state_name] = int(sample(state_cfg, py_rng=self.py_rng, np_rng=self.np_rng))

                agent = {
                    "id": self._assign_next_agent_id(),
                    "role": role,
                    "attributes": attrs,
                    "state": state,
                }
                agents.append(agent)

        return agents

    def _clean_message(self, response: str = None) -> Optional[str]:
        """
        Clean the response from the language model.

        Args:
            response (Optional[str]): The response string to clean.

        Returns:
            Optional[str]: The cleaned response string.
        """
        if not response:
            return response

        response = response.split("</think>")[-1].strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[-1]
        if response.endswith("```"):
            response = response.rsplit("\n", 1)[0]
        response = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", response)

        return response.strip()

    async def _generate_basic_info(self, agent: Dict[str, Any], max_retries: int = 3):
        """
        Infer basic information for the agent's profile.

        Args:
            agent (Dict[str, Any]): The agent data.
            max_retries (int): The maximum number of retries for the API call.
        """
        output_format_lines = []
        fields = list(self.config["profile"].items())
        for i, (field_name, spec) in enumerate(fields):
            data_type = spec["data_type"]
            line = f'    "{field_name}": ({data_type})'
            if i < len(fields) - 1:
                line += ","
            if "description" in spec:
                line += f'   // {spec["description"]}'
            output_format_lines.append(line)
        output_format = "{\n" + "\n".join(output_format_lines) + "\n}"

        system_prompt = f"""You are an expert character profiler.
        Based on a character's intrinsic attributes and social relationships,
        INFER a consistent and detailed character profile.

        ## Input format:
        {{
            "world_name": (string),          // environment where the character lives
            "world_description": (string),   // general setting, culture, or background
            "name": (string),                // unique identifier
            "role": (string),                // functional/social role
            "attributes": {{ ... }}          // intrinsic properties
        }}

        ## Output format:
        {output_format}"""

        user_prompt = json.dumps(
            {
                "world_name": self.config["world_name"],
                "world_description": self.config["world_description"],
                "name": agent["id"],
                "role": agent["role"],
                "attributes": agent["attributes"],
            },
            ensure_ascii=False,
        )

        response = None
        for attempt in range(max_retries):
            try:
                response = await self.llm.chat(user_prompt, system_prompt=system_prompt, timeout=self.timeout)
                response = self._clean_message(response)
                profile = json.loads(response)
                agent["profile"] = profile
                return

            except Exception as e:
                logger.warning(f"Failed profile gen for {agent['id']} (retry {attempt}): {e}")
                logger.debug(f"Response: {response}")
                await asyncio.sleep(1)

    async def _compress_description(self, description: str, max_retries: int = 3) -> str | None:
        """
        Condense the agent profile description into a single sentence.

        Args:
            description (str): The long description to compress.
            max_retries (int): The maximum number of retries for the API call.

        Returns:
            Optional[str]: The compressed description, or None on failure.
        """
        system_prompt = """You are an expert editor.
        Given a character description, compress it into a short summary of  **only 1 sentence**,
        while keeping the core traits and motivations.

        ## Input:
        A long description text.

        ## Output:
        A short summary in **only 1 sentence**."""

        response = None
        for attempt in range(max_retries):
            try:
                response = await self.llm.chat(
                    user_prompt=description, system_prompt=system_prompt, timeout=self.timeout
                )
                response = self._clean_message(response)
                return response

            except Exception as e:
                logger.warning(f"Failed description compression (retry {attempt}), text_len={len(description)}: {e}")
                logger.debug(f"Response: {response}")
                await asyncio.sleep(1)

        return None

    def _assign_random_name(self, agent: dict) -> str:
        """
        Assign a unique name based on gender using the configured name generator.

        Args:
            agent (dict): The agent data.

        Returns:
            str: A unique name, or None if a name could not be assigned.
        """
        profile = agent.get("profile")

        gender_raw = str(profile.get("gender") or "").strip().lower()
        cn_map = {"男": "male", "女": "female", "男性": "male", "女性": "female"}
        if gender_raw in cn_map:
            gender = cn_map[gender_raw]
        elif gender_raw in ["m", "male", "man", "boy"]:
            gender = "male"
        elif gender_raw in ["f", "female", "woman", "girl"]:
            gender = "female"
        else:
            gender = None

        name = self.name_generator.generate_name(gender, self.used_names, self.py_rng)
        if name:
            self.used_names.add(name)
            return name

        return None

    def _remove_none_values(self, data: Any) -> Any:
        """
        Recursively remove keys whose value is None from a dictionary or list.

        Args:
            data (Union[Dict, List]): The data to process.

        Returns:
            Union[Dict, List]: The data with None values removed.
        """
        if isinstance(data, dict):
            return {key: self._remove_none_values(value) for key, value in data.items() if value is not None}
        elif isinstance(data, list):
            return [self._remove_none_values(item) for item in data]
        else:
            return data

    async def _generate_profile(self, agent: Dict[str, Any]) -> bool:
        """
        Generate a complete profile for a single agent.

        This includes generating basic info, assigning a name, compressing the
        description, and saving the profile and state to files.

        Args:
            agent (Dict[str, Any]): The agent data.

        Returns:
            bool: True if the profile was generated successfully, False otherwise.
        """
        try:
            await self._generate_basic_info(agent)

            agent["name"] = self._assign_random_name(agent)

            profile = agent.get("profile")
            description = profile.get("description", "")
            agent_id = agent["id"]
            if agent_id in description:
                agent_name = agent["name"]
                description = description.replace(agent_id, agent_name)
                if re.search(r"[\u4e00-\u9fff]", agent_name):
                    escaped_name = re.escape(agent_name)
                    description = re.sub(rf"\s*({escaped_name})\s*", r"\1", description)
            profile["description"] = description

            compressed_description = await self._compress_description(profile["description"])
            profile["compressed_description"] = compressed_description

            os.makedirs(os.path.dirname(self.profile_output_path), exist_ok=True)
            with open(self.profile_output_path, "a", encoding="utf-8") as f:
                profile_info = {
                    "id": agent["name"],
                    "name": agent["name"],
                    "role": agent["role"],
                    **agent["profile"],
                    **agent["attributes"],
                }
                profile_info = self._remove_none_values(profile_info)
                f.write(json.dumps(profile_info, ensure_ascii=False) + "\n")

            with open(self.state_output_path, "a", encoding="utf-8") as f:
                state_info = {"id": agent["name"], **agent["state"]}
                f.write(json.dumps(state_info, ensure_ascii=False) + "\n")

            return True

        except Exception as e:
            logger.info(f"Error generating profile for agent {agent.get('id')}: {e}")
            return False

    async def run(self):
        """Run the agent generation process."""
        agents = self._initialize_agents()

        tasks = [self._generate_profile(agent) for agent in agents]
        results = await tqdm_asyncio.gather(*tasks, desc="Generating agent profiles")

        success_count = sum(1 for r in results if r is True)
        logger.info(
            f"Save {success_count}/{len(results)} agents to {self.profile_output_path} and {self.state_output_path}"
        )
