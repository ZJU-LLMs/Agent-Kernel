"""Ray-backed implementation of the MAS pod manager."""

import asyncio
from typing import Any, Dict, List, Literal, Optional, Type

import ray
from ray.actor import ActorHandle

from ...mas.environment.base import EnvironmentPlugin
from ...mas.system import System
from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter, AsyncModelRouter
from ...toolkit.storages.base import DatabaseAdapter
from ...toolkit.storages.connection_pools import close_connection_pools, create_connection_pools
from ...types.configs import Config, PodConfig
from ...types.schemas.message import Message
from ..controller import BaseController
from .mas_pod import MasPod
from .pod_manager_base import BasePodManager

logger = get_logger(__name__)


class PodManagerImpl(BasePodManager):
    """Concrete pod manager that coordinates Ray actors."""

    def __init__(
        self,
        pod_size: int = 5,
        init_batch_size: int = 5,
        controller_class: Optional[Type[BaseController]] = None,
    ) -> None:
        """
        Initialize the pod manager with batching details.

        Args:
            pod_size (int): Maximum number of agents per pod. Default is 5.
            init_batch_size (int): Number of pods to initialize or close concurrently. Default is 5.
            controller_class (Optional[Type[BaseController]]): Controller class used by each pod.
        """
        super().__init__(pod_size=pod_size, init_batch_size=init_batch_size, controller_class=controller_class)
        self._self_handle: Optional[Any] = None

    async def _init_adapters(self) -> None:
        """
        Initialize database adapters required for pod manager operations.

        Raises:
            ValueError: If a configured adapter references a missing connection pool.
        """
        if not self._configs or not self._configs.database:
            logger.warning("Database configuration not found. Skipping adapter initialization for PodManager.")
            return

        db_config = self._configs.database
        self._connection_pools = await create_connection_pools(db_config)
        logger.info("PodManager: Initializing data adapters for initial data loading...")

        adapter_class_map = self._resource_maps.get("adapters", {})
        if not adapter_class_map:
            logger.warning("PodManager: No adapter classes found in resource maps. Cannot initialize adapters.")
            return

        initialized_adapters: Dict[str, DatabaseAdapter] = {}
        for name, adapter_config in db_config.adapters.items():
            adapter_class = adapter_class_map.get(name)
            if adapter_class is None:
                logger.warning(f"PodManager: Adapter class for '{name}' not found. Skipping.")
                continue
            try:
                adapter_instance: DatabaseAdapter = adapter_class()
                adapter_settings = adapter_config.settings or {}

                if "embedding_model" in adapter_settings:
                    logger.info(f"Adapter '{name}' requires an embedding model. Injecting ModelRouter.")
                    await adapter_instance.connect(config=adapter_settings, model_router=self._model_router)
                elif adapter_config.use_pool:
                    pool_info = self._connection_pools.get(adapter_config.use_pool)
                    if not pool_info:
                        raise ValueError(
                            f"Connection pool '{adapter_config.use_pool}' required by adapter '{name}' was not found."
                        )
                    pool_to_use = pool_info["instance"]
                    await adapter_instance.connect(config=adapter_settings, pool=pool_to_use)
                else:
                    await adapter_instance.connect(config=adapter_settings)

                initialized_adapters[name] = adapter_instance
                logger.info(f"PodManager: Adapter '{name}' initialized successfully.")
            except Exception as exc:
                logger.error(f"PodManager: Failed to initialize adapter '{name}': {exc}", exc_info=True)
        self._adapters = initialized_adapters

    async def init(
        self,
        configs: Config,
        resource_maps: Dict[str, Dict[str, Any]],
        model_router_config: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Initialize pods and supporting infrastructure.

        Args:
            configs (Config): Deployment configuration describing agents and pods.
            resource_maps (Dict[str, Dict[str, Any]]): Shared registry of loadable classes and singletons.
            model_router_config (Optional[List[Dict[str, Any]]]): Optional configuration for the model router.
        """
        self._resource_maps = resource_maps
        self._configs = configs
        self._model_router_config = model_router_config

        if model_router_config:
            model_backend = AsyncModelRouter(models_configs=model_router_config)
            self._model_router = ModelRouter(model_backend)

        await self._init_adapters()

        all_agents_configs = configs.agents
        pod_agent_configs = [
            all_agents_configs[i : i + self._pod_size] for i in range(0, len(all_agents_configs), self._pod_size)
        ]

        pod_handles: Dict[str, MasPod] = {}
        for pod_index, pod_agent_cfgs in enumerate(pod_agent_configs):
            pod_id = f"pod_{pod_index}"
            pod_cfg = PodConfig(
                agent_templates=configs.agent_templates,
                agents=pod_agent_cfgs,
                actions=configs.actions,
                environment=configs.environment,
                database=configs.database,
            )
            handle = MasPod.remote(
                pod_id=pod_id,
                pod_config=pod_cfg,
                resource_maps=resource_maps,
                controller_class=self._controller_class,
            )
            pod_handles[pod_id] = handle

        self._pod_id_to_pod = pod_handles
        logger.info(f"Created {len(self._pod_id_to_pod)} MasPod handles.")

        all_handles = list(self._pod_id_to_pod.values())
        for batch_start in range(0, len(all_handles), self._init_batch_size):
            batch = all_handles[batch_start : batch_start + self._init_batch_size]
            await asyncio.gather(
                *[handle.init.remote(model_router_config=self._model_router_config) for handle in batch]
            )
            logger.info(f"Initialized Pod batch {batch_start // self._init_batch_size + 1}...")

        agent_id_to_pod: Dict[str, MasPod] = {}
        get_ids_tasks = [handle.forward.remote("get_agent_ids") for handle in all_handles]
        results = await asyncio.gather(*get_ids_tasks)
        for pod_handle, agent_ids_list in zip(all_handles, results):
            for agent_id in agent_ids_list:
                agent_id_to_pod[agent_id] = pod_handle
        logger.info("Agent to Pod map initialized.")
        self._agent_id_to_pod = agent_id_to_pod

        await self.save_to_db(scope="all")

    async def post_init(self, system_handle: System, pod_manager_handle: ActorHandle) -> None:
        """
        Distribute runtime handles to pods after the manager has been created.

        Args:
            system_handle (System): Reference to the global system service.
            pod_manager_handle (ActorHandle): Reference to this pod manager (local or remote).
        """
        self._system_handle = system_handle
        self._self_handle = pod_manager_handle

        await asyncio.gather(
            *[pod.post_init.remote(system_handle, self._self_handle) for pod in self._pod_id_to_pod.values()]
        )
        logger.info("All MasPods post-initialized with ModelRouter and System handles.")

    async def save_to_db(self, scope: Literal["all", "agents", "action", "environment"] = "agents") -> None:
        """
        Save the state of agents, actions, or environment to the database.

        Args:
            scope (Literal["all", "agents", "action", "environment"]): Specifies which components to save.
                - "all": Save agents, environment, and actions.
                - "agents": Save only agent states. (Default)
                - "action": Save only action states.
                - "environment": Save only environment states.

        Raises:
            ValueError: If an invalid scope is provided.
        """

        if scope == "agents":
            try:
                await asyncio.gather(
                    *[pod.forward.remote("save_to_db", "agents") for pod in self._pod_id_to_pod.values()]
                )
                logger.info("All agent data saved to database successfully.")
            except Exception as exc:
                logger.error(f"Failed to save agent data to database: {exc}", exc_info=True)

        elif scope == "all":
            pods = list(self._pod_id_to_pod.values())

            save_tasks = []

            representative_pod = pods[0]
            save_tasks.append(representative_pod.forward.remote("save_to_db", "all"))

            for pod in pods[1:]:
                save_tasks.append(pod.forward.remote("save_to_db", "agents"))

            try:
                await asyncio.gather(*save_tasks)
                logger.info("All data saved to database successfully.")
            except Exception as exc:
                logger.error(f"Failed to save all data to database: {exc}", exc_info=True)

        elif scope in ["action", "environment"]:

            representative_pod = next(iter(self._pod_id_to_pod.values()))
            try:
                await representative_pod.forward.remote("save_to_db", scope)
                logger.info(f"{scope.capitalize()} data saved to database successfully.")
            except Exception as exc:
                logger.error(f"Failed to save {scope} data to database: {exc}", exc_info=True)

    async def load_from_db(self) -> None:
        """
        Load the state of agents, actions, and environment from the database.
        """
        try:
            await asyncio.gather(*[pod.forward.remote("load_from_db") for pod in self._pod_id_to_pod.values()])
            logger.info("All data loaded from database successfully.")
        except Exception as exc:
            logger.error(f"Failed to load data from database: {exc}", exc_info=True)

    async def _create_new_pod(self) -> MasPod:
        """
        Create and initialize a new pod when existing ones are full.

        Returns:
            MasPod: Handle to the newly created pod actor.
        """
        pod_id = f"pod_{len(self._pod_id_to_pod)}"
        logger.info(f"Creating a new pod '{pod_id}' as all others are full.")

        pod_cfg = PodConfig(
            agent_templates=self._configs.agent_templates,
            agents=[],
            actions=self._configs.actions,
            environment=self._configs.environment,
            database=self._configs.database,
        )

        handle = MasPod.remote(
            pod_id=pod_id,
            pod_config=pod_cfg,
            resource_maps=self._resource_maps,
            controller_class=self._controller_class,
        )

        await handle.init.remote(model_router_config=self._model_router_config)
        await handle.post_init.remote(self._system_handle, self._self_handle)

        self._pod_id_to_pod[pod_id] = handle
        logger.info(f"New pod '{pod_id}' created and initialized successfully.")
        return handle

    async def step_agent(self) -> None:
        """
        Advance every managed pod by one step.

        Returns:
            None
        """
        await asyncio.gather(*[pod.forward.remote("step_agent") for pod in self._pod_id_to_pod.values()])

    async def deliver_message(self, to_id: str, message: Message) -> bool:
        """
        Deliver a message to the pod hosting the specified agent.

        Args:
            to_id (str): Identifier of the recipient agent.
            message (Message): Message to deliver.

        Returns:
            bool: True when the message is delivered successfully.
        """
        if to_id not in self._agent_id_to_pod:
            logger.error(f"Agent ID '{to_id}' not found in any Pod.")
            return False

        pod = self._agent_id_to_pod[to_id]
        return await pod.forward.remote("deliver_message", to_id, message)

    async def run_agent_method(
        self, agent_id: str, component_name: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a component method on an agent managed by a pod.

        Args:
            agent_id (str): Identifier of the target agent.
            component_name (str): Component that exposes the method.
            method_name (str): Method name to execute.
            *args (Any): Positional arguments forwarded to the method.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            Any: Result produced by the remote method.

        Raises:
            ValueError: If the agent cannot be located.
        """
        if agent_id not in self._agent_id_to_pod:
            raise ValueError(f"Agent ID '{agent_id}' not found in any Pod.")

        pod = self._agent_id_to_pod[agent_id]
        return await pod.forward.remote("run_agent_method", agent_id, component_name, method_name, *args, **kwargs)

    async def add_agent(self, agent_id: str, template_name: str, data: Dict[str, Any]) -> bool:
        """
        Add an agent to an existing pod or provision a new pod when necessary.

        Args:
            agent_id (str): Identifier for the new agent.
            template_name (str): Template name used for instantiation.
            data (Dict[str, Any]): Initialization payload for the agent.

        Returns:
            bool: True when the agent is added successfully.
        """
        if agent_id in self._agent_id_to_pod:
            logger.error(f"Agent ID '{agent_id}' already exists in the system.")
            return False

        target_pod: Optional[MasPod] = None
        for pod in self._pod_id_to_pod.values():
            agent_count = await pod.forward.remote("get_agent_count")
            if agent_count < self._pod_size:
                target_pod = pod
                break

        if target_pod is None:
            target_pod = await self._create_new_pod()

        success = await target_pod.forward.remote("add_agent", agent_id, template_name, data)
        if success:
            self._agent_id_to_pod[agent_id] = target_pod
            logger.info(f"Agent '{agent_id}' successfully added to its pod.")
        else:
            logger.error(f"Failed to add agent '{agent_id}' to a pod.")

        return success

    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent and terminate empty pods when appropriate.

        Args:
            agent_id (str): Identifier of the agent to remove.

        Returns:
            bool: True when the agent is removed successfully.
        """
        target_pod = self._agent_id_to_pod.get(agent_id)
        if not target_pod:
            logger.warning(f"Agent '{agent_id}' not found in any pod. Cannot remove.")
            return False

        success = await target_pod.forward.remote("remove_agent", agent_id)
        if not success:
            logger.error(f"Failed to remove agent '{agent_id}' from its pod.")
            return False

        del self._agent_id_to_pod[agent_id]
        logger.info(f"Agent '{agent_id}' removed from manager's tracking map.")

        # agent_count = await target_pod.forward.remote("get_agent_count")
        # if agent_count == 0:
        #     pod_id_to_remove = next(
        #         (pod_id for pod_id, handle in self._pod_id_to_pod.items() if handle == target_pod),
        #         None,
        #     )
        #     if pod_id_to_remove:
        #         logger.info(f"Pod '{pod_id_to_remove}' is now empty. Terminating actor.")
        #         ray.kill(target_pod)
        #         del self._pod_id_to_pod[pod_id_to_remove]
        #         logger.info(f"Pod '{pod_id_to_remove}' terminated and removed from manager.")

        return True

    async def make_snapshot(self) -> bool:
        """
        Trigger snapshot creation across every pod.

        Returns:
            bool: True when all pods succeed; otherwise False.
        """
        logger.info("Triggering snapshot...")

        await self.save_to_db(scope="all")

        if not self._adapters:
            logger.warning("No adapters registered.")
            return False

        snapshot_tasks = []
        adapter_names_with_snapshot = []

        current_tick = await self._system_handle.run("timer", "get_tick")

        for name, adapter in self._adapters.items():
            if hasattr(adapter, "snapshot") and asyncio.iscoroutinefunction(adapter.snapshot):
                snapshot_tasks.append(adapter.snapshot(tick=current_tick))
                adapter_names_with_snapshot.append(name)
            else:
                logger.warning(f"Adapter '{name}' does not support 'snapshot' method. Skipping.")

        if not snapshot_tasks:
            logger.info("No adapters with 'snapshot' functionality found.")
            return False

        try:
            results = await asyncio.gather(*snapshot_tasks, return_exceptions=True)

            overall_success = True

            for i, result in enumerate(results):
                adapter_name = adapter_names_with_snapshot[i]
                if isinstance(result, Exception):
                    logger.error(
                        f"Snapshot creation for adapter '{adapter_name}' failed with an exception.",
                        exc_info=result,
                    )
                    overall_success = False

            return overall_success

        except Exception as exc:
            logger.error(f"Unexpected error during snapshot creation: {exc}", exc_info=True)
            return False

    async def rollback_to_tick(self, tick: int) -> bool:
        """
        Roll back every pod to the specified tick.

        Args:
            tick (int): Simulation tick to restore.

        Returns:
            bool: True when all pods succeed; otherwise False.
        """

        logger.info(f"Initiating rollback to tick {tick}...")

        if not self._adapters:
            logger.warning("No adapters registered. Rollback is trivially successful.")
            return True

        rollback_tasks = []
        adapter_names_with_undo = []
        for name, adapter in self._adapters.items():
            if hasattr(adapter, "undo") and asyncio.iscoroutinefunction(adapter.undo):
                rollback_tasks.append(adapter.undo(tick=tick))
                adapter_names_with_undo.append(name)
            else:
                logger.warning(f"Adapter '{name}' does not support 'undo' method. Skipping.")

        if not rollback_tasks:
            logger.info("No adapters with 'undo' functionality found. Rollback complete.")
            return True

        results = await asyncio.gather(*rollback_tasks, return_exceptions=True)

        overall_success = True
        for i, result in enumerate(results):
            adapter_name = adapter_names_with_undo[i]
            if isinstance(result, Exception):
                logger.error(
                    f"Rollback for adapter '{adapter_name}' failed with an exception.",
                    exc_info=result,
                )
                overall_success = False
            elif not result:
                logger.error(f"Rollback for adapter '{adapter_name}' returned a failure status (False).")
                overall_success = False
            else:
                logger.info(f"Adapter '{adapter_name}' successfully rolled back.")
        if overall_success:
            await self.load_from_db()

        return overall_success

    async def close(self) -> bool:
        """
        Close all pods and release shared resources.

        Returns:
            bool: True when every resource closes successfully.
        """
        is_ok = True
        all_handles = list(self._pod_id_to_pod.values())
        try:
            for batch_start in range(0, len(all_handles), self._init_batch_size):
                batch = all_handles[batch_start : batch_start + self._init_batch_size]
                await asyncio.gather(*[handle.close.remote() for handle in batch])
                logger.info(f"Closed Pod batch {batch_start // self._init_batch_size + 1}...")
            logger.info("All MasPods have been closed.")
        except Exception as exc:
            logger.error(f"Exception {exc} occurred while closing MasPods.")
            is_ok = False
        try:
            if self._model_router:
                await self._model_router.close()
                logger.info("ModelRouter has been closed.")
        except Exception as exc:
            logger.error(f"Exception {exc} occurred while closing the ModelRouter.")
            is_ok = False
        try:
            for name, adapter in self._adapters.items():
                await adapter.disconnect()
                logger.info(f"PodManager's {name} adapter client has been closed.")
            await close_connection_pools(self._connection_pools)
            logger.info("PodManager's database connection pools have been closed.")
        except Exception as exc:
            logger.error(f"Exception {exc} occurred while closing PodManager database resources.")
            is_ok = False
        return is_ok


@ray.remote
class PodManager(PodManagerImpl):
    """Ray actor wrapper around PodManagerImpl."""

    pass
