"""Base classes for agent plugins used by the MAS runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

from ....types.schemas.agent import ActionRecord, CurrentAction, PerceptionData
from ....types.schemas.message import Message

if TYPE_CHECKING:
    from ..components import (
        InvokeComponent,
        PerceiveComponent,
        PlanComponent,
        ProfileComponent,
        ReflectComponent,
        StateComponent,
    )
    from .component_base import AgentComponent

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
        self._perception: PerceptionData = {}

    @property
    def perception(self) -> PerceptionData:
        """Return the current perception data produced by the plugin."""
        return self._perception

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
        self._current_plan: Optional[Dict[str, Any]] = None
        self._current_step_index: int = 0

    @property
    def current_plan(self) -> Optional[Dict[str, Any]]:
        """Return the plan currently produced by the plugin."""
        return self._current_plan

    @property
    def current_step_index(self) -> int:
        """Return the planner's progress within the current plan."""
        return self._current_step_index


class ReflectPlugin(AgentPlugin):
    """Base class for reflection plugins."""

    COMPONENT_TYPE = "reflect"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["ReflectComponent"] = None
        self._recent_reflection: Dict[str, Any] = {}

    @property
    def recent_reflection(self) -> Dict[str, Any]:
        """Return the most recent reflection result."""
        return self._recent_reflection


class StatePlugin(AgentPlugin):
    """Base class for state plugins."""

    COMPONENT_TYPE = "state"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["StateComponent"] = None
        self._state_data: Dict[str, Any] = {}

    @property
    def state_data(self) -> Dict[str, Any]:
        """Return the latest state data maintained by the plugin."""
        return self._state_data

    @abstractmethod
    async def set_state(self, key: str, value: Any) -> None:
        """
        Update a state entry within the plugin.

        Args:
            key (str): State key to update.
            value (Any): Associated value to store.
        """


class ProfilePlugin(AgentPlugin):
    """Base class for profile plugins."""

    COMPONENT_TYPE = "profile"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["ProfileComponent"] = None
        self._profile_data: Dict[str, Any] = {}

    @property
    def profile_data(self) -> Dict[str, Any]:
        """Return the profile data maintained by the plugin."""
        return self._profile_data

    @abstractmethod
    async def set_profile(self, key: str, value: Any) -> None:
        """
        Update a profile entry within the plugin.

        Args:
            key (str): Profile key to update.
            value (Any): Associated value to store.
        """


class InvokePlugin(AgentPlugin):
    """Base class for action plugins."""

    COMPONENT_TYPE = "invoke"

    def __init__(self) -> None:
        super().__init__()
        self._component: Optional["InvokeComponent"] = None
        self._action_history: list[ActionRecord] = []
        self._current_action: Optional[CurrentAction] = None

    @property
    def action_history(self) -> list[ActionRecord]:
        """Return the recorded action history."""
        return self._action_history

    @property
    def current_action(self) -> Optional[CurrentAction]:
        """Return the action currently in progress."""
        return self._current_action
