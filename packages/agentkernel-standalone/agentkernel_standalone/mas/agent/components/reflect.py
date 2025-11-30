"""Agent component that coordinates reflection and memory plugins."""

from typing import Any, Dict

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import ReflectPlugin

__all__ = ["ReflectComponent"]

logger = get_logger(__name__)


class ReflectComponent(AgentComponent[ReflectPlugin]):
    """A component that manages the agent's reflection and memory."""

    COMPONENT_NAME = "reflect"

    def __init__(self) -> None:
        """Initialize the reflect component."""
        super().__init__()
        self._recent_reflection: Dict[str, Any] = {}

    @property
    def recent_reflection(self) -> Dict[str, Any]:
        """Return the most recent reflection payload."""
        return self._recent_reflection

    @recent_reflection.setter
    def recent_reflection(self, new_reflection: Dict[str, Any]) -> None:
        """
        Replace the cached reflection payload.

        Args:
            new_reflection (Dict[str, Any]): Reflection data provided by the plugin.
        """
        self._recent_reflection = new_reflection

    async def execute(self, current_tick: int) -> None:
        """
        Execute the reflection plugin for the given simulation tick.

        Args:
            current_tick (int): Simulation tick used when invoking the plugin.
        """
        if not self._plugin:
            logger.warning("No plugin found in ReflectComponent.")
            return

        await self._plugin.execute(current_tick)

        self._recent_reflection = self._plugin.recent_reflection
