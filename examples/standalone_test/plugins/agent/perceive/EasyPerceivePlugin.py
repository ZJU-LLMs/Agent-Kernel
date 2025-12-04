from typing import Dict, Any, Optional, List, Tuple

import heapq
import itertools
import math

from agentkernel_standalone.types.schemas.message import Message
from agentkernel_standalone.mas.agent.base.plugin_base import PerceivePlugin
from agentkernel_standalone.mas.environment.components import *
from agentkernel_standalone.toolkit.logger import get_logger

logger = get_logger(__name__)


class EasyPerceivePlugin(PerceivePlugin):
    def __init__(self):
        """
        The Easy Perceive plugin for the agent.
        Function include:
        1. Get surrounding information, like agents, objects, etc.
        2. Receive messages from system.
        """
        super().__init__()
        self.global_tick = 0
        self.received_messages = []
        self.last_tick_messages = []
        self.surrounding_agents = []
        logger.info(f"EasyPerceivePlugin initialized.")

    async def init(self):
        self.controller = self._component.agent.controller
        self.agent_id = self._component.agent.agent_id
        self.plan_comp = self._component.agent.get_component("plan")

    async def execute(self, current_tick: int):

        agent_info = await self.controller.run_environment("space", "get_agent", self.agent_id)
        self.current_position = agent_info["position"]
        self.last_tick_messages = self.received_messages
        self.received_messages = []
        logger.info(
            f"Agent {self.agent_id} is at position {self.current_position}, at last tick, there are {len(self.last_tick_messages)} messages."
        )
        # Get current postion.

        could_see_distance = 10
        self.surrounding_agents = []
        self.all_agents = []

        self.all_agents = await self.controller.run_environment("space", "get_all_agents")
        for agent in self.all_agents:
            if agent["id"] != self.agent_id:
                if (
                    math.sqrt(
                        (agent["position"][0] - self.current_position[0]) ** 2 + (agent["position"][1] - self.current_position[1]) ** 2
                    )
                    <= could_see_distance
                ):
                    self.surrounding_agents.append(agent)

        logger.info(f"Agent {self.agent_id} looked around, and found {len(self.surrounding_agents)} agents.")

    async def add_message(self, message: Message):
        """
        Called by the system's dispatch function, add the message to the received_messages list.
        """

        logger.info(f"Agent {self.agent_id} received message from {message.from_id}: {message.content}")
        copyed_message = {"from_id": message.from_id, "kind": message.kind, "content": message.content}
        self.received_messages.append(copyed_message)
        logger.info(f"Agent {self.agent_id} stored message: {copyed_message}")
