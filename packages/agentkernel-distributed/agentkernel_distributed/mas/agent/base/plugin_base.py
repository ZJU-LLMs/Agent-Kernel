"""Base classes for agent plugins used by the MAS runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, TypeVar

from ....types.schemas.message import Message

if TYPE_CHECKING:
    from ..agent import Agent
    from ..components import (
        InvokeComponent,
        PerceiveComponent,
        PlanComponent,
        ProfileComponent,
        ReflectComponent,
        StateComponent,
    )
    from .component_base import AgentComponent

T = TypeVar("T", bound="AgentPlugin")

__all__ = [
    "AgentPlugin",
    "PerceivePlugin",
    "PlanPlugin",
    "ReflectPlugin",
    "StatePlugin",
    "ProfilePlugin",
    "InvokePlugin",
]


class AgentPlugin(ABC):
    """Base class for all agent plugins."""

    COMPONENT_TYPE = "base"

    def __init__(self) -> None:
        """Initialize the plugin without an attached component."""
        self._component: Optional["AgentComponent[Any]"] = None

    @property
    def component(self) -> Optional["AgentComponent[Any]"]:
        """
        Return the component that owns this plugin.

        Returns:
            Optional[AgentComponent[Any]]: Owning component when attached.
        """
        return self._component

    @component.setter
    def component(self, component: Optional["AgentComponent[Any]"]) -> None:
        """
        Associate the plugin with a component.

        Args:
            component: Optional[AgentComponent[Any]]: Owning component instance or None.
        """
        self._component = component

    @property
    def agent(self) -> Optional["Agent"]:
        """
        Return the agent that owns this plugin's component.

        Returns:
            Optional[Agent]: Agent instance when attached, otherwise None.
        """
        if self._component is not None:
            return self._component.agent
        return None

    def peer_plugin(self, name: str, plugin_type: Type[T]) -> Optional[T]:
        """
        Retrieve a peer plugin from the same agent with type-safe access.

        This method provides a convenient way to access other plugins within
        the same agent, with full type hints for the returned plugin instance.

        Args:
            name (str): Name of the component to retrieve the plugin from
                (e.g., "perceive", "profile", "state", "plan", "invoke", "reflect").
            plugin_type (Type[T]): Expected plugin class type for type inference
                and runtime validation.

        Returns:
            Optional[T]: The plugin instance cast to the specified type if found
                and type-matched, otherwise None.

        Example:
            >>> perceive = self.peer_plugin("perceive", MyPerceivePlugin)
            >>> if perceive:
            ...     messages = perceive.get_messages()
        """
        if self._component is None or self._component.agent is None:
            return None
        component = self._component.agent.get_component(name)
        if component is not None:
            plugin = component.get_plugin()
            if isinstance(plugin, plugin_type):
                return plugin
        return None

    @abstractmethod
    async def init(self) -> None:
        """Perform post-construction initialization for the plugin."""

    @abstractmethod
    async def execute(self, current_tick: int) -> None:
        """
        Execute plugin logic for the given simulation tick.

        Args:
            current_tick (int): Simulation tick during which execution occurs.
        """

    async def save_to_db(self) -> None:
        """
        (Optional) Save the plugin's persistent state to the database.

        Subclasses that require persistence should override this method.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"Plugin {self.__class__.__name__} does not implement 'save_to_db'")

    async def load_from_db(self) -> None:
        """
        (Optional) Load the plugin's persistent state from the database.

        Subclasses that require persistence should override this method.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"Plugin {self.__class__.__name__} does not implement 'load_from_db'")


class PerceivePlugin(AgentPlugin):
    """Base class for perception plugins."""

    COMPONENT_TYPE = "perceive"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["PerceiveComponent"] = None

    @abstractmethod
    async def add_message(self, message: Message) -> None:
        """
        Add a perception message to the plugin.

        Args:
            message (Message): Arbitrary payload to incorporate into perception state.
        """


class PlanPlugin(AgentPlugin):
    """Base class for planning plugins."""

    COMPONENT_TYPE = "plan"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["PlanComponent"] = None


class ReflectPlugin(AgentPlugin):
    """Base class for reflection plugins."""

    COMPONENT_TYPE = "reflect"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["ReflectComponent"] = None


class StatePlugin(AgentPlugin):
    """Base class for state plugins."""

    COMPONENT_TYPE = "state"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["StateComponent"] = None

    @abstractmethod
    async def set_state(self, key: str, value: Any) -> None:
        """
        Update a state entry within the plugin.

        Args:
            key (str): State key to update.
            value (Any): Associated value to store.
        """

    @abstractmethod
    async def get_state(self, key: str) -> Any:
        """
        Retrieve a state entry from the plugin.

        Args:
            key (str): State key to retrieve.

        Returns:
            Any: The value associated with the key, or None if not found.
        """


class ProfilePlugin(AgentPlugin):
    """Base class for profile plugins."""

    COMPONENT_TYPE = "profile"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["ProfileComponent"] = None

    @abstractmethod
    async def set_profile(self, key: str, value: Any) -> None:
        """
        Update a profile entry within the plugin.

        Args:
            key (str): Profile key to update.
            value (Any): Associated value to store.
        """

    @abstractmethod
    async def get_profile(self, key: str) -> Any:
        """
        Retrieve a profile entry from the plugin.

        Args:
            key (str): Profile key to retrieve.

        Returns:
            Any: The value associated with the key, or None if not found.
        """


class InvokePlugin(AgentPlugin):
    """Base class for action plugins."""

    COMPONENT_TYPE = "invoke"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["InvokeComponent"] = None
