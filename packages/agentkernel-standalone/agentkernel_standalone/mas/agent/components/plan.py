"""Agent component that coordinates planning plugins."""

from typing import Any, Dict, Optional

from ....toolkit.logger import get_logger
from ..base.component_base import AgentComponent
from ..base.plugin_base import PlanPlugin

__all__ = ["PlanComponent"]

logger = get_logger(__name__)


class PlanComponent(AgentComponent[PlanPlugin]):
    """A component that manages the agent's planning process."""

    COMPONENT_NAME = "plan"

    def __init__(self) -> None:
        """Initialize the plan component."""
        super().__init__()
        self._current_plan: Optional[Dict[str, Any]] = None
        self._current_step_index: int = 0
        self._current_tool_call: Optional[Dict[str, Any]] = None

    @property
    def current_plan(self) -> Optional[Dict[str, Any]]:
        """Return the plan currently produced by the planner plugin."""
        return self._current_plan

    @current_plan.setter
    def current_plan(self, current_plan: Optional[Dict[str, Any]]) -> None:
        """
        Replace the tracked plan.

        Args:
            current_plan (Optional[Dict[str, Any]]): Plan description provided by the plugin.
        """
        self._current_plan = current_plan

    @property
    def current_step_index(self) -> int:
        """Return the current position within the active plan."""
        return self._current_step_index

    @current_step_index.setter
    def current_step_index(self, current_step_index: int) -> None:
        """
        Record progress within the plan.

        Args:
            current_step_index (int): Step index reported by the plugin.
        """
        self._current_step_index = current_step_index

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

        self._current_plan = self._plugin.current_plan
        self._current_step_index = self._plugin.current_step_index
