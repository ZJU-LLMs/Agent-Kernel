"""Container that coordinates system-level components such as timers and recorders."""

import asyncio
import inspect
from typing import Any, Dict, Optional

from typing import TYPE_CHECKING
from ...toolkit.logger import get_logger
if TYPE_CHECKING:
    from ..controller import BaseController


from .components import SystemComponent

logger = get_logger(__name__)


class System:
    """Store and manage system components, delegating calls on demand."""

    def __init__(self) -> None:
        """Initialize the component registry."""
        self._components: Dict[str, SystemComponent] = {}

    def add_component(self, name: str, component: SystemComponent) -> None:
        """
        Register a component with the system container.

        Args:
            name (str): Unique identifier for the component.
            component (SystemComponent): System component instance.
        """
        if name in self._components:
            logger.warning("Component '%s' is being overwritten.", name)

        self._components[name] = component
        setattr(self, name, component)
        logger.info("Component '%s' has been added to the system.", name)

    async def post_init(self, controller: "BaseController") -> None:
        """
        Run post-initialization hooks on every registered component.

        Args:
            controller ("BaseController"): Controller used to deliver inter-agent messages.
        """
        logger.info("Running post_init for all applicable system components...")
        post_init_tasks = []
        for name, component in self._components.items():
            if not hasattr(component, "post_init"):
                continue

            if name == "messager":
                post_init_tasks.append(component.post_init(controller=controller))
            else:
                post_init_tasks.append(component.post_init())

        if post_init_tasks:
            try:
                await asyncio.gather(*post_init_tasks)
                logger.info("All applicable system components have been post-initialized.")
            except Exception as exc:
                logger.error("An error occurred while running post_init hooks: %s", exc)

    async def run(self, component_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a method on a registered system component.

        Args:
            component_name (str): Name of the component to target.
            method_name (str): Method exposed by the component.
            *args (Any): Positional arguments forwarded to the component.
            **kwargs (Any): Keyword arguments forwarded to the component.

        Returns:
            Any: Result produced by the component.

        Raises:
            ValueError: If the component or method cannot be found.
        """
        component = getattr(self, component_name, None)
        if component is None:
            raise ValueError(f"System component '{component_name}' not found.")

        method = getattr(component, method_name, None)
        if method is None or not callable(method):
            raise ValueError(f"Method '{method_name}' not found in component '{component_name}'.")

        if asyncio.iscoroutinefunction(method):
            return await method(*args, **kwargs)
        else:
            return method(*args, **kwargs)

    async def close(self) -> bool:
        """
        Close every component that exposes a `close` method.

        Returns:
            bool: True when all components close successfully.
        """
        logger.info("Closing all applicable system components...")
        try:
            for name, component in self._components.items():
                close_method: Optional[Any] = getattr(component, "close", None)
                if close_method is None:
                    continue
                await close_method()
                logger.info("Component '%s' has been closed.", name)
        except Exception as exc:
            logger.error("Exception %s occurred while closing the system.", exc)
            return False
        return True
