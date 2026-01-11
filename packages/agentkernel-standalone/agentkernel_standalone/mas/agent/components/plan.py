"""Plan component that coordinates planning plugin."""

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import PlanPlugin

__all__ = ["PlanComponent"]

logger = get_logger(__name__)


class PlanComponent(AgentComponent[PlanPlugin]):
    """Component container for planning plugin."""

    COMPONENT_NAME = "plan"

    def __init__(self) -> None:
        """Initialize the plan component."""
        super().__init__()

    async def execute(self, current_tick: int) -> None:
        """
        Execute the planning plugin for the given simulation tick.

        Args:
            current_tick (int): Simulation tick used when invoking the plugin.
        """
        if not self._plugin:
            logger.warning("No plugin found in PlanComponent.")
            return

        await self._plugin.execute(current_tick)
