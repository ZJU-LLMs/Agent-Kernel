"""Abstract contract for controller implementations coordinating the MAS runtime."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ...mas.action.action import Action
from ...mas.environment.environment import Environment
from ...mas.system.system import System
from ...toolkit.models.router import ModelRouter
from ...types.schemas.action import ActionResult
from ...types.schemas.message import Message
from ..agent.agent_manager import AgentManager

if TYPE_CHECKING:
    from ..pod.pod_manager_base import BasePodManager


class BaseController(ABC):
    """Define the lifecycle and coordination hooks required for controllers."""

    def __init__(
        self,
        agent_manager: Optional[AgentManager] = None,
        action: Optional[Action] = None,
        environment: Optional[Environment] = None,
        adapters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize shared references used by controller implementations.

        Args:
            agent_manager (Optional[AgentManager]): Manager providing access to local agents.
            action (Optional[Action]): Action proxy responsible for plugin execution.
            environment (Optional[Environment]): Environment proxy for component access.
            adapters (Optional[Dict[str, Any]]): Optional adapter mapping used for persistence.
        """
        self._agent_manager: Optional[AgentManager] = agent_manager
        self._environment: Optional[Environment] = environment
        self._action: Optional[Action] = action
        self._adapters: Optional[Dict[str, Any]] = adapters
        self._system: Optional[System] = None
        self._model_router: Optional[ModelRouter] = None
        self._pod_manager: Optional["BasePodManager"] = None

    @abstractmethod
    async def post_init(self, adapters: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        """
        Finalize setup after all components have been initialized.

        Args:
            adapters (Optional[Dict[str, Any]], optional): Optional adapter mapping shared across the system.
            **kwargs: Implementation-specific configuration parameters.
        """

    @abstractmethod
    async def step_agent(self) -> Any:
        """
        Advance the simulation by one tick for every managed agent.

        Returns:
            Any: Implementation-defined data gathered during the step.
        """

    @abstractmethod
    async def run_agent_method(
        self, agent_id: str, component_name: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a method on a specific agent component.

        Args:
            agent_id (str): Identifier of the target agent.
            component_name (str): Component that exposes the method.
            method_name (str): Name of the method to execute.

        Returns:
            Any: Result produced by the agent method.
        """

    @abstractmethod
    async def deliver_message(self, to_id: str, message: Message) -> bool:
        """
        Deliver a message to a specific agent.

        Args:
            to_id (str): Recipient agent identifier.
            message (Message): Message instance being delivered.

        Returns:
            bool: True when delivery succeeds, otherwise False.
        """

    @abstractmethod
    async def add_agent(self, agent_id: str, template_name: str, data: Dict[str, Any]) -> bool:
        """
        Add a new agent instance to the system.

        Args:
            agent_id (str): Identifier to assign to the new agent.
            template_name (str): Template used to instantiate the agent.
            data (Dict[str, Any]): Initialization payload for the agent.

        Returns:
            bool: True when the agent is created successfully.
        """

    @abstractmethod
    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the system.

        Args:
            agent_id (str): Identifier of the agent to remove.

        Returns:
            bool: True when the agent is removed successfully.
        """

    @abstractmethod
    async def run_environment(self, component_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a method on an environment component.

        Args:
            component_name (str): Name of the environment component.
            method_name (str): Method to invoke on the component.
            *args (Any): Positional arguments forwarded to the method.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            Any: Result produced by the environment method.
        """

    @abstractmethod
    async def run_action(self, component_name: str, method_name: str, **kwargs: Any) -> ActionResult:
        """
        Execute a method on an action component.

        Args:
            component_name (str): Name of the action component.
            method_name (str): Method to invoke on the component.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            ActionResult: Standardized result of the action execution.
        """

    @abstractmethod
    async def get_available_actions(
        self, component_name: str, method_name: Optional[Union[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Enumerate agent-callable methods for a component.

        Args:
            component_name (str): Name of the component that owns the methods.
            method_name (Optional[Union[str, List[str]]]): Optional filter for one or more method names.

        Returns:
            List[Dict[str, Any]]: Metadata describing the available methods.
        """

    @abstractmethod
    async def run_system(self, component_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a method on a system service component.

        Args:
            component_name (str): Name of the system component.
            method_name (str): Method to invoke on the component.
            *args (Any): Positional arguments forwarded to the method.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            Any: Result returned by the system component.
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Release all resources held by the controller.

        Returns:
            None
        """
