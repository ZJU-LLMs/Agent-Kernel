"""Facade around environment components providing a unified interface."""

import asyncio
from typing import Any, Dict, List, Literal, Optional, overload

from ...toolkit.logger import get_logger
from ...types.configs import EnvironmentComponentConfig
from .base.component_base import EnvironmentComponent
from .components import RelationComponent, SpaceComponent

logger = get_logger(__name__)

__all__ = ["Environment"]


class Environment:
    """Proxy responsible for delegating calls to environment components."""

    def __init__(self) -> None:
        """Initialize the environment proxy.

        Returns:
            None
        """
        self.components: Dict[str, EnvironmentComponent] = {}

    async def init(
        self,
        comp_configs: Dict[str, EnvironmentComponentConfig],
        resource_maps: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Initialize every environment component with its configuration.

        Args:
            comp_configs (Dict[str, EnvironmentComponentConfig]): Mapping of component names to configurations.
            resource_maps (Dict[str, Dict[str, Any]]): Registry of dependencies required by components.

        Returns:
            None
        """
        init_tasks = []
        for name, comp_config in comp_configs.items():
            component = self.components.get(name)
            if component is None:
                raise ValueError(f"Environment component '{name}' not registered.")
            init_tasks.append(component.init(comp_config=comp_config, resource_maps=resource_maps))
        if init_tasks:
            await asyncio.gather(*init_tasks)

    async def post_init(self) -> None:
        """
        Run post-initialization hooks on each component.

        Returns:
            None
        """
        if self.components:
            await asyncio.gather(*(component.post_init() for component in self.components.values()))
        logger.info("Environment Proxy: All components initialized.")

    def add_component(self, name: str, component: EnvironmentComponent) -> None:
        """
        Register an environment component.

        Args:
            name (str): Component identifier.
            component (EnvironmentComponent): Component instance.

        Returns:
            None
        """
        self.components[name] = component

    async def save_to_db(self) -> None:
        """
        Save the state of all environment components to the database.

        Returns:
            None
        """
        logger.info(f"Environment Proxy: Saving state for {len(self.components)} components...")
        save_tasks = [component.forward("save_to_db") for component in self.components.values()]
        if save_tasks:
            try:
                await asyncio.gather(*save_tasks)
                logger.info("Environment Proxy: All component states saved successfully.")
            except Exception as e:
                logger.error(f"Environment Proxy: Error during concurrent component save: {e}", exc_info=True)
        else:
            logger.info("Environment Proxy: No components to save.")

    async def load_from_db(self) -> None:
        """
        Load the state of all environment components from the database.

        Returns:
            None
        """
        logger.info(f"Environment Proxy: Loading state for {len(self.components)} components...")
        load_tasks = [component.forward("load_from_db") for component in self.components.values()]
        if load_tasks:
            try:
                await asyncio.gather(*load_tasks)
                logger.info("Environment Proxy: All component states loaded successfully.")
            except Exception as e:
                logger.error(f"Environment Proxy: Error during concurrent component load: {e}", exc_info=True)
        else:
            logger.info("Environment Proxy: No components to load.")

    async def run(self, component_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a method on the requested environment component.

        Args:
            component_name (str): Name of the component to target.
            method_name (str): Method name to invoke.
            *args (Any): Positional arguments forwarded to the component.
            **kwargs (Any): Keyword arguments forwarded to the component.

        Returns:
            Any: Result produced by the component.

        Raises:
            ValueError: If the component is not registered.
        """
        component = self.components.get(component_name)
        if component is None:
            raise ValueError(f"Environment component '{component_name}' not found.")
        return await component.forward(method_name, *args, **kwargs)

    @overload
    def get_component(self, name: Literal["relation"]) -> Optional[RelationComponent]: ...

    @overload
    def get_component(self, name: Literal["space"]) -> Optional[SpaceComponent]: ...

    def get_component(self, name: str) -> Optional[EnvironmentComponent]:
        """
        Retrieve a component by name.

        Args:
            name (str): Component identifier.

        Returns:
            Optional[EnvironmentComponent]: Component when found.
        """
        return self.components.get(name)

    def remove_component(self, name: str) -> None:
        """
        Remove a previously registered component.

        Args:
            name (str): Component identifier.

        Returns:
            None
        """
        if name in self.components:
            del self.components[name]

    def list_components(self) -> List[str]:
        """
        Return the names of all registered components.

        Returns:
            List[str]: Component identifiers.
        """
        return list(self.components.keys())
