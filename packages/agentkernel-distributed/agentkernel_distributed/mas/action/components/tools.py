"""Tools component for managing function tool plugins and MCP tool plugins."""

from typing import Callable

from ....toolkit.logger import get_logger
from ..base import ActionComponent, FunctionToolPlugin

logger = get_logger(__name__)

__all__ = ["ToolsComponent"]


class ToolsComponent(ActionComponent):
    """Manage tool plugins and enforce type checks for dynamic method updates."""

    COMPONENT_NAME = "tools"

    def __init__(self) -> None:
        """Initialize the tools component."""
        super().__init__()

    async def add_method(self, plugin_name: str, method_name: str, func: Callable[..., object]) -> None:
        """
        Add a method to a function tool plugin after validating its type.

        Args:
            plugin_name (str): Name of the plugin that should receive the method.
            method_name (str): Name assigned to the new method.
            func (Callable[..., object]): Callable injected into the plugin.

        Raises:
            ValueError: When the plugin cannot be found.
            TypeError: When the target plugin does not subclass `FunctionToolPlugin`.
        """
        target_plugin = self._plugins.get(plugin_name)
        if target_plugin is None:
            raise ValueError(f"Plugin '{plugin_name}' not found.")

        if not isinstance(target_plugin, FunctionToolPlugin):
            raise TypeError(
                f"Adding methods is only supported for 'FunctionToolPlugin', not '{type(target_plugin).__name__}'."
            )

        await super().add_method(plugin_name, method_name, func)

    async def update_method(self, plugin_name: str, method_name: str, func: Callable[..., object]) -> None:
        """
        Replace an existing method on a function tool plugin.

        Args:
            plugin_name (str): Name of the plugin whose method is updated.
            method_name (str): Method to replace.
            func (Callable[..., object]): Replacement callable.

        Raises:
            ValueError: When the plugin cannot be found.
            TypeError: When the target plugin does not subclass `FunctionToolPlugin`.
        """
        target_plugin = self._plugins.get(plugin_name)
        if target_plugin is None:
            raise ValueError(f"Plugin '{plugin_name}' not found.")

        if not isinstance(target_plugin, FunctionToolPlugin):
            raise TypeError(
                f"Updating methods is only supported for 'FunctionToolPlugin', not '{type(target_plugin).__name__}'."
            )

        await super().update_method(plugin_name, method_name, func)

    async def delete_method(self, plugin_name: str, method_name: str) -> None:
        """
        Remove a method from a function tool plugin.

        Args:
            plugin_name (str): Name of the plugin whose method will be removed.
            method_name (str): Method name to delete.

        Raises:
            ValueError: When the plugin cannot be found.
            TypeError: When the target plugin does not subclass `FunctionToolPlugin`.
        """
        target_plugin = self._plugins.get(plugin_name)
        if target_plugin is None:
            raise ValueError(f"Plugin '{plugin_name}' not found.")

        if not isinstance(target_plugin, FunctionToolPlugin):
            raise TypeError(
                f"Deleting methods is only supported for 'FunctionToolPlugin', not '{type(target_plugin).__name__}'."
            )

        await super().delete_method(plugin_name, method_name)
