"""State component that maintains state via plugin."""

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import StatePlugin

__all__ = ["StateComponent"]

logger = get_logger(__name__)


class StateComponent(AgentComponent[StatePlugin]):
    """Component container for state plugin."""

    COMPONENT_NAME = "state"

    def __init__(self) -> None:
        """Initialize the state component."""
        super().__init__()

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
