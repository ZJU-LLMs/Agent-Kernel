"""Runtime manager responsible for orchestrating agents within a pod."""

import asyncio
import copy
import inspect
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter
from ...types.configs import AgentConfig, AgentTemplateConfig
from ...types.schemas.message import Message
from .agent import Agent

if TYPE_CHECKING:
    from ..controller import BaseController

logger = get_logger(__name__)

__all__ = ["AgentManager"]


class AgentManager:
    """Manage the lifecycle and execution of agents hosted within a single pod."""

    def __init__(
        self,
        pod_id: str,
        agent_templates: Optional[AgentTemplateConfig],
        agent_configs: List[AgentConfig],
        resource_maps: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Initialize the manager with configuration and resource maps.

        Args:
            pod_id (str): Identifier of the owning pod.
            agent_templates (Optional[AgentTemplateConfig]): Template definitions used when spawning agents.
            agent_configs (List[AgentConfig]): Configuration objects for initial agents.
            resource_maps (Dict[str, Dict[str, Any]]): Shared registry of component implementations.
        """
        self._pod_id = pod_id
        self._agent_configs = agent_configs
        self._resource_maps = resource_maps
        self._agent_templates = agent_templates

        self._agents: Dict[str, Agent] = {}
        self._model_router: Optional[ModelRouter] = None
        self._controller: Optional["BaseController"] = None

    async def init(self) -> None:
        """
        Instantiate and initialize all configured agents.

        Returns:
            None
        """
        logger.info(f"[{self._pod_id}] AgentManager: Initializing {len(self._agent_configs)} agents...")
        init_tasks = []
        for agent_config in self._agent_configs:
            agent_id = agent_config.id
            agent_instance = Agent(agent_id=agent_id, component_order=agent_config.component_order)
            init_tasks.append(agent_instance.init(agent_config.components, self._resource_maps))
            self._agents[agent_id] = agent_instance
        await asyncio.gather(*init_tasks)
        logger.info(f"[{self._pod_id}] AgentManager: All agents initialized.")

    async def post_init(self, model_router: ModelRouter, controller: "BaseController") -> None:
        """
        Inject shared dependencies into every agent.

        Args:
            model_router (ModelRouter): Shared model router instance.
            controller ("BaseController"): Controller orchestrating agents and other modules.

        Returns:
            None
        """
        self._model_router = model_router
        self._controller = controller
        await asyncio.gather(*(agent.post_init(model_router, controller) for agent in self._agents.values()))
        logger.info(f"[{self._pod_id}] AgentManager: All agents post-initialized with dependencies.")

    def get_agent_count(self) -> int:
        """
        Retrieve the number of managed agents.

        Returns:
            int: Count of managed agents.
        """
        return len(self._agents)

    def get_agent_ids(self) -> List[str]:
        """
        Retrieve the identifiers of all managed agents.

        Returns:
            List[str]: Agent identifiers.
        """
        return list(self._agents.keys())

    async def deliver_message(self, to_id: str, message: Message) -> None:
        """
        Deliver a message to an agent hosted by this manager.

        Args:
            to_id (str): Recipient agent identifier.
            message (Message): Message instance to deliver.

        Returns:
            None
        """
        agent = self._agents.get(to_id)
        if agent is None:
            logger.error(f"[{self._pod_id}] Could not find agent '{to_id}' to deliver message.")
            return

        perception_component = agent.get_component("perceive")
        if perception_component is None:
            logger.warning(f"[{self._pod_id}] Agent '{to_id}' has no perception component.")
            return

        await perception_component.add_message(message)
        logger.debug(f"[{self._pod_id}] Delivered message to local agent '{to_id}'.")

    async def run_tick(self, tick: int) -> None:
        """
        Execute a full simulation tick for all agents.

        Args:
            tick (int): Current simulation tick.

        Returns:
            None
        """
        tasks = [agent.run(tick) for agent in self._agents.values()]
        if tasks:
            await asyncio.gather(*tasks)

    async def run_agent_method(
        self, agent_id: str, component_name: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a method on a component belonging to a specific agent.

        Args:
            agent_id (str): Identifier of the target agent.
            component_name (str): Component exposing the method.
            method_name (str): Name of the method or attribute to access.
            *args: Positional arguments forwarded to the method.
            **kwargs: Keyword arguments forwarded to the method.

        Returns:
            Any: Result produced by the component.

        Raises:
            ValueError: If the agent or component cannot be found.
            AttributeError: If the component lacks the requested attribute.
            TypeError: If arguments are provided for a non-callable attribute.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"[{self._pod_id}] Agent ID '{agent_id}' not found in this pod.")

        component = agent.get_component(component_name)
        if component is None:
            raise ValueError(f"[{self._pod_id}] Component '{component_name}' not found in agent '{agent_id}'.")

        if not hasattr(component, method_name):
            raise AttributeError(
                f"[{self._pod_id}] Method or attribute '{method_name}' not found in component '{component_name}'."
            )

        member = getattr(component, method_name)
        if callable(member):
            if inspect.iscoroutinefunction(member):
                return await member(*args, **kwargs)
            return member(*args, **kwargs)

        if args or kwargs:
            raise TypeError(f"Attribute '{method_name}' is not callable and cannot accept arguments.")
        return member

    def _generate_single_agent_config(
        self, agent_id: str, template_name: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Produce configuration data for a new agent based on a template.

        Args:
            agent_id (str): Identifier to assign to the new agent.
            template_name (str): Name of the template to apply.
            data (Dict[str, Any]): Payload containing overrides for component parameters.

        Returns:
            Optional[Dict[str, Any]]: Configuration dictionary or None if template lookup fails.
        """
        if self._agent_templates is None:
            logger.error("Agent templates are not available for dynamic agent creation.")
            return None

        template = next((tmpl for tmpl in self._agent_templates.templates if tmpl.name == template_name), None)
        if template is None:
            logger.error(f"Template '{template_name}' not found.")
            return None

        agent_components = copy.deepcopy(template.components)
        component_order = template.component_order

        for comp_config in agent_components.values():
            plugin_entry = comp_config.plugin
            if not plugin_entry:
                continue

            _, plugin_obj = next(iter(plugin_entry.items()))
            plugin_config = plugin_obj.model_dump()

            for param, data_key in list(plugin_config.items()):
                if isinstance(data_key, str) and data_key in data:
                    plugin_config[param] = data[data_key]

            for key, value in plugin_config.items():
                if hasattr(plugin_obj, key):
                    setattr(plugin_obj, key, value)

        return {"id": agent_id, "components": agent_components, "component_order": component_order}

    async def save_to_db(self) -> None:
        """
        Save the state of all managed agents to the database.

        This concurrently calls `save_to_db` on every agent, which in
        turn calls `save_to_db` on all of its components.

        Returns:
            None
        """
        logger.info(f"[{self._pod_id}] Saving state for {len(self._agents)} agents...")
        save_tasks = [agent.save_to_db() for agent in self._agents.values()]
        if save_tasks:
            try:
                await asyncio.gather(*save_tasks)
                logger.info(f"[{self._pod_id}] All agent states saved successfully.")
            except Exception as e:
                logger.error(f"[{self._pod_id}] Error during concurrent agent save: {e}", exc_info=True)
        else:
            logger.info(f"[{self._pod_id}] No agents to save.")

    async def load_from_db(self) -> None:
        """
        Load the state of all managed agents from the database.

        This concurrently calls `load_from_db` on every agent, which in
        turn calls `load_from_db` on all of its components.

        Returns:
            None
        """
        logger.info(f"[{self._pod_id}] Loading state for {len(self._agents)} agents...")
        load_tasks = [agent.load_from_db() for agent in self._agents.values()]
        if load_tasks:
            try:
                await asyncio.gather(*load_tasks)
                logger.info(f"[{self._pod_id}] All agent states loaded successfully.")
            except Exception as e:
                logger.error(f"[{self._pod_id}] Error during concurrent agent load: {e}", exc_info=True)
        else:
            logger.info(f"[{self._pod_id}] No agents to load.")

    async def add_agent(self, agent_id: str, template_name: str, data: Dict[str, Any]) -> bool:
        """
        Create and register a new agent at runtime.

        Args:
            agent_id (str): Identifier for the new agent.
            template_name (str): Name of the template to instantiate.
            data (Dict[str, Any]): Initialization payload applied to the template.

        Returns:
            bool: True when the agent is created successfully.
        """
        agent_config = self._generate_single_agent_config(agent_id, template_name, data)
        if not agent_config:
            logger.error(f"[{self._pod_id}] Failed to generate config for new agent '{agent_id}'.")
            return False

        logger.info(f"[{self._pod_id}] Adding new agent '{agent_id}'...")
        try:
            agent_instance = Agent(
                agent_id=agent_id,
                component_order=agent_config.get("component_order"),
            )
            await agent_instance.init(agent_config.get("components", {}), self._resource_maps)

            if self._model_router and self._controller:
                await agent_instance.post_init(self._model_router, self._controller)

            self._agents[agent_id] = agent_instance
            logger.info(f"[{self._pod_id}] Successfully added agent '{agent_id}'. Total agents: {len(self._agents)}")
            return True
        except Exception as exc:
            logger.error(f"[{self._pod_id}] Failed to add agent '{agent_id}': {exc}", exc_info=True)
            return False

    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent and perform any available cleanup hooks.

        Args:
            agent_id (str): Identifier of the agent to remove.

        Returns:
            bool: True when the agent is removed successfully.
        """
        agent_instance = self._agents.get(agent_id)
        if agent_instance is None:
            logger.warning(f"[{self._pod_id}] Agent '{agent_id}' not found for deletion.")
            return False

        logger.info(f"[{self._pod_id}] Deleting agent '{agent_id}'...")

        try:
            close_callable = getattr(agent_instance, "close", None)
            if callable(close_callable):
                if inspect.iscoroutinefunction(close_callable):
                    await close_callable()
                else:
                    close_callable()
        except Exception as exc:
            logger.error(
                f"[{self._pod_id}] Error during cleanup for agent '{agent_id}': {exc}",
                exc_info=True,
            )

        del self._agents[agent_id]
        logger.info(f"[{self._pod_id}] Successfully deleted agent '{agent_id}'. Remaining agents: {len(self._agents)}")
        return True
