from typing import Dict, Any, Optional, List
import json
import textwrap
from enum import Enum

from agentkernel_distributed.mas.agent.base.plugin_base import ReflectPlugin
from agentkernel_distributed.toolkit.logger import get_logger
from agentkernel_distributed.toolkit.utils import clean_json_response


logger = get_logger(__name__)

class EasyReflectPlugin(ReflectPlugin):
    def __init__(self):
        super().__init__()
        self.agent_id = None
        
    async def init(self):
        self.agent_id = self._component.agent.agent_id 
        
    async def execute(self, current_tick: int) -> Dict[str, Any]:
        logger.info(f'Agent {self.agent_id} reflect his whole day, and get nothing.')