import math
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from agentkernel_standalone.mas.environment.base.plugin_base import RelationPlugin
from agentkernel_standalone.toolkit.logger import get_logger

logger = get_logger(__name__)

class EasyRelationPlugin(RelationPlugin):
    def __init__(self, relations: Optional[List[Dict[str, Any]]] = None):
        self.relations = relations if relations is not None else []
        
    async def init(self):
        pass
    
    async def save_to_db(self):
        pass
            
