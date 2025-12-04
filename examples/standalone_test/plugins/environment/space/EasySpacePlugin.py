import asyncio
import json
import math
from typing import Dict, Any, List, Optional, Tuple
from agentkernel_standalone.mas.environment.base.plugin_base import SpacePlugin
from agentkernel_standalone.toolkit.logger import get_logger

logger = get_logger(__name__)

class EasySpacePlugin(SpacePlugin):
    '''
    EasySpacePlugin is a plugin that stores, updates the entity's postion.
    '''
    def __init__(self, agents: Optional[Dict[str, Any]] = None):
        self.agents = agents or None
        
        logger.info(f"EasySpacePlugin initialized with {len(agents)} agents.")
        
    async def get_agent(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """MODIFIED: Gets agent info from memory."""
        return self.agents.get(entity_id)
    
    async def get_all_entities(self, entity_type: str) -> List[Dict[str, Any]]:
        """MODIFIED: Gets entities from memory. Keep async for consistency."""
        # Logic remains the same, reads from self.agents/self.objects
        if entity_type == "agent":
            return list(self.agents.values())
        elif entity_type is None:
            return list(self.agents.values()) + list(self.objects.values())
        else:
            raise ValueError(f"Invalid entity_type: {entity_type!r}. Expected 'agent', 'object', or None.")
        
    async def get_all_agents(self) -> List[Dict[str, Any]]:
        """Gets all agents from memory."""
        return await self.get_all_entities("agent")
    
    async def update_agent_position(self, agent_id: str, new_position: Tuple[int, int]) -> None:
        '''
        Update the position of an agent.

        Args:
            agent_id (str): The ID of the agent.
            new_position (Tuple[float, float]): The new position of the agent.

        Returns:
            None
        '''

        if self.agents is not None:
            if agent_id in self.agents:
                self.agents[agent_id]["position"] = new_position
                logger.info(f"Agent {agent_id} has moved to new_position {self.agents[agent_id]['position']}.")
            else:
                logger.warning(f"Agent {agent_id} not found in self.agents.")
                
    async def update_agents_status(self) -> None:
        logger.info('All the agents have been updated.')
