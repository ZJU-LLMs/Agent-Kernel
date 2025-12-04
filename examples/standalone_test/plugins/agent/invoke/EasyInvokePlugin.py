from typing import List
from agentkernel_standalone.mas.agent.base.plugin_base import InvokePlugin
from agentkernel_standalone.toolkit.logger import get_logger
from agentkernel_standalone.types.schemas.action import ActionResult, CallStatus
from agentkernel_standalone.types.schemas.agent import CurrentAction, ActionRecord, ActionOutcome

logger = get_logger(__name__)

class EasyInvokePlugin(InvokePlugin):
    """
    Do what EasyPlanPlugin ask to do.
    """
    def __init__(self):
        super().__init__()
        self.agent_id = None
        self.plan_comp = None
        self.plans = []
        self.controller = None
    async def init(self): 
        self.agent_id = self._component.agent.agent_id
        self.plan_comp = self._component.agent.get_component('plan')
        self.plan_plug = self.plan_comp._plugin
        self.controller = self._component.agent.controller
    async def execute(self, current_tick: int):
        
        self.plans = self.plan_plug.plan
        for plan in self.plans:
            if plan['action'] == 'move':
                await self.move_to_pos(tuple(plan['target']))
            elif plan['action'] == 'chat':
                await self.chat_with_agent(plan['target'], plan['content'])
                
    async def move_to_pos(self, target: tuple[int, int]):
        await self.controller.run_environment('space', 'update_agent_position', 
                                        agent_id = self.agent_id, 
                                        new_position = target
                                        )
        logger.info(f'Agent {self._component.agent.agent_id} move to {target}')

    async def chat_with_agent(self, target_id: str, content: str):
        await self.controller.run_action('communication', 'send_message', from_id =self.agent_id, to_id = target_id, content = content)
        logger.info(f'Agent {self._component.agent.agent_id} say to {target_id} : {content}')