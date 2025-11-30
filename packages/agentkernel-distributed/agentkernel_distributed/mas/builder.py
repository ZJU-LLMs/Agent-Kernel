"""Initializes and builds the distributed simulation system based on configuration."""

import copy
import json
import os

import ray
import yaml
from typing import List, Dict, Any, Optional, Type, Tuple

from .system import System
from .pod import BasePodManager, PodManager
from .controller import Controller, BaseController

from ..toolkit.models.router import ModelRouter, AsyncModelRouter
from ..toolkit.logger import get_logger
from ..types.configs import Config, AgentConfig, AgentTemplateConfig


logger = get_logger(__name__)


def load_config(project_path: str) -> Config:
    """
    Loads all configurations based on a conventional project structure.

    Args:
        project_path (str): The absolute path to the project's root directory.

    Returns:
        Config: A validated Pydantic Config object containing all simulation settings.

    Raises:
        FileNotFoundError: If directories or required files are not found.
    """
    logger.info(f"Loading configuration from project path: {project_path}")

    configs_base_dir = os.path.join(project_path, "configs")

    if not os.path.isdir(configs_base_dir):
        raise FileNotFoundError(f"Configuration directory not found at: {configs_base_dir}")

    main_config_path = os.path.join(configs_base_dir, "simulation_config.yaml")
    if not os.path.exists(main_config_path):
        raise FileNotFoundError(f"Main configuration file not found at: {main_config_path}")

    with open(main_config_path, "r", encoding="utf-8") as f:
        final_config_dict = yaml.safe_load(f)

    config_paths = final_config_dict.get("configs", {})
    for module_name, relative_path in config_paths.items():
        full_path = os.path.join(configs_base_dir, relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Config file for '{module_name}' not found at: {full_path}")

        logger.info(f"Loading '{module_name}' config from: {full_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            final_config_dict[module_name] = yaml.safe_load(f)

    data_paths = final_config_dict.get("data", {})
    loaded_data: Dict[str, Any] = {}
    for data_key, relative_path in data_paths.items():
        full_path = os.path.join(project_path, relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Data file for '{data_key}' not found at: {full_path}")

        logger.info(f"Loading data source '{data_key}' from: {full_path}")
        with open(full_path, "r", encoding="utf-8") as f:
            if full_path.endswith(".json"):
                data = json.load(f)
            elif full_path.endswith((".yaml", ".yml")):
                data = yaml.safe_load(f)
            elif full_path.endswith(".jsonl"):
                data = [json.loads(line) for line in f if line.strip()]
            else:
                logger.warning(f"Unsupported data file type for '{data_key}': {full_path}. Skipping.")

        loaded_data[data_key] = {}
        if (
            isinstance(data, list)
            and all(isinstance(entry, dict) for entry in data)
            and all("id" in entry for entry in data)
        ):
            for entry in data:
                loaded_data[data_key][entry["id"]] = entry
        else:
            loaded_data[data_key] = data

    final_config_dict["loaded_data"] = loaded_data

    agents_cfg = final_config_dict.get("agent_templates")
    if agents_cfg and isinstance(agents_cfg, dict):
        templates = agents_cfg.get("templates") or []
        for template in templates or []:
            if not template.get("agents"):
                profiles = loaded_data.get("agent_profiles")
                template["agents"] = sorted(list(profiles.keys()))

    try:
        config = Config(**final_config_dict)
        logger.info("Configuration loaded and validated successfully.")
        return config
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}", exc_info=True)
        raise


class Builder:
    """
    A stateless builder for the (Async) Simulation engine.

    Its primary role is to use the configuration to initialize and wire
    together all distributed actors, and then return a fully configured
    System object that holds the simulation state.
    """

    def __init__(self, project_path: str, resource_maps: Dict[str, Any]) -> None:
        """
        Initializes the simulation builder.

        Args:
            project_path (str): The absolute path to the project's root directory.
            resource_maps (Dict[str, Any]): A dictionary mapping resource keys
                (like 'controller', 'pod_manager') to their respective classes.
        """
        logger.info("Initializing Simulation Engine (Builder)...")
        self._project_path = project_path
        self._config: Config = load_config(project_path)
        self._resource_maps = resource_maps
        self._model_router_config: List[Dict[str, Any]] = []
        self._pod_manager: BasePodManager = None
        self._system: System = None

        self._controller_class: Type[BaseController]
        self._pod_manager_class: Type[BasePodManager]

        custom_controller = self._resource_maps.get("controller")
        custom_pod_manager = self._resource_maps.get("pod_manager")

        if custom_controller:
            logger.info(f"Using custom controller '{custom_controller.__name__}' from resource_maps.")
            if not issubclass(custom_controller, BaseController):
                raise TypeError(f"Custom Controller '{custom_controller.__name__}' must inherit from 'BaseController'.")
            self._controller_class = custom_controller
        else:
            logger.info("Using default Controller.")
            self._controller_class = Controller

        if custom_pod_manager:
            original_pod_manager_class = custom_pod_manager.__ray_metadata__.modified_class
            logger.info(f"Using custom pod manager '{original_pod_manager_class.__name__}' from resource_maps.")

            if not issubclass(original_pod_manager_class, BasePodManager):
                raise TypeError(
                    f"Custom Pod Manager '{original_pod_manager_class.__name__}' must inherit from 'BasePodManager'."
                )
            self._pod_manager_class = custom_pod_manager
        else:
            logger.info("Using default PodManager.")
            self._pod_manager_class = PodManager

    @property
    def config(self) -> Config:
        """
        Gets the loaded and validated simulation configuration object.

        Returns:
            Config: The simulation configuration.
        """
        return self._config

    @property
    def resource_maps(self) -> Dict[str, Any]:
        """
        Gets the provided resource maps.

        Returns:
            Dict[str, Any]: The dictionary of resource classes.
        """
        return self._resource_maps

    async def init(self) -> Tuple[Optional[BasePodManager], System]:
        """
        Main entry point to initialize and assemble the entire distributed simulation.

        This method constructs and returns a fully operational System object and
        the associated PodManager.

        Returns:
            Tuple[Optional[BasePodManager], System]: A tuple containing the
            initialized PodManager actor handle and the System object.
        """
        if not ray.is_initialized():
            ray.init(
                runtime_env={"working_dir": self._project_path},
                _system_config={"memory_monitor_refresh_ms": 0}
            )
        logger.info("Ray is initialized.")

        models_configs = self.config.models or []
        models_configs_dict = [m.model_dump() for m in models_configs]
        self._model_router_config = models_configs_dict
        logger.info("ModelRouter Actor and Proxy are created.")

        self._load_data_into_config()

        await self._init_pod_manager()

        await self._init_system()

        await self.post_init()

        return self._pod_manager, self._system

    def _load_data_into_config(self) -> None:
        """
        Injects data from `loaded_data` into the agent and environment configurations.

        This makes the configurations self-contained before they are passed to actors.
        """
        logger.info("Injecting loaded data into agent and environment configurations...")
        loaded_data = self._config.loaded_data

        if self._config.agent_templates:
            self._config.agents = self._generate_all_agent_configs(self._config.agent_templates, loaded_data)

        if self._config.environment and self._config.environment.components:
            for comp_config in self._config.environment.components.values():
                plugin_name, plugin_obj = next(iter(comp_config.plugin.items()))
                plugin_config_dict = plugin_obj.model_dump()

                for param, data_key in list(plugin_config_dict.items()):
                    if isinstance(data_key, str) and data_key in loaded_data:
                        logger.debug(f"Injecting data for '{data_key}' into env plugin '{plugin_name}'.")
                        plugin_config_dict[param] = loaded_data[data_key]

                for key, value in plugin_config_dict.items():
                    if hasattr(plugin_obj, key):
                        setattr(plugin_obj, key, value)

        logger.info("Data injection complete.")

    def _generate_all_agent_configs(self, agent_config: AgentTemplateConfig, loaded_data: Dict) -> List[Dict]:
        """
        Generates a complete configuration dictionary for each agent based on
        the templates and injects its specific data.

        Args:
            agent_config (AgentTemplateConfig): The agent templates configuration.
            loaded_data (Dict): The dictionary of all loaded data sources.

        Returns:
            List[Dict]: A list of complete and data-injected agent
            configuration dictionaries.
        """
        all_configs = []
        templates = agent_config.templates

        for template in templates:
            components_template = template.components
            agent_ids_for_template = template.agents
            component_order = template.component_order

            for agent_id in agent_ids_for_template:
                agent_components = copy.deepcopy(components_template)

                for comp_config in agent_components.values():
                    plugin_dict = comp_config.plugin
                    if not plugin_dict:
                        continue

                    plugin_name, plugin_obj = next(iter(plugin_dict.items()))
                    plugin_config_dict = plugin_obj.model_dump()

                    for param, data_key in list(plugin_config_dict.items()):
                        if isinstance(data_key, str) and data_key in loaded_data:
                            data_source = loaded_data[data_key]
                            injected_data = data_source.get(agent_id)
                            if injected_data is not None:
                                plugin_config_dict[param] = injected_data

                    for key, value in plugin_config_dict.items():
                        if hasattr(plugin_obj, key):
                            setattr(plugin_obj, key, value)

                final_agent_config = {
                    "id": agent_id,
                    "components": agent_components,
                    "component_order": component_order,
                }
                all_configs.append(final_agent_config)
        return all_configs

    async def _init_pod_manager(self) -> None:
        """
        Initializes the PodManager.

        This manager dynamically generates agent configs from a template and
        data files, then creates and manages the agent pods.
        """
        if not self._config.agents:
            logger.warning("Agent template configuration not found. Skipping agent pod initialization.")
            self._pod_manager = None
            return

        POD_MANAGER_ACTOR_NAME = "global_pod_manager"
        pod_manager = self._pod_manager_class.options(
            name=POD_MANAGER_ACTOR_NAME,
        ).remote(
            pod_size=self._config.simulation.pod_size,
            init_batch_size=self._config.simulation.init_batch_size,
            controller_class=self._controller_class,
        )
        logger.info(f"PodManager Actor is being created with the name: '{POD_MANAGER_ACTOR_NAME}'")

        await pod_manager.init.remote(
            configs=self._config,
            resource_maps=self.resource_maps,
            model_router_config=self._model_router_config,
        )

        logger.info("MasPodManager and MasPods are created and initialized.")
        self._pod_manager = pod_manager

    async def _init_system(self) -> None:
        """
        Creates and returns the core System object with its components
        (e.g., Timer, Messager, Recorder).

        Raises:
            ValueError: If system configuration is missing or 'system_components'
                are not found in resource_maps.
        """
        logger.info("Initializing system components (Timer, Messager, Recorder)...")

        if not self.config.system or not self.config.system.components:
            raise ValueError("System configuration or components are missing from the main config.")

        component_class_map = self.resource_maps.get("system_components", {})
        if not component_class_map:
            raise ValueError("Could not find 'system_components' in resource_maps.")

        system = System()

        components_config = self.config.system.components
        for component_name, component_config in components_config.items():
            if component_config is None:
                continue

            if component_name not in component_class_map:
                logger.warning(
                    f"component '{component_name}' found in config, but no corresponding class in resource_maps. Skipping."
                )
                continue

            try:
                component_handle = component_class_map[component_name].remote(**component_config)

                system.add_component(component_name, component_handle)

            except Exception as e:
                logger.error(
                    f"Failed to initialize component '{component_name}': {e}. This component will be disabled.",
                    exc_info=True,
                )

        self._system = system
        logger.info("System object created and populated with all configured components.")

    async def post_init(self) -> None:
        """
        Performs post-initialization steps, linking the System and PodManager.
        """
        await self._system.post_init(pod_manager=self._pod_manager)

        await self._pod_manager.post_init.remote(system_handle=self._system, pod_manager_handle=self._pod_manager)

        logger.info("Post-initialization of system and pod manager complete.")
