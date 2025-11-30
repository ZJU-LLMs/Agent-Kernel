"""Invoke component that manages action-execution plugin."""

from typing import List, Optional

from ....toolkit.logger import get_logger
from ....types.schemas.agent import ActionRecord, CurrentAction
from ..base.component_base import AgentComponent
from ..base.plugin_base import InvokePlugin
from . import *

logger = get_logger(__name__)

__all__ = ["InvokeComponent"]


class InvokeComponent(AgentComponent[InvokePlugin]):
    """Manage action plugin and expose plugin's execution state."""

    COMPONENT_NAME = "invoke"

    def __init__(self) -> None:
        """Initialize in-memory state for current and historical actions."""
        super().__init__()
        self._action_history: List[ActionRecord] = []
        self._current_action: Optional[CurrentAction] = None

    @property
    def action_history(self) -> List[ActionRecord]:
        """Return the list of historical action records."""
        return self._action_history

    @action_history.setter
    def action_history(self, action_history: List[ActionRecord]) -> None:
        """
        Replace the stored action history.

        Args:
            action_history (List[ActionRecord]): New action history sequence.
        """
        self._action_history = action_history

    @property
    def current_action(self) -> Optional[CurrentAction]:
        """Return the action currently in progress."""
        return self._current_action

    @current_action.setter
    def current_action(self, current_action: Optional[CurrentAction]) -> None:
        """
        Record the action currently being executed.

        Args:
            current_action (Optional[CurrentAction], optional): Action metadata tracked by the plugin.
        """
        self._current_action = current_action

    async def execute(self, current_tick: int) -> None:
        """
        Execute the action plugin for the given simulation tick.

        Args:
            current_tick (int): Simulation tick used when invoking the plugin.
        """
        if not self._plugin:
            logger.warning("No plugin found in InvokeComponent.")
            return

        await self._plugin.execute(current_tick)
        self._current_action = self._plugin.current_action
        self._action_history = self._plugin.action_history
