"""Example custom controller"""

from __future__ import annotations

from agentkernel_standalone.mas.controller.controller import ControllerImpl
from agentkernel_standalone.toolkit.logger import get_logger

logger = get_logger(__name__)


class CustomController(ControllerImpl):
    """Controller extension"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    async def update_agents_status(self) -> None:
        """Trigger each pod to refresh agent status within the environment.

        Returns:
            None
        """
        logger.info("Updating agent status...")

