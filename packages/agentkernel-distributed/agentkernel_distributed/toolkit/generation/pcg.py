"""Procedural Content Generation (PCG) entry point."""

import asyncio
import argparse
import os
import sys
import yaml
from pathlib import Path

from ..models.async_router import AsyncModelRouter
from ..generation.pcg_agent import AgentGenerator
from ..generation.pcg_relationship import RelationshipGenerator
from ..generation.pcg_space import SpaceGenerator
from ..logger import get_logger

logger = get_logger(__name__)


class PCGGenerator:
    """A unified generator for agents, relationships, and space."""

    def __init__(self, data_dir: str, llms_config_path: str, pcg_config_path: str):
        """
        Initialize the PCG generator.

        Args:
            data_dir (str): The base directory for data files.
            llms_config_path (str): The path to the LLM configuration YAML file.
            pcg_config_path (str): The path to the PCG configuration YAML file.
        """
        self.data_dir = data_dir
        self.llms_config_path = llms_config_path
        self.pcg_config_path = pcg_config_path
        self.llm = None
        self.pcg_config = None
        self.seed = None
        self.steps = None

    async def load_configs(self):
        """Load configurations from the specified paths."""
        with open(self.llms_config_path, "r", encoding="utf-8") as f:
            llms_config = yaml.safe_load(f)

        self.llm = AsyncModelRouter(llms_config)

        with open(self.pcg_config_path, "r", encoding="utf-8") as f:
            self.pcg_config = yaml.safe_load(f)

        self.seed = self.pcg_config.get("seed")
        self.steps = self.pcg_config.get("steps")
        if not self.steps:
            self.steps = ("agents", "relationships", "space")

        config_output_dir = self.pcg_config.get("output_dir")
        if config_output_dir:
            self.data_dir = os.path.join(self.data_dir, config_output_dir)

    async def generate_agents(self):
        """Generate agent profiles and states."""
        cfg_agent = self.pcg_config["agent"]
        name_pool_path = cfg_agent.get("name_pool_path", None)
        profile_output_path = os.path.join(self.data_dir, cfg_agent["profile_output_path"])
        state_output_path = os.path.join(self.data_dir, cfg_agent["state_output_path"])

        agent_generator = AgentGenerator(
            llm=self.llm,
            agent_config=cfg_agent,
            profile_output_path=profile_output_path,
            state_output_path=state_output_path,
            name_pool_path=name_pool_path,
            is_incremental=True,
            seed=self.seed,
        )
        await agent_generator.run()

    async def generate_relationships(self):
        """Generate relationships between agents."""
        cfg_agent, cfg_relationship = self.pcg_config["agent"], self.pcg_config["relationship"]
        profile_path = os.path.join(self.data_dir, cfg_agent["profile_output_path"])
        node_output_path = os.path.join(self.data_dir, cfg_relationship["node_output_path"])
        edge_output_path = os.path.join(self.data_dir, cfg_relationship["edge_output_path"])

        relationship_generator = RelationshipGenerator(
            profile_path=profile_path,
            relationship_config=cfg_relationship,
            node_output_path=node_output_path,
            edge_output_path=edge_output_path,
            seed=self.seed,
        )
        await relationship_generator.run()

    def generate_space(self):
        """Generate spatial entities for agents."""
        cfg_agent, cfg_space = self.pcg_config["agent"], self.pcg_config.get("space")
        profile_path = os.path.join(self.data_dir, cfg_agent["profile_output_path"])
        agent_space_output_path = os.path.join(self.data_dir, cfg_space["output_path"])

        space_generator = SpaceGenerator(
            profile_path=profile_path, space_config=cfg_space, output_path=agent_space_output_path, seed=self.seed
        )
        space_generator.run()

    def _safe_read_jsonl(self, path: str):
        """
        Safely read a JSONL file.

        Args:
            path (str): The path to the JSONL file.

        Returns:
            List[Dict]: A list of items from the JSONL file.
        """
        items = []
        if not os.path.exists(path):
            return items
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(yaml.safe_load(line))
                except Exception:
                    try:
                        import json

                        items.append(json.loads(line))
                    except Exception:
                        continue
        return items

    async def run(self, steps=("agents", "relationships", "space")):
        """
        Run the complete PCG pipeline.

        Args:
            steps (Tuple[str, ...]): A tuple of steps to execute.
        """
        await self.load_configs()
        try:
            for step in steps:
                method = getattr(self, f"generate_{step}", None)
                if method:
                    logger.info(f"Generating {step}...")
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    logger.info(f"Completed {step}")
                else:
                    logger.warning(f"Unknown step: {step}")
        finally:
            if self.llm:
                await self.llm.close()


def parse_args():
    """Parse command-line arguments for the PCG script."""
    parser = argparse.ArgumentParser(
        description="Procedural Content Generation (PCG) for Multi-Agent Systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all content using paths from pcg_config.yaml
  pcg \\
    --llms-config configs/models_config.yaml \\
    --pcg-config configs/pcg_config.yaml

  # Generate only agents and relationships
  pcg \\
    --llms-config configs/models_config.yaml \\
    --pcg-config configs/pcg_config.yaml \\
    --steps agents relationships

  # Explicitly specify an output directory, overriding the config
  pcg \\
    --output-dir ./examples/distributed_test/data \\
    --llms-config configs/models_config.yaml \\
    --pcg-config configs/pcg_config.yaml

  # Use absolute paths for all configurations
  pcg \\
    --output-dir /path/to/data \\
    --llms-config /path/to/models_config.yaml \\
    --pcg-config /path/to/pcg_config.yaml
        """,
    )

    parser.add_argument(
        "--output-dir", type=str, default=".", help="Base directory for data files (default: current directory)."
    )

    parser.add_argument("--llms-config", type=str, required=True, help="Path to the LLM configuration YAML file.")

    parser.add_argument("--pcg-config", type=str, required=True, help="Path to the PCG configuration YAML file.")

    parser.add_argument(
        "--steps",
        nargs="+",
        choices=["agents", "relationships", "space"],
        default=["agents", "relationships", "space"],
        help="The generation steps to execute (default: all).",
    )

    return parser.parse_args()


def resolve_path(base_dir: str, path: str) -> str:
    """
    Resolve a file path relative to a base directory or the current working directory.

    If the path is absolute, it is returned as-is. Otherwise, it is resolved
    relative to `base_dir` and then the current working directory.

    Args:
        base_dir (str): The base directory for relative paths.
        path (str): The path to resolve.

    Returns:
        str: The resolved absolute path.

    Raises:
        FileNotFoundError: If the file cannot be found in any of the checked locations.
    """
    path_obj = Path(path)

    if path_obj.is_absolute():
        if not path_obj.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        return str(path_obj)

    base_path = Path(base_dir) / path
    if base_path.exists():
        return str(base_path)

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return str(cwd_path)

    raise FileNotFoundError(f"Configuration file not found: {path}\n" f"  Tried: {base_path}\n" f"  Tried: {cwd_path}")


async def main():
    """The main entry point for the PCG script."""
    args = parse_args()

    try:
        llms_config_path = resolve_path(args.output_dir, args.llms_config)
        pcg_config_path = resolve_path(args.output_dir, args.pcg_config)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    generator = PCGGenerator(
        data_dir=args.output_dir, llms_config_path=llms_config_path, pcg_config_path=pcg_config_path
    )

    try:
        await generator.run(steps=tuple(args.steps))
        logger.info("PCG generation completed successfully")
    except Exception as e:
        logger.error(f"PCG generation failed: {e}", exc_info=True)
        sys.exit(1)


def cli():
    """The command-line interface entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
