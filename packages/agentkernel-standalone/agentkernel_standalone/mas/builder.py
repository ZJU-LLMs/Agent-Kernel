import copy
import json
import os
from typing import List, Dict, Any, Optional, Type, Tuple

from .agent.agent_manager import AgentManager
from .action.action import Action
from .environment.environment import Environment
from .system import System
from .controller import Controller, BaseController

from ..toolkit.models.router import ModelRouter, AsyncModelRouter
from ..toolkit.storages.base import DatabaseAdapter
from ..toolkit.storages.connection_pools import create_connection_pools
from ..toolkit.logger import get_logger
from ..types.configs import Config, AgentConfig, AgentTemplateConfig
import yaml


logger = get_logger(__name__)


def load_config(project_path: str) -> Config:
    """
    Load all configurations from a structured project directory.

    This function reads YAML and JSON files from a 'configs' directory
    and data files from a 'data' directory, merging them into a single
    configuration object.

    Args:
        project_path (str): The absolute path to the project's root directory.

    Returns:
        Config: A validated configuration object.

    Raises:
        FileNotFoundError: If required configuration or data files are missing.
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
    A stateless builder for the standalone simulation engine.

    Its primary role is to use the configuration to initialize and wire
    together all components for a single-process simulation.
    """

    def __init__(self, project_path: str, resource_maps: Dict[str, Any]) -> None:
        """
        Initialize the simulation builder.

        Args:
            project_path (str): The absolute path to the project's root directory.
            resource_maps (Dict[str, Any]): A dictionary mapping resource keys
                (like 'controller') to their respective classes.
        """
        logger.info("Initializing Simulation Engine (Builder)...")
        self._project_path = project_path
        self._config: Config = load_config(project_path)
        self._resource_maps = resource_maps
        self._model_router: Optional[ModelRouter] = None
        self._system: Optional[System] = None

        self._controller: Optional[BaseController] = None
        self._agent_manager: Optional[AgentManager] = None
        self._action: Optional[Action] = None
        self._environment: Optional[Environment] = None

        self._connection_pools: Dict[str, Any] = {}
        self._adapters: Dict[str, DatabaseAdapter] = {}

        self._controller_class: Type[BaseController]

        custom_controller = self._resource_maps.get("controller")

        if custom_controller:
            logger.info(f"Using custom controller '{custom_controller.__name__}' from resource_maps.")
            if not issubclass(custom_controller, BaseController):
                raise TypeError(f"Custom Controller '{custom_controller.__name__}' must inherit from 'BaseController'.")
            self._controller_class = custom_controller
        else:
            logger.info("Using default Controller.")
            self._controller_class = Controller

    @property
    def config(self) -> Config:
        """Get the loaded and validated simulation configuration object."""
        return self._config

    @property
    def resource_maps(self) -> Dict[str, Any]:
        """Get the provided resource maps."""
        return self._resource_maps

    async def init(self) -> Tuple[Optional[BaseController], System]:
        """
        Initialize and assemble the entire standalone simulation.

        This method constructs and returns a fully operational Controller object
        that manages the simulation.

        Returns:
            Tuple[Optional[BaseController], System]: The fully initialized controller and system.

        Raises:
            RuntimeError: If initialization fails.
        """
        logger.info("Initializing in standalone mode.")

        # 1. Init Model Router
        models_configs = self.config.models or []
        models_configs_dict = [m.model_dump() for m in models_configs]

        try:
            model_backend = AsyncModelRouter(models_configs_dict)
            self._model_router = ModelRouter(backend_router=model_backend)
            logger.info("Local ModelRouter and Backend are created.")
        except Exception as e:
            logger.error(f"Failed to create local ModelRouter. Error: {e}", exc_info=True)
            raise

        # 2. Load data
        self._load_data_into_config()

        # 3. Init System
        await self._init_system()

        # 4. Init Adapters
        await self._init_adapters()
        self._resource_maps["adapters"] = self._adapters

        # 5. Init Environment
        await self._init_environment()

        # 6. Init Action
        await self._init_action()

        # 7. Init AgentManager
        await self._init_agent_manager()

        # 8. Init Controller
        await self._init_controller()

        # 9. Run Post-init to wire everything together
        await self.post_init()

        # 10. Check controller
        if not self._controller:
            raise RuntimeError("Controller initialization failed.")

        # 11. Save initial state to DB
        await self._controller.save_to_db(scope="all")

        logger.info("Standalone simulation engine initialized successfully.")
        return self._controller, self._system

    def _load_data_into_config(self) -> None:
        """Inject data from `loaded_data` into agent and environment configurations."""
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

    def _generate_all_agent_configs(self, agent_config: AgentTemplateConfig, loaded_data: Dict) -> List[AgentConfig]:
        """
        Generate a complete configuration for each agent based on templates.

        Args:
            agent_config (AgentTemplateConfig): The agent template configuration.
            loaded_data (Dict): The loaded data to inject.

        Returns:
            List[AgentConfig]: A list of complete agent configurations.
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
                all_configs.append(AgentConfig(**final_agent_config))
        return all_configs

    async def _init_adapters(self) -> None:
        """Initialize all configured database adapters."""
        db_config = self._config.database
        if not db_config:
            logger.warning("[standalone] No database config found, skipping adapter init.")
            return

        self._connection_pools = await create_connection_pools(db_config)
        logger.info("[standalone] Initializing data adapters...")

        adapter_class_map = self._resource_maps.get("adapters", {})
        if not adapter_class_map:
            logger.warning("[standalone] No adapter classes found in resource maps.")
            self._adapters = {}
            return

        initialized_adapters: Dict[str, DatabaseAdapter] = {}
        for name, config in db_config.adapters.items():
            adapter_class = adapter_class_map.get(name)
            if adapter_class is None:
                logger.warning(f"[standalone] Adapter class for '{name}' not found. Skipping.")
                continue

            try:
                adapter_instance: DatabaseAdapter = adapter_class()
                adapter_settings = config.settings or {}

                if "embedding_model" in adapter_settings:
                    logger.info(f"[standalone] Adapter '{name}' requires an embedding model.")
                    await adapter_instance.connect(config=adapter_settings, model_router=self._model_router)
                elif config.use_pool:
                    pool_info = self._connection_pools.get(config.use_pool)
                    if not pool_info:
                        raise ValueError(
                            f"Connection pool '{config.use_pool}' required by adapter '{name}' was not found."
                        )
                    await adapter_instance.connect(config=adapter_settings, pool=pool_info["instance"])
                else:
                    await adapter_instance.connect(config=adapter_settings)

                initialized_adapters[name] = adapter_instance
                logger.info(f"[standalone] Adapter '{name}' initialized successfully.")
            except Exception as exc:
                logger.error(f"[standalone] Failed to initialize adapter '{name}': {exc}", exc_info=True)

        self._adapters = initialized_adapters

    async def _init_agent_manager(self) -> None:
        """Create the agent manager and initialize all agents."""
        self._agent_manager = AgentManager(
            agent_templates=self._config.agent_templates,
            agent_configs=self._config.agents,
            resource_maps=self._resource_maps,
        )
        await self._agent_manager.init()
        logger.info(
            "[standalone] AgentManager initialized with %s agents.",
            self._agent_manager.get_agent_count(),
        )

    async def _init_action(self) -> None:
        """Initialize the action proxy and all configured components."""
        action_components_config = self._config.actions.components if self._config.actions else {}
        components = {name: self._resource_maps["action_components"][name]() for name in action_components_config}
        self._action = Action()
        for name, component in components.items():
            self._action.add_component(name, component)

        await self._action.init(
            comp_configs=action_components_config,
            resource_maps=self._resource_maps,
        )
        logger.info("[standalone] Action proxy initialized.")

    async def _init_environment(self) -> None:
        """Initialize the environment proxy and all configured components."""
        env_components_config = self._config.environment.components if self._config.environment else {}
        components = {name: self._resource_maps["environment_components"][name]() for name in env_components_config}
        self._environment = Environment()
        for name, component in components.items():
            self._environment.add_component(name, component)

        await self._environment.init(
            comp_configs=env_components_config,
            resource_maps=self._resource_maps,
        )
        logger.info("[standalone] Environment proxy initialized.")

    async def _init_controller(self) -> None:
        """Instantiate the controller."""
        self._controller = self._controller_class(
            agent_manager=self._agent_manager,
            action=self._action,
            environment=self._environment,
            adapters=self._adapters,
        )
        logger.info("[standalone] Controller instance created.")

    async def _init_system(self) -> None:
        """
        Create and return the core System object with its components.
        """
        logger.info("Initializing system components (Timer, Messager, Recorder) as local objects...")

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
                component_handle = component_class_map[component_name](**component_config)

                system.add_component(component_name, component_handle)

            except Exception as e:
                logger.error(
                    f"Failed to initialize component '{component_name}': {e}. This component will be disabled.",
                    exc_info=True,
                )

        self._system = system
        logger.info("System object created and populated with all configured local components.")

    async def post_init(self) -> None:
        """Perform post-initialization steps, linking all local components."""
        if (
            not self._system
            or not self._controller
            or not self._agent_manager
            or not self._environment
            or not self._action
        ):
            raise RuntimeError("Cannot run post_init, core components are missing.")

        # 1. Post-init System
        await self._system.post_init(controller=self._controller)

        # 2. Post-init Controller
        await self._controller.post_init(
            system=self._system,
            model_router=self._model_router,
        )

        # 3. Post-init Environment
        await self._environment.post_init()

        # 4. Post-init Action
        await self._action.post_init(controller=self._controller, model_router=self._model_router)

        # 5. Post-init AgentManager
        await self._agent_manager.post_init(model_router=self._model_router, controller=self._controller)

        logger.info("Post-initialization of all standalone components complete.")
