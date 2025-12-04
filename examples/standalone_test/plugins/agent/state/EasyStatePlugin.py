import json
from typing import Dict, Any, Optional
from agentkernel_standalone.toolkit.logger import get_logger
from agentkernel_standalone.mas.agent.base.plugin_base import StatePlugin

logger = get_logger(__name__)

class EasyStatePlugin(StatePlugin):
    def __init__(self, state_data: Optional[Dict[str, Any]] = None):
        super().__init__()
        # state_data is the specific state maintained by this plugin
        self._state_data: Dict[str, Any] = state_data if state_data is not None else {}
        self.agent_id = None
        
    async def init(self):
        self.agent_id = self._component.agent.agent_id
        
    async def execute(self, current_tick: int):
        logger.info(f'Agent {self.agent_id} have the same state as yesterday.')
    
    async def set_state(self, key: str, value: Any):
        pass