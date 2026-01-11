"""Perceive component responsible for aggregating perception data."""

from ....toolkit.logger import get_logger
from ....types.schemas.message import Message
from ..base.component_base import AgentComponent
from ..base.plugin_base import PerceivePlugin

__all__ = ["PerceiveComponent"]

logger = get_logger(__name__)


class PerceiveComponent(AgentComponent[PerceivePlugin]):
    """Component container for perception plugin."""

    COMPONENT_NAME = "perceive"

    def __init__(self) -> None:
        """Initialize the perceive component."""
        super().__init__()

    async def add_message(self, message: Message) -> None:
        """
        Forward a message to the perception plugin.

        Args:
            message (Message): Message payload to deliver.
        """
        if self._plugin and hasattr(self._plugin, "add_message"):
            await self._plugin.add_message(message)

    async def execute(self, current_tick: int) -> None:
        """
        Execute the perception plugin for the given simulation tick.

        Args:
            current_tick (int): Simulation tick used when invoking the plugin.
        """
        if not self._plugin:
            logger.warning("No plugin found in PerceiveComponent.")
            return

        await self._plugin.execute(current_tick)
