import json
import textwrap
import asyncio
from typing import List, Dict, Any
import json_repair
from agentkernel_standalone.mas.agent.base.plugin_base import PlanPlugin
from agentkernel_standalone.mas.agent.components import *
from agentkernel_standalone.toolkit.logger import get_logger


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
                You are a goal planner, help me plan what to do next. Currently, you are on a 300x300 2D map. You can choose to move to any position on the map, or talk to someone nearby.
                Agents you can see around you: {json.dumps(could_see_agents)}
                Your current position: {json.dumps(current_position)}
                Chat history from previous conversations: {json.dumps(chat_history)}
                Response examples:
                    {{ "action":"move", "target":[50,60]}}
                    or
                    {{"action":"chat", "target": "agent_id", "content": "Hello"}}
                Please ensure the response is in JSON format.
                Please choose your next action:
                '''
        
        model_response = await self.model.chat(prompt)
        print(model_response)
        logger.info(f"Agent {self.agent_id} has planned its next step: {model_response}.")
        self.plan.append(json_repair.loads(model_response))