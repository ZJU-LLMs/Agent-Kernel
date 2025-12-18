"""
API endpoints for reading and writing YAML configuration files.

This module supports dynamic environment component configuration, allowing users
to define custom component types without modifying the core configurations.
"""

import os
import yaml
from fastapi import APIRouter, HTTPException, Body
from typing import Any, Dict

from ..services.simulation_manager import simulation_manager
from ..services.registry_generator import registry_generator

router = APIRouter()
CONFIGS_DIR = os.path.join(simulation_manager.workspace_path, "configs")

# Base default configurations (environment_config is generated dynamically)
BASE_DEFAULT_CONFIGS = {
    "simulation_config.yaml": {
        "simulation": {"pod_size": 10, "init_batch_size": 5, "max_ticks": 100},
        "configs": {
            "environment": "environment_config.yaml",
            "actions": "actions_config.yaml",
            "agent_templates": "agents_config.yaml",
            "system": "system_config.yaml",
            "database": "db_config.yaml",
            "models": "models_config.yaml",
        },
        "data": {
            "agent_profiles": "data/agent/profiles.jsonl",
            "agent_states": "data/agent/states.jsonl",
            "relationship_nodes": "data/relationship/nodes.jsonl",
            "relationship_edges": "data/relationship/edges.jsonl",
            "map_objects": "data/map/objects.jsonl",
            "map_agents": "data/map/agents.jsonl",
        },
        "api_server": {"host": "0.0.0.0", "port": 8000},
    },
    "agents_config.yaml": {"templates": []},
    "actions_config.yaml": {
        "name": "TestActions",
        "components": {
            "communication": {"plugins": {}},
            "tools": {"plugins": {}},
            "otheractions": {"plugins": {}},
        },
    },
    "db_config.yaml": {"pools": {}, "adapters": {}},
    "models_config.yaml": [],
    "system_config.yaml": {
        "name": "TestSystem",
        "components": {
            "messager": {"allow_self_messages": False, "block_empty_content": True},
            "timer": {"current_tick": 0, "timeout_ticks": 5},
            "recorder": None,
        },
    },
}


async def get_default_config_for(config_name: str) -> Dict[str, Any]:
    """
    Get the default configuration for a specific config file.

    For environment_config.yaml, this generates the config dynamically
    to include any custom environment component types discovered in the workspace.

    Args:
        config_name (str): The name of the configuration file.

    Returns:
        Dict[str, Any]: The default configuration, or None if no default exists.
    """
    if config_name == "environment_config.yaml":
        # Generate dynamically to include custom component types
        return await get_dynamic_environment_config()
    return BASE_DEFAULT_CONFIGS.get(config_name)


async def get_dynamic_environment_config() -> Dict[str, Any]:
    """
    Generate the environment configuration dynamically.

    This includes built-in components (relation, space) and any custom
    component types discovered in the workspace.

    Returns:
        Dict[str, Any]: The environment configuration.
    """
    # Start with built-in components
    components = {
        "relation": {"plugin": {}},
        "space": {"plugin": {}},
    }

    # Discover custom component types from the workspace
    try:
        registry_info = await registry_generator.get_registry_info(simulation_manager.workspace_path)
        # Add any custom environment component types
        env_plugins = registry_info.get("environment_plugins", {})
        for comp_type in env_plugins.keys():
            if comp_type not in components:
                components[comp_type] = {"plugin": {}}
    except Exception as e:
        print(f"Warning: Could not discover custom environment components: {e}")

    return {
        "name": "TestEnvironment",
        "components": components,
    }


@router.get("/{config_name}")
async def get_config_file(config_name: str):
    """
    Read a specified YAML configuration file.

    For environment_config.yaml, defaults are generated dynamically to include
    any custom environment component types discovered in the workspace.

    Args:
        config_name (str): The name of the configuration file to read.

    Returns:
        dict: The parsed YAML configuration data or default configuration if file is empty.

    Raises:
        HTTPException: If config name is invalid or file not found without default available.
    """
    if ".." in config_name or config_name.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid config name.")

    file_path = os.path.join(CONFIGS_DIR, config_name)
    os.makedirs(CONFIGS_DIR, exist_ok=True)

    if not os.path.exists(file_path):
        default_config = await get_default_config_for(config_name)
        if default_config is not None:
            return default_config
        else:
            raise HTTPException(
                status_code=404, detail=f"Config file '{config_name}' not found and no default is available."
            )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            default_config = await get_default_config_for(config_name)
            if default_config is not None:
                return default_config
            else:
                return {}

        # For environment config, merge with discovered custom components
        if config_name == "environment_config.yaml" and data:
            try:
                registry_info = await registry_generator.get_registry_info(simulation_manager.workspace_path)
                env_plugins = registry_info.get("environment_plugins", {})
                components = data.get("components", {})
                # Add any missing custom component types
                for comp_type in env_plugins.keys():
                    if comp_type not in components:
                        components[comp_type] = {"plugin": {}}
                data["components"] = components
            except Exception as e:
                print(f"Warning: Could not merge custom environment components: {e}")

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading or parsing YAML file: {e}")


@router.post("/{config_name}")
async def update_config_file(config_name: str, content: Dict[str, Any] = Body(...)):
    """
    Update a specified YAML configuration file with new content.

    Args:
        config_name (str): The name of the configuration file to update.
        content (Dict[str, Any]): The new configuration content as JSON.

    Returns:
        dict: A message indicating successful update.

    Raises:
        HTTPException: If config name is invalid or write operation fails.
    """
    if ".." in config_name or config_name.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid config name.")

    file_path = os.path.join(CONFIGS_DIR, config_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f, sort_keys=False, allow_unicode=True)
        return {"message": f"Successfully updated '{config_name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing YAML file: {e}")
