import textwrap
import json
import inspect
from typing import List, Dict, Any, Optional
from agentkernel_distributed.mas.action.base.plugin_base import CommunicationPlugin
from agentkernel_distributed.types.schemas.message import Message, MessageKind
from agentkernel_distributed.toolkit.logger import get_logger
from agentkernel_distributed.toolkit.utils.annotation import ServiceCall
from agentkernel_distributed.toolkit.utils.annotation import AgentCall
# Import the standardized ActionResult and ActionStatus
from agentkernel_distributed.types.schemas.action import ActionResult

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
            from_id = from_id,
            to_id = to_id,
            kind = MessageKind.FROM_AGENT_TO_AGENT,
            content = content,
            created_at = await self.controller.run_system('timer', 'get_tick'),
            extra = {}
        )
        
        try: 
            await self.controller.run_system('messager', 'send_message', message = message)
            logger.info(f"{from_id} send message to {to_id}")
        except Exception as e:
            logger.error(f"{from_id} Error sending message: {e}")
            
    async def _log_action(self, *args: Any, **kwargs: Any) -> None:
        """
        Record execution metadata for auditing.

        Args:
            *args: Positional data to log.
            **kwargs: Keyword data to log.
        """
        logger.info(f"{self.controller.agent_id} executed {inspect.stack()[1][3]} with args: {args} and kwargs: {kwargs}")

    @ServiceCall
    async def save_to_db(self) -> None:
        """
        Save the plugin's persistent state to the database.
        For EasyCommunicationPlugin, there's no persistent state to save.
        """
        logger.info(f"EasyCommunicationPlugin for agent {getattr(self.controller, 'agent_id', 'unknown')} has no state to save.")

    @ServiceCall
    async def load_from_db(self) -> None:
        """
        Load the plugin's persistent state from the database.
        For EasyCommunicationPlugin, there's no persistent state to load.
        """
        logger.info(f"EasyCommunicationPlugin for agent {getattr(self.controller, 'agent_id', 'unknown')} has no state to load.")