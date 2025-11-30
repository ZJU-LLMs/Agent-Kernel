"""State component that maintains state via plugin."""

from typing import Any, Dict
import copy

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import StatePlugin
from . import *  # noqa: F401,F403

__all__ = ["StateComponent"]

logger = get_logger(__name__)


class StateComponent(AgentComponent[StatePlugin]):
    """Proxy that orchestrates state plugin and snapshots plugin's outputs."""

    COMPONENT_NAME = "state"

    def __init__(self) -> None:
        """Initialize in-memory storage for state data."""
        super().__init__()
        self._state_data: Dict[str, Any] = {}

    @property
    def state_data(self) -> Dict[str, Any]:
        """Return the latest state data emitted by the plugin."""
        return self._state_data

    @state_data.setter
    def state_data(self, state_data: Dict[str, Any]) -> None:
        """
        Replace the stored state data.

        Args:
            state_data (Dict[str, Any]): New state mapping provided by the plugin.
        """
        self._state_data = state_data

    async def set_state(self, key: str, value: Any) -> None:
        """
        Update an individual state entry via the underlying plugin.

        Args:
            key (str): State key to update.
            value (Any): Associated value stored by the plugin.
        """
        self._state_data[key] = value
        await self._plugin.set_state(key, value)

    async def execute(self, current_tick: int) -> None:
        """
        Execute the state plugin for the given simulation tick.

        Args:
            current_tick (int): Simulation tick used when invoking the plugin.
        """
        if not self._plugin:
            logger.warning("No plugin found in StateComponent.")
            return
        await self._plugin.execute(current_tick)

        self._state_data = self._plugin.state_data
