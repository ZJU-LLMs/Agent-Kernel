"""Reflect component that coordinates reflection plugin."""

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import ReflectPlugin

__all__ = ["ReflectComponent"]

logger = get_logger(__name__)


class ReflectComponent(AgentComponent[ReflectPlugin]):
    """Component container for reflection plugin."""

    COMPONENT_NAME = "reflect"

    def __init__(self) -> None:
        """Initialize the reflect component."""
        super().__init__()

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
