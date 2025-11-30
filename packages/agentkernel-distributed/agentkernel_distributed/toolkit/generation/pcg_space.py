"""Module for generating spatial assignments for agents."""

import os
import json
import random
from typing import Any, Dict, List

from ..logger import get_logger

logger = get_logger(__name__)


class SpaceGenerator:
    """A class for generating spatial assignments for agents."""

    def __init__(self, profile_path: str, space_config: Dict[str, Any], output_path: str, seed: int | None = None):
        """
        Initialize the SpaceGenerator.

        Args:
            profile_path (str): The path to the agent profiles file.
            space_config (Dict[str, Any]): The space configuration.
            output_path (str): The path to the output file for agent space info.
            seed (Optional[int]): The random seed.
        """
        self.profile_path = profile_path
        self.space_config = space_config
        self.world_size = self.space_config["world_size"]
        self.output_path = output_path
        self.rng = random.Random(seed)
        logger.info(f"running SpaceGenerator")

    def _normalize_agents(self) -> List[Dict[str, Any]]:
        """
        Load and normalize agent data from the profile path.

        Returns:
            List[Dict[str, Any]]: A list of agent data.
        """
        agents: List[Dict[str, Any]] = []
        with open(self.profile_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                agent = json.loads(line)
                agents.append(agent)
        return agents

    def run(self):
        """Randomly assign positions in the map to agents."""
        agents = self._normalize_agents()
        width, height = self.world_size

        for agent in agents:
            x = self.rng.randint(1, width - 1)
            y = self.rng.randint(1, height - 1)
            agent["position"] = [x, y]

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            for agent in agents:
                space_info = {
                    "id": agent["id"],
                    "name": agent["name"],
                    "position": agent["position"],
                }
                f.write(json.dumps(space_info, ensure_ascii=False) + "\n")

        logger.info(f"Save {len(agents)} coordinates to {self.output_path}")
