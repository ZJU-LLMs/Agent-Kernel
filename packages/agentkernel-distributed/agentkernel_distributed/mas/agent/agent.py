"""Agent container responsible for coordinating agent components."""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, overload

from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter
from ...types.configs.agent import AgentComponentConfig
from .base.component_base import AgentComponent
from .components import (
    InvokeComponent,
    PerceiveComponent,
    PlanComponent,
    ProfileComponent,
    ReflectComponent,
    StateComponent,
)

if TYPE_CHECKING:
    from ..controller import BaseController

logger = get_logger(__name__)

__all__ = ["Agent"]


class Agent:
    """Encapsulate a collection of components that implement agent behaviour."""

    def __init__(self, agent_id: str, component_order: Optional[List[str]] = None) -> None:
        """
        Create a new agent with optional component execution order.

        Args:
            agent_id (str): Identifier assigned to this agent.
            component_order (Optional[List[str]], optional): Optional explicit ordering of component execution.
                Defaults to ["perceive", "plan", "invoke", "state", "reflect"].
        """
        self._agent_id = agent_id
        self._controller: Optional["BaseController"] = None
        self._model: Optional[ModelRouter] = None
        self._global_tick = 0
        self._components: Dict[str, AgentComponent] = {}
        self._component_order = component_order or ["perceive", "plan", "invoke", "state", "reflect"]

    @property
    def model(self) -> Optional[ModelRouter]:
        """Return the injected model router."""
        return self._model

    @property
    def global_tick(self) -> int:
        """Return the last recorded global tick."""
        return self._global_tick

    @property
    def agent_id(self) -> str:
        """Return the identifier of this agent."""
        return self._agent_id

    @property
    def controller(self) -> Optional["BaseController"]:
        """Return the controller coordinating this agent."""
        return self._controller

    def set_global_tick(self, tick: int) -> None:
        """
        Record the current global tick for the agent.

        Args:
            tick (int): Simulation tick to record.
        """
        self._global_tick = tick

    async def init(
        self,
        configs: Dict[str, AgentComponentConfig],
        resource_maps: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Instantiate and initialize all configured components.

        Args:
            configs (Dict[str, AgentComponentConfig]): Mapping of component names to their configuration.
            resource_maps (Dict[str, Dict[str, Any]]): Registry of available component implementations.

        Returns:
            None
        """
        init_tasks = []
        for name, config in configs.items():
            component_class = resource_maps["agent_components"].get(name)
            if component_class is None:
                logger.warning(f"Component '{name}' not found in component maps for agent '{self._agent_id}'.")
                continue

            component_instance = component_class()
            self.add_component(component_instance)
            init_tasks.append(self._components[name].init(self, config, resource_maps))

        if init_tasks:
            await asyncio.gather(*init_tasks)
        logger.info("Successfully initialized Agent components concurrently.")

    async def post_init(self, model_router: ModelRouter, controller: "BaseController") -> None:
        """
        Provide shared dependencies to all components.

        Args:
            model_router (ModelRouter): Shared model router instance.
            controller ("BaseController"): Controller orchestrating this agent and other modules.

        Returns:
            None
        """
        self._model = model_router
        self._controller = controller
        await asyncio.gather(*(component.post_init() for component in self._components.values()))
        logger.info("Agent '%s' successfully completed post-initialization for all components.", self._agent_id)

    def add_component(self, component: AgentComponent) -> None:
        """
        Register a component with the agent.

        Args:
            component (AgentComponent): Component instance to add.
        """
        name = component.COMPONENT_NAME
        self._components[name] = component

    def remove_component(self, name: str) -> None:
        """
        Remove a component from the agent.

        Args:
            name (str): Identifier of the component to remove.
        """
        if name in self._components:
            del self._components[name]

    @overload
    def get_component(self, name: Literal["profile"]) -> Optional[ProfileComponent]: ...

    @overload
    def get_component(self, name: Literal["perceive"]) -> Optional[PerceiveComponent]: ...

    @overload
    def get_component(self, name: Literal["plan"]) -> Optional[PlanComponent]: ...

    @overload
    def get_component(self, name: Literal["invoke"]) -> Optional[InvokeComponent]: ...

    @overload
    def get_component(self, name: Literal["reflect"]) -> Optional[ReflectComponent]: ...

    @overload
    def get_component(self, name: Literal["state"]) -> Optional[StateComponent]: ...

    def get_component(self, name: str) -> Optional[AgentComponent]:
        """
        Retrieve a component by name.

        Args:
            name (str): Component identifier.

        Returns:
            Optional[AgentComponent]: Component instance when found.
        """
        return self._components.get(name)

    def list_components(self) -> List[str]:
        """
        List the identifiers of all registered components.

        Returns:
            List[str]: Component identifiers.
        """
        return list(self._components.keys())

    async def save_to_db(self) -> None:
        """
        Save the state of all components managed by this agent.
        """
        logger.debug(f"Saving state for agent '{self._agent_id}'...")
        save_tasks = [component.save_to_db() for component in self._components.values()]
        if save_tasks:
            await asyncio.gather(*save_tasks)
        logger.info(f"Successfully saved state for agent '{self._agent_id}'.")

    async def load_from_db(self) -> None:
        """
        Load the state of all components managed by this agent.
        """
        logger.debug(f"Loading state for agent '{self._agent_id}'...")
        load_tasks = [component.load_from_db() for component in self._components.values()]
        if load_tasks:
            await asyncio.gather(*load_tasks)
        logger.info(f"Successfully loaded state for agent '{self._agent_id}'.")

    async def run(self, current_tick: int) -> None:
        """
        Execute the component pipeline for a single simulation tick.

        Args:
            current_tick (int): Current simulation tick.

        Returns:
            None
        """
        logger.debug("Agent '%s' run method called. Component order: %s", self._agent_id, self._component_order)
        for component_name in self._component_order:
            component = self.get_component(component_name)
            if component is None:
                logger.warning("Component '%s' not found in agent '%s'.", component_name, self._agent_id)
                continue
            await component.execute(current_tick)
