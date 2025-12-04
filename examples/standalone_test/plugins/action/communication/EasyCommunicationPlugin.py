import textwrap
import json
import inspect
from typing import List, Dict, Any, Optional
from agentkernel_standalone.mas.action.base.plugin_base import CommunicationPlugin
from agentkernel_standalone.types.schemas.message import Message, MessageKind
from agentkernel_standalone.toolkit.logger import get_logger
from agentkernel_standalone.toolkit.utils.annotation import ServiceCall
from agentkernel_standalone.toolkit.utils.annotation import AgentCall

# Import the standardized ActionResult and ActionStatus
from agentkernel_standalone.types.schemas.action import ActionResult

logger = get_logger(__name__)


class EasyCommunicationPlugin(CommunicationPlugin):
    """
    EasyCommunicationPlugin chieve the communication function bwtween two agents.
    """

    def __init__(self):
        super().__init__()

    async def init(self, controller, model_router):
        self.controller = controller

    @AgentCall
    async def send_message(self, from_id: str, to_id: str, content: str):
        logger.info(f"{from_id} send message to {to_id}")
        message = Message(
            from_id=from_id,
            to_id=to_id,
            kind=MessageKind.FROM_AGENT_TO_AGENT,
            content=content,
            created_at=await self.controller.run_system("timer", "get_tick"),
            extra={},
        )

        try:
            await self.controller.run_system("messager", "send_message", message=message)
            logger.info(f"{from_id} send message to {to_id}")
        except Exception as e:
            logger.error(f"{from_id} Error sending message: {e}")
