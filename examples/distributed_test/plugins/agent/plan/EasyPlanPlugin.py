import json
import textwrap
import asyncio
from typing import List, Dict, Any
import json_repair
from agentkernel_distributed.mas.agent.base.plugin_base import PlanPlugin
from agentkernel_distributed.mas.agent.components import *
from agentkernel_distributed.toolkit.logger import get_logger

from agentkernel_distributed.types.schemas.action import CallStatus

logger = get_logger(__name__)

class EasyPlanPlugin(PlanPlugin):
    """
    A simple plan plugin that generate a plan for the next tick.
    1. Choose whether move to another position or stay in the current position.
    2. Choose whether to chat with another agent or not.
    """
    
    def __init__(self):
        super().__init__()
        self.plan = []
        logger.info("EasyPlanPlugin initialized")
        
    async def init(self):
        self.agent_id = self._component.agent.agent_id
        self.model = self._component.agent.model
        self.perceive_comp: PerceiveComponent = self._component.agent.get_component("perceive")
        self.perceive_plug = self.perceive_comp._plugin
    async def execute(self, current_tick: int) -> Dict[str, Any]:
        self.plan.clear()
        could_see_agents = self.perceive_plug.surrounding_agents
        current_position = self.perceive_plug.current_position
        chat_history = self.perceive_plug.last_tick_messages
        
        prompt = f'''
                你是一个目标规划者,帮我规划下一步该做什么,目前,你在一张300*300的二维地图上,你可以选择移动到地图的任何一个位置,或者和身边的某一个人说话.
                你身边可以看到的agents有:{json.dumps(could_see_agents)}
                你当前的位置:{json.dumps(current_position)}
                之前和你聊天的人的历史信息:{json.dumps(chat_history)}
                回答示例：
                    {{ "action":"move", "target":[50,60]}}
                    或者
                    {{"action":"chat", "target": "agent_id", "content": "你好"}}
                务必保证回答为json格式。
                请选择你的下一步行为：
                '''
        
        model_response = await self.model.chat(prompt)
        print(model_response)
        logger.info(f"Agent {self.agent_id} has planned its next step: {model_response}.")
        self.plan.append(json_repair.loads(model_response))