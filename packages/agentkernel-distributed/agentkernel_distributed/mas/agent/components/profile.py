"""Profile component that manages profile metadata."""

from typing import Any, Dict
import copy

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import ProfilePlugin

__all__ = ["ProfileComponent"]

logger = get_logger(__name__)


class ProfileComponent(AgentComponent[ProfilePlugin]):
    """Proxy that coordinates profile plugin."""

    COMPONENT_NAME = "profile"

    def __init__(self) -> None:
        """Initialize local storage for profile fields."""
        super().__init__()
        self._profile_data: Dict[str, Any] = {}

    @property
    def profile_data(self) -> Dict[str, Any]:
        """Return the current profile data for the agent."""
        return self._profile_data

    @profile_data.setter
    def profile_data(self, profile_data: Dict[str, Any]) -> None:
        """
        Replace the stored profile data.

        Args:
            profile_data (Dict[str, Any]): New profile values keyed by field name.
        """
        self._profile_data = profile_data

    async def set_profile(self, key: str, value: Any) -> None:
        """
        Update a profile field via the underlying plugin.

        Args:
            key (str): Profile attribute to update.
            value (Any): Value assigned to the attribute.
        """
        self._profile_data[key] = value
        await self._plugin.set_profile(key, value)

    async def execute(self, current_tick: int) -> None:
        """
        Execute the profile plugin for the given simulation tick.

        Args:
            current_tick (int): Simulation tick used when invoking the plugin.
        """
        if not self._plugin:
            logger.warning("No plugin found in ProfileComponent.")
            return

        await self._plugin.execute(current_tick)

        self._profile_data = self._plugin.profile_data
