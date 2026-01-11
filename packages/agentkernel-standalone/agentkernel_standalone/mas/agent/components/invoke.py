"""Invoke component that manages action-execution plugin."""

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import InvokePlugin

logger = get_logger(__name__)

__all__ = ["InvokeComponent"]


class InvokeComponent(AgentComponent[InvokePlugin]):
    """Component container for action-execution plugin."""

    COMPONENT_NAME = "invoke"

    def __init__(self) -> None:
        """Initialize the invoke component."""
        super().__init__()

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
