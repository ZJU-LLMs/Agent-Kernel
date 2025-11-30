"""Action proxy responsible for delegating calls to component plugins."""

import asyncio
from typing import Any, Dict, List, Optional, Union

from ...toolkit.logger import get_logger
from ...toolkit.models.router import ModelRouter
from ...types.configs import ActionComponentConfig
from ...types.schemas.action import ActionResult
from .base import ActionComponent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..controller import BaseController

logger = get_logger(__name__)


class Action:
    """A proxy for routing action calls to underlying components."""

    def __init__(self) -> None:
        """Initialize the component registry."""
        self.components: Dict[str, ActionComponent] = {}

    async def init(
        self,
        comp_configs: Dict[str, ActionComponentConfig],
        resource_maps: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Initialize every managed component from configuration.

        Args:
            comp_configs (Dict[str, ActionComponentConfig]): Mapping of component names to their configurations.
            resource_maps (Dict[str, Dict[str, Any]]): Resource mapping that resolves plugin and adapter classes.
        """
        logger.info("Action Proxy: Initializing all managed components concurrently...")
        init_tasks = []
        for name, comp_config in comp_configs.items():
            init_tasks.append(
                self.components[name].init(
                    comp_config=comp_config,
                    resource_maps=resource_maps,
                )
            )
        try:
            await asyncio.gather(*init_tasks)
            logger.info("Action Proxy: All components initialized concurrently.")
        except Exception as e:
            logger.error(f"Action Proxy: Error during concurrent component initialization: {e}")

    async def post_init(self, controller: "BaseController", model_router: ModelRouter) -> None:
        """
        Distribute shared dependencies to every component after initialization.

        Args:
            controller ("BaseController"): Controller coordinating component interactions.
            model_router (ModelRouter): Model router used by components.
        """
        logger.info("Action Proxy: Post initializing all managed components...")

        dependencies = {"controller": controller, "model_router": model_router}

        init_tasks = []
        for component in self.components.values():
            init_tasks.append(component.post_init(**dependencies))

        await asyncio.gather(*init_tasks)
        logger.info("Action Proxy: All components initialized.")

    def add_component(self, name: str, component: ActionComponent) -> None:
        """
        Register a component with the action proxy.

        Args:
            name (str): Name assigned to the component.
            component (ActionComponent): Component instance that provides action methods.
        """
        self.components[name] = component

    def remove_component(self, name: str) -> None:
        """
        Remove a component from the registry.

        Args:
            name (str): Name of the component to remove.
        """
        if name in self.components:
            del self.components[name]

    def get_component(self, name: Optional[str] = None) -> Optional[Union[ActionComponent, Dict[str, ActionComponent]]]:
        """
        Retrieve a component or the full component mapping.

        Args:
            name (Optional[str]): Component name to retrieve. When omitted, return the entire registry.

        Returns:
            Optional[Union[ActionComponent, Dict[str, ActionComponent]]]: Matching component or the full mapping.
        """
        if name is None:
            return self.components
        return self.components.get(name)

    def list_components(self) -> List[str]:
        """
        List the names of all registered components.

        Returns:
            List[str]: Component identifiers.
        """
        return list(self.components.keys())

    def list_comp_methods_names(
        self, component_name: str, annotation_type: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        Retrieve method names exposed by a specific component.

        Args:
            component_name (str): Name of the component to inspect.
            annotation_type (Optional[str]): The type of annotation to filter methods by.

        Returns:
            Optional[List[str]]: Method names provided by the component.
        """

        if component_name not in self.components:
            return None

        component = self.components[component_name]

        return component.list_methods_names(annotation_type=annotation_type)

    async def get_agent_call_methods(
        self, component_name: str, method_name: Optional[Union[str, List[str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve callable method metadata for agents.

        Args:
            component_name (str): Component from which to fetch methods.
            method_name (Optional[Union[str, List[str]]]): Optional single method or list of methods to filter results.

        Returns:
            List[Dict[str, Any]]: Method metadata dictionaries.
        """
        if component_name not in self.components:
            return []

        component = self.components[component_name]

        return await component.get_method(method_name=method_name, annotation_type="AgentCall")

    async def save_to_db(self) -> None:
        """Save the persistent state of all managed components to the database."""
        logger.info("Action Proxy: Saving state for all managed components...")
        save_tasks = [component.forward("save_to_db") for component in self.components.values()]

        if not save_tasks:
            logger.info("Action Proxy: No components to save.")
            return

        all_success = True
        try:
            results = await asyncio.gather(*save_tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Action Proxy: An exception occurred during save: {res}")
                    all_success = False
                elif isinstance(res, ActionResult) and res.is_error():
                    logger.warning(f"Action Proxy: A component failed to save state: {res.message}")
                    all_success = False

            if all_success:
                logger.info("Action Proxy: All components' state saved successfully.")
            else:
                logger.warning("Action Proxy: Some components failed to save state.")

        except Exception as e:
            logger.error(f"Action Proxy: A critical error occurred during saving: {e}")

    async def load_from_db(self) -> None:
        """Load the persistent state of all managed components from the database."""
        logger.info("Action Proxy: Loading state for all managed components...")
        load_tasks = [component.forward("load_from_db") for component in self.components.values()]

        if not load_tasks:
            logger.info("Action Proxy: No components to load state from.")
            return

        all_success = True
        try:
            results = await asyncio.gather(*load_tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Action Proxy: An exception occurred during load: {res}")
                    all_success = False
                elif isinstance(res, ActionResult) and res.is_error():
                    logger.warning(f"Action Proxy: A component failed to load state: {res.message}")
                    all_success = False

            if all_success:
                logger.info("Action Proxy: All components' state loaded successfully.")
            else:
                logger.warning("Action Proxy: Some components failed to load state.")

        except Exception as e:
            logger.error(f"Action Proxy: A critical error occurred during loading: {e}")

    async def run(self, component_name: str, method_name: str, **kwargs: Any) -> ActionResult:
        """
        Execute a method on a component and return a standardized result.

        Args:
            component_name (str): Component exposing the target method.
            method_name (str): Method name to execute.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            ActionResult: Execution outcome or error information.
        """
        if component_name not in self.components:
            return ActionResult.error(
                method_name=method_name, message=f"Action component '{component_name}' not found."
            )

        component = self.components[component_name]

        try:
            result = await component.forward(method_name, arguments=kwargs)

            if not isinstance(result, ActionResult):
                logger.warning("Component did not return an ActionResult. Wrapping it.")
                return ActionResult.success(
                    method_name=method_name, message="Action completed successfully", data=result
                )

            return result
        except Exception as e:
            logger.error(f"Failed to run action '{method_name}' on component '{component_name}': {e}")
            return ActionResult.error(method_name=method_name, message=str(e))
