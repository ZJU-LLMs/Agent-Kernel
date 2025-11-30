"""Perceive component responsible for aggregating perception data."""

from typing import Any, Optional

from ....toolkit.logger import get_logger
from ....types.schemas.agent import PerceptionData
from ....types.schemas.message import Message
from ..base.component_base import AgentComponent
from ..base.plugin_base import PerceivePlugin

__all__ = ["PerceiveComponent"]

logger = get_logger(__name__)


class PerceiveComponent(AgentComponent[PerceivePlugin]):
    """Proxy that orchestrates perception plugin."""

    COMPONENT_NAME = "perceive"

    def __init__(self) -> None:
        """Initialize local storage for perception data and spatial references."""
        super().__init__()
        self._perception: PerceptionData = {}

    @property
    def perception(self) -> PerceptionData:
        """Return the most recent perception data gathered by the plugin."""
        return self._perception

    @perception.setter
    def perception(self, new_perception: PerceptionData) -> None:
        """
        Store the latest perception data.

        Args:
            new_perception (PerceptionData): Data captured by the perception plugin.
        """
        self._perception = new_perception

    async def add_message(self, message: Message) -> None:
        """
        Forward a message to the perception plugin if supported.

        Args:
            message (Message): Arbitrary perception payload.
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
            logger.warning("No plugin found in PerceptionComponent.")
            return

        await self._plugin.execute(current_tick)
        self._perception = self._plugin.perception
