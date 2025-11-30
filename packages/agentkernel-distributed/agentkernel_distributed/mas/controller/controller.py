"""Default controller implementation coordinating MAS components."""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Tuple, Union

from ...mas.action.action import Action
from ...mas.environment.environment import Environment
from ...mas.system.system import System
from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter
from ...types.schemas.action import ActionResult
from ...types.schemas.message import Message
from ..agent.agent_manager import AgentManager
from .base import BaseController

if TYPE_CHECKING:
    from ..pod.pod_manager_base import BasePodManager

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
            agent_manager (Optional[AgentManager]): Manager overseeing local agents.
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

    async def post_init(
        self, system: Optional[System], model_router: Optional[ModelRouter], pod_manager: Optional["BasePodManager"]
    ) -> None:
        """
        Finalize initialization by capturing system-level dependencies.

        Args:
            system (Optional[System]): System service used for global coordination.
            model_router (Optional[ModelRouter]): Router for model-related services.
            pod_manager (Optional[BasePodManager]): Remote pod manager handle.
        """
        if system is None:
            logger.error("System is not in controller post_init")
        self._system = system
        self._model_router = model_router
        self._pod_manager = pod_manager

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

        Raises:
            RuntimeError: If the agent manager or pod manager handle is unavailable.
        """
        if not self._agent_manager:
            raise RuntimeError("AgentManager is not initialized in the System.")
        if agent_id in self._agent_manager.get_agent_ids():
            return await self._agent_manager.run_agent_method(agent_id, component_name, method_name, *args, **kwargs)
        if not self._pod_manager:
            raise RuntimeError("PodManager handle is not available in this Controller.")
        return await self._pod_manager.run_agent_method.remote(agent_id, component_name, method_name, *args, **kwargs)

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

    async def request_add_agent(self, agent_id: str, template_name: str, data: Dict[str, Any]) -> bool:
        """
        Forward a request to add an agent via the pod manager.

        Args:
            agent_id (str): Identifier for the new agent.
            template_name (str): Template used to instantiate the agent.
            data (Dict[str, Any]): Initialization payload forwarded to the agent.

        Returns:
            bool: True when the agent is scheduled successfully.

        Raises:
            RuntimeError: If the pod manager handle is unavailable.
        """
        if not self._pod_manager:
            raise RuntimeError("PodManager handle is not available in this Controller.")

        return await self._pod_manager.add_agent.remote(agent_id, template_name, data)

    async def request_remove_agent(self, agent_id: str) -> bool:
        """
        Forward a request to remove an agent via the pod manager.

        Args:
            agent_id (str): Identifier of the agent to remove.

        Returns:
            bool: True when the removal request succeeds.

        Raises:
            RuntimeError: If the pod manager handle is unavailable.
        """
        if not self._pod_manager:
            raise RuntimeError("PodManager handle is not available in this Controller.")
        return await self._pod_manager.remove_agent.remote(agent_id)

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

    async def get_available_actions(self, method_names: Optional[Union[str, List[str]]] = None) -> List[Dict[str, Any]]:
        """
        get all available agent call methods across all components.

        Args:
            method_names (Optional[Union[str, List[str]]]): Optional method name or list of method names to filter.

        Returns:
            A dictionary mapping component names to their available methods.

        Raises:
            RuntimeError: If the action proxy is unavailable.
        """
        if not self._action:
            raise RuntimeError("Action is not initialized.")

        available_actions = {}
        component_names = self._action.list_components()
        for comp_name in component_names:
            all_comp_methods = self._action.list_comp_methods_names(comp_name)

            if method_names:
                # Filter method_names to get only those belonging to this component
                if isinstance(method_names, str):
                    comp_methods = [method_names] if method_names in all_comp_methods else []
                else:
                    comp_methods = [method for method in method_names if method in all_comp_methods]
            else:
                comp_methods = all_comp_methods

            methods = await self._action.get_agent_call_methods(comp_name, comp_methods)

            for method_info in methods:
                method_name = method_info.get("name")
                if method_name:
                    if comp_name not in available_actions:
                        available_actions[comp_name] = {}
                    available_actions[comp_name][method_name] = method_info

        return available_actions

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

    async def close(self) -> None:
        """
        Release resources held by the controller.

        Returns:
            None
        """
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
            self._model_router = None


class Controller(ControllerImpl):
    """Backwards-compatible alias for the default controller implementation."""
