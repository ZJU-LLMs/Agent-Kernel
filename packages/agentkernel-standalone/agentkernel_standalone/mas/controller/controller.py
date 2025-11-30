"""Default controller implementation coordinating MAS components."""

import asyncio
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from ...mas.action.action import Action
from ...mas.environment.environment import Environment
from ...mas.system.system import System
from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter
from ...types.schemas.action import ActionResult
from ...types.schemas.message import Message
from ..agent.agent_manager import AgentManager
from .base import BaseController

logger = get_logger(__name__)


class ControllerImpl(BaseController):
    """Default controller that wires agents, environment, actions, and pods."""

    def __init__(
        self,
        agent_manager: Optional["AgentManager"] = None,
        action: Optional[Action] = None,
        environment: Optional[Environment] = None,
        adapters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the controller with optional component references.

        Args:
            agent_manager (Optional["AgentManager"]): Manager overseeing local agents.
            action (Optional[Action]): Action proxy used to execute component methods.
            environment (Optional[Environment]): Environment proxy coordinating world state.
            adapters (Optional[Dict[str, Any]]): Optional mapping of adapter instances.
        """
        super().__init__(
            agent_manager=agent_manager,
            action=action,
            environment=environment,
            adapters=adapters,
        )

    async def post_init(self, system: Optional[System], model_router: Optional[ModelRouter]) -> None:
        """
        Finalize initialization by capturing system-level dependencies.

        Args:
            system (Optional[System]): System service used for global coordination.
            model_router (Optional[ModelRouter]): Router for model-related services.
        """
        if system is None:
            logger.error("System is not in controller post_init")
        self._system = system
        self._model_router = model_router

    async def step_agent(self) -> None:
        """
        Advance the agent manager by one tick.

        Raises:
            RuntimeError: If the agent manager is not available.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        current_tick = await self.run_system("timer", "get_tick")
        await self._agent_manager.run_tick(current_tick)

    async def run_agent_method(
        self, agent_id: str, component_name: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a component method on a specific agent.

        Args:
            agent_id (str): Identifier of the agent to target.
            component_name (str): Component exposing the desired method.
            method_name (str): Name of the method to execute.
            *args (Any): Positional arguments forwarded to the method.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            Any: Result returned by the executed method.

        """
        return await self._agent_manager.run_agent_method(agent_id, component_name, method_name, *args, **kwargs)

    async def load_from_db(self) -> None:
        """
        Load the persistent state of all managed components (agents, environment,
        and actions) from the database concurrently.
        """
        logger.info("Controller: Starting to load state from database...")
        load_tasks = []

        if self._agent_manager:
            load_tasks.append(self._agent_manager.load_from_db())
        else:
            logger.warning("Controller: AgentManager is not available, skipping load.")

        if self._environment:
            load_tasks.append(self._environment.load_from_db())
        else:
            logger.warning("Controller: Environment is not available, skipping load.")

        if self._action:
            load_tasks.append(self._action.load_from_db())
        else:
            logger.warning("Controller: Action is not available, skipping load.")

        if not load_tasks:
            logger.info("Controller: No components available to load state from database.")
            return

        try:
            await asyncio.gather(*load_tasks)
            logger.info("Controller: All component states loaded successfully.")
        except Exception as e:
            logger.error(f"Controller: Error during concurrent state load: {e}", exc_info=True)

    async def save_to_db(self, scope: Literal["all", "agents", "action", "environment"] = "agents") -> None:
        """
        Save the persistent state of managed components to the database concurrently.

        Args:
            scope (Literal["all", "agents", "action", "environment"]): Specifies which components to save.
                - "all": Save agents, environment, and actions.
                - "agents": Save only agent states. (Default)
                - "action": Save only action states.
                - "environment": Save only environment states.
        """
        logger.info(f"Controller: Starting to save state to database (scope: {scope})...")
        save_tasks = []

        if scope in ("all", "agents"):
            if self._agent_manager:
                save_tasks.append(self._agent_manager.save_to_db())
            else:
                logger.warning("Controller: AgentManager is not available, skipping save.")

        if scope in ("all", "environment"):
            if self._environment:
                save_tasks.append(self._environment.save_to_db())
            else:
                logger.warning("Controller: Environment is not available, skipping save.")

        if scope in ("all", "action"):
            if self._action:
                save_tasks.append(self._action.save_to_db())
            else:
                logger.warning("Controller: Action is not available, skipping save.")

        if not save_tasks:
            logger.info(f"Controller: No components available to save for scope '{scope}'.")
            return

        try:
            await asyncio.gather(*save_tasks)
            logger.info(f"Controller: All component states for scope '{scope}' saved successfully.")
        except Exception as e:
            logger.error(f"Controller: Error during concurrent state save (scope: {scope}): {e}", exc_info=True)

    def get_agent_ids(self) -> List[str]:
        """
        Retrieve all agent identifiers managed locally.

        Returns:
            List[str]: Identifiers of managed agents.

        Raises:
            RuntimeError: If the agent manager is not available.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        return self._agent_manager.get_agent_ids()

    def get_agent_count(self) -> int:
        """
        Retrieve the number of managed agents.

        Returns:
            int: Count of active agents.

        Raises:
            RuntimeError: If the agent manager is not available.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        return self._agent_manager.get_agent_count()


    async def deliver_message(self, to_id: str, message: Message) -> bool:
        """
        Deliver a message to a specific agent.

        Args:
            to_id (str): Recipient agent identifier.
            message (Message): Message payload to deliver.

        Returns:
            bool: True when the message is delivered successfully.

        Raises:
            RuntimeError: If the agent manager is not available.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        return await self._agent_manager.deliver_message(to_id, message)

    async def add_agent(self, agent_id: str, template_name: str, data: Dict[str, Any]) -> bool:
        """
        Add an agent directly via the local agent manager.

        Args:
            agent_id (str): Identifier for the new agent.
            template_name (str): Template used to instantiate the agent.
            data (Dict[str, Any]): Initialization payload forwarded to the agent.

        Returns:
            bool: True when the agent is added successfully.

        Raises:
            RuntimeError: If the agent manager is not available.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        return await self._agent_manager.add_agent(agent_id, template_name, data)

    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent directly via the local agent manager.

        Args:
            agent_id (str): Identifier of the agent to remove.

        Returns:
            bool: True when the agent is removed successfully.

        Raises:
            RuntimeError: If the agent manager is not available.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        return await self._agent_manager.remove_agent(agent_id)

    async def list_environment_components(self) -> List[str]:
        """
        List all registered environment components.

        Returns:
            List[str]: Names of available environment components.
        """
        if self._environment is None:
            return []
        return self._environment.list_components()

    async def run_environment(self, component_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a method on an environment component.

        Args:
            component_name (str): Environment component exposing the method.
            method_name (str): Name of the method to execute.
            *args (Any): Positional arguments forwarded to the environment component.
            **kwargs (Any): Keyword arguments forwarded to the environment component.

        Returns:
            Any: Result produced by the environment method.

        Raises:
            RuntimeError: If the environment proxy is unavailable.
        """
        if not self._environment:
            raise RuntimeError("Environment is not initialized in the System.")
        return await self._environment.run(component_name, method_name, *args, **kwargs)

    async def list_action_components(self) -> List[str]:
        """
        List all registered action components.

        Returns:
            List[str]: Names of available action components.
        """
        if self._action is None:
            return []
        return self._action.list_components()

    async def run_action(self, component_name: str, method_name: str, **kwargs: Any) -> ActionResult:
        """
        Execute a method on an action component.

        Args:
            component_name (str): Action component exposing the method.
            method_name (str): Name of the method to execute.
            **kwargs (Any): Keyword arguments forwarded to the action component.

        Returns:
            ActionResult: Standardized result of the action execution.

        Raises:
            RuntimeError: If the action proxy is unavailable.
        """
        if not self._action:
            raise RuntimeError("Action is not initialized.")
        return await self._action.run(component_name, method_name, **kwargs)

    async def get_available_actions(
        self, method_names: Optional[Union[str, List[str]]] = None
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
        """
        Gather all agent-callable methods across components.

        Args:
            method_names (Optional[Union[str, List[str]]]): Optional filter for specific method names.

        Returns:
            Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]: Tuple containing method information and component mapping.

        Raises:
            RuntimeError: If the action proxy is unavailable.
        """
        if not self._action:
            raise RuntimeError("Action is not initialized.")

        method_info_dict: Dict[str, Dict[str, Any]] = {}
        method_to_component_dict: Dict[str, str] = {}
        component_names = self._action.list_components()
        for comp_name in component_names:
            all_comp_methods = self._action.list_comp_methods_names(comp_name, annotation_type="AgentCall")

            if method_names:
                if isinstance(method_names, str):
                    comp_methods = [method_names] if method_names in (all_comp_methods or []) else []
                else:
                    comp_methods = [
                        method for method in method_names if all_comp_methods and method in all_comp_methods
                    ]
            else:
                comp_methods = all_comp_methods

            methods = await self._action.get_agent_call_methods(comp_name, comp_methods)

            for method_info in methods:
                method_name = method_info.pop("name", None)
                if method_name:
                    method_info_dict[method_name] = method_info
                    method_to_component_dict[method_name] = comp_name

        return method_info_dict, method_to_component_dict

    async def run_system(self, component_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a method on a system-level component.

        Args:
            component_name (str): Name of the system component to target.
            method_name (str): Method to invoke on the component.
            *args (Any): Positional arguments forwarded to the component.
            **kwargs (Any): Keyword arguments forwarded to the component.

        Returns:
            Any: Result produced by the system component.

        Raises:
            RuntimeError: If the system handle is unavailable.
        """
        if not self._system:
            raise RuntimeError("System is not initialized.")
        return await self._system.run(component_name, method_name, *args, **kwargs)
    

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

        current_tick = await self._system.run("timer", "get_tick")

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

    async def close(self) -> None:
        """Release resources held by the controller."""
        if self._environment:
            if hasattr(self._environment, "close"):
                self._environment.close()
            self._environment = None
        if self._action:
            if hasattr(self._action, "close"):
                self._action.close()
            self._action = None
        if self._system:
            self._system = None
        if self._agent_manager:
            if hasattr(self._agent_manager, "close"):
                await self._agent_manager.close()
            self._agent_manager = None
        if self._model_router:
            await self._model_router.close()
            self._model_router = None


class Controller(ControllerImpl):
    """Backwards-compatible alias for the default controller implementation."""
