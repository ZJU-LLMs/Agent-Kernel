"""Ray actor encapsulating the runtime for a group of agents with environment, actions and a controller."""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

import os
import ray
import psutil

from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter, AsyncModelRouter
from ...toolkit.storages.base import DatabaseAdapter
from ...toolkit.storages.connection_pools import close_connection_pools, create_connection_pools
from ...types.configs import PodConfig
from ..action import Action
from ..agent.agent_manager import AgentManager
from ..controller import BaseController
from ..environment import Environment
from ..system import System

if TYPE_CHECKING:
    from .pod_manager_base import BasePodManager

logger = get_logger(__name__)

__all__ = ["MasPod"]


@ray.remote
class MasPod:
    """Ray actor that hosts agents, environment, actions, and a controller."""

    def __init__(
        self,
        pod_id: str,
        pod_config: PodConfig,
        resource_maps: Dict[str, Dict[str, Any]],
        controller_class: Type[BaseController],
    ) -> None:
        """
        Store configuration and resource references for later initialization.

        Args:
            pod_id (str): Unique identifier of this pod.
            pod_config (PodConfig): Configuration describing agents, actions, and environment.
            resource_maps (Dict[str, Dict[str, Any]]): Shared registry of components, adapters, and plugins.
            controller_class (Type[BaseController]): Controller implementation used inside the pod.
        """
        self._pod_id = pod_id
        self._pod_config = pod_config
        self._resource_maps = resource_maps.copy()
        self._controller_class = controller_class

        self._connection_pools: Dict[str, Any] = {}
        self._adapters: Dict[str, DatabaseAdapter] = {}

        self._agent_manager: Optional[AgentManager] = None
        self._action: Optional[Action] = None
        self._environment: Optional[Environment] = None
        self._controller: Optional[BaseController] = None

        self._model_router: Optional[ModelRouter] = None
        self._system_handle: Optional[System] = None
        self._pod_manager_handle: Optional["BasePodManager"] = None

        self._process = psutil.Process(os.getpid())
        logger.info("[%s] Actor process created with PID %d.", self._pod_id, self._process.pid)

    async def init(self, model_router_config: Optional[List[Dict[str, Any]]]) -> None:
        """
        Initialize adapters, environment, actions, agents, and controller.

        Args:
            model_router_config (Optional[List[Dict[str, Any]]]): Configuration for the model router used in this pod.

        Returns:
            None
        """
        logger.info("[%s] Starting full internal initialization...", self._pod_id)
        model_backend = AsyncModelRouter(models_configs=model_router_config)
        self._model_router = ModelRouter(model_backend)

        await self._init_adapters()
        self._resource_maps["adapters"] = self._adapters
        logger.info("[%s] Adapters initialized.", self._pod_id)

        await self._init_environment()
        await self._init_action()
        await self._init_agent_manager()
        await self._init_controller()

        if self._agent_manager:
            agent_count = self._agent_manager.get_agent_count()
        else:
            agent_count = 0
        logger.info("[%s] Full initialization complete. Managing %s agents.", self._pod_id, agent_count)

    async def post_init(self, system_handle: System, pod_manager_handle: "BasePodManager") -> None:
        """
        Inject runtime dependencies after all pods are created.

        Args:
            system_handle (System): Handle to the global system service.
            pod_manager_handle (BasePodManager): Handle to the pod manager supervising this pod.
        """
        self._system_handle = system_handle
        self._pod_manager_handle = pod_manager_handle

        if self._controller:
            await self._controller.post_init(
                system=system_handle,
                model_router=self._model_router,
                pod_manager=pod_manager_handle,
            )

        if self._environment:
            await self._environment.post_init()

        if self._action and self._controller and self._model_router:
            await self._action.post_init(controller=self._controller, model_router=self._model_router)

        if self._agent_manager and self._model_router and self._controller:
            await self._agent_manager.post_init(model_router=self._model_router, controller=self._controller)

        logger.info("[%s] External dependencies injected.", self._pod_id)
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the current Pod Actor process.
        Returns:
            Dict[str, Any]: A dictionary containing CPU and memory usage metrics.
        """
        return {
            "pod_id": self._pod_id,
            "memory_rss_mb": self._process.memory_info().rss / (1024 * 1024),
        }

    def get_pod_id(self) -> str:
        """
        Return the identifier of this pod.

        Returns:
            str: Pod identifier.
        """
        return self._pod_id

    async def forward(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a controller method from outside the pod.

        Args:
            method_name (str): Name of the controller method to invoke.
            *args (Any): Positional arguments forwarded to the controller.
            **kwargs (Any): Keyword arguments forwarded to the controller.

        Returns:
            Any: Result produced by the controller method.

        Raises:
            RuntimeError: If the controller has not been initialized.
            AttributeError: If the controller lacks the requested attribute.
            TypeError: If the requested attribute is not callable.
        """
        if not self._controller:
            raise RuntimeError(f"[{self._pod_id}] Controller is not initialized.")
        if not hasattr(self._controller, method_name):
            raise AttributeError(f"[{self._pod_id}] Controller has no method '{method_name}'.")

        method = getattr(self._controller, method_name)
        if not callable(method):
            raise TypeError(f"[{self._pod_id}] Attribute '{method_name}' is not callable.")

        result = method(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _init_adapters(self) -> None:
        """
        Initialize all configured database adapters.

        Returns:
            None
        """
        db_config = self._pod_config.database
        self._connection_pools = await create_connection_pools(db_config)
        logger.info("[%s] Initializing data adapters...", self._pod_id)

        adapter_class_map = self._resource_maps.get("adapters", {})
        if not adapter_class_map:
            logger.warning("[%s] No adapter classes found in resource maps.", self._pod_id)
            self._adapters = {}
            return

        initialized_adapters: Dict[str, DatabaseAdapter] = {}
        for name, config in db_config.adapters.items():
            adapter_class = adapter_class_map.get(name)
            if adapter_class is None:
                logger.warning("[%s] Adapter class for '%s' not found. Skipping.", self._pod_id, name)
                continue

            try:
                adapter_instance: DatabaseAdapter = adapter_class()
                adapter_settings = config.settings or {}

                if "embedding_model" in adapter_settings:
                    logger.info("[%s] Adapter '%s' requires an embedding model.", self._pod_id, name)
                    await adapter_instance.connect(config=adapter_settings, model_router=self._model_router)
                elif config.use_pool:
                    pool_info = self._connection_pools.get(config.use_pool)
                    if not pool_info:
                        raise ValueError(
                            f"Connection pool '{config.use_pool}' required by adapter '{name}' was not found."
                        )
                    pool = pool_info["instance"]
                    await adapter_instance.connect(config=adapter_settings, pool=pool)
                else:
                    await adapter_instance.connect(config=adapter_settings)

                initialized_adapters[name] = adapter_instance
                logger.info("[%s] Adapter '%s' initialized successfully.", self._pod_id, name)
            except Exception as exc:
                logger.error("[%s] Failed to initialize adapter '%s': %s", self._pod_id, name, exc, exc_info=True)

        self._adapters = initialized_adapters

    async def _init_agent_manager(self) -> None:
        """
        Create the agent manager and initialize all agents.

        Returns:
            None
        """
        self._agent_manager = AgentManager(
            pod_id=self._pod_id,
            agent_templates=self._pod_config.agent_templates,
            agent_configs=self._pod_config.agents,
            resource_maps=self._resource_maps,
        )
        await self._agent_manager.init()
        logger.info(
            "[%s] AgentManager initialized with %s agents.",
            self._pod_id,
            self._agent_manager.get_agent_count(),
        )

    async def _init_action(self) -> None:
        """
        Initialize the action proxy and all configured components.

        Returns:
            None
        """
        action_components_config = self._pod_config.actions.components if self._pod_config.actions else {}
        components = {name: self._resource_maps["action_components"][name]() for name in action_components_config}
        self._action = Action()
        for name, component in components.items():
            self._action.add_component(name, component)

        await self._action.init(
            comp_configs=action_components_config,
            resource_maps=self._resource_maps,
        )
        logger.info("[%s] Action proxy initialized.", self._pod_id)

    async def _init_environment(self) -> None:
        """
        Initialize the environment proxy and all configured components.

        Returns:
            None
        """
        env_components_config = self._pod_config.environment.components if self._pod_config.environment else {}
        components = {name: self._resource_maps["environment_components"][name]() for name in env_components_config}
        self._environment = Environment()
        for name, component in components.items():
            self._environment.add_component(name, component)

        await self._environment.init(
            comp_configs=env_components_config,
            resource_maps=self._resource_maps,
        )
        logger.info("[%s] Environment proxy initialized.", self._pod_id)

    async def _init_controller(self) -> None:
        """
        Instantiate the controller used within this pod.

        Returns:
            None
        """
        self._controller = self._controller_class(
            agent_manager=self._agent_manager,
            action=self._action,
            environment=self._environment,
            adapters=self._adapters,
        )
        logger.info("[%s] Controller instance created.", self._pod_id)

    async def close(self) -> None:
        """
        Release resources owned by the pod.

        Returns:
            None
        """
        if self._controller:
            await self._controller.close()

        try:
            for name, adapter in self._adapters.items():
                await adapter.disconnect()
                logger.info("%s adapter client has been closed.", name)
            await close_connection_pools(self._connection_pools)
        except Exception as exc:
            logger.error("Exception %s occurred while closing database resources.", exc)

        try:
            if self._model_router:
                await self._model_router.close()
                logger.info("ModelRouter has been closed.")
        except Exception as exc:
            logger.error(f"Exception {exc} occurred while closing the ModelRouter.")

        logger.info("MasPod %s has been closed.", self._pod_id)
