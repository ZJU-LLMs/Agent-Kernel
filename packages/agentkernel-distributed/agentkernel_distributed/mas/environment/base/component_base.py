"""Base class for environment components."""

from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from .plugin_base import EnvironmentPlugin
from ....toolkit.utils.exceptions import PluginTypeMismatchError
from ....toolkit.logger import get_logger
from ....types.configs import DatabaseConfig, EnvironmentComponentConfig

logger = get_logger(__name__)

__all__ = ["EnvironmentComponent"]


class EnvironmentComponent(ABC):
    """
    Abstract base class for an environment component.

    Each component acts as a container for a single, specialized plugin that
    defines its behavior. It handles the initialization of this plugin and
    forwards calls to it.
    """

    COMPONENT_NAME: str = "base"

    def __init__(self) -> None:
        """Initializes the EnvironmentComponent."""
        self._plugin: Optional[EnvironmentPlugin] = None
        self._plugin_methods: Dict[str, str] = {}

    async def init(
        self,
        comp_config: EnvironmentComponentConfig,
        resource_maps: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Initializes the component's single plugin.

        It injects file-based data and configures all its required adapters.

        Args:
            comp_config (EnvironmentComponentConfig): The configuration object for
                this specific component.
            resource_maps (Dict[str, Dict[str, Any]]): A dictionary mapping
                resource types (like 'environment_plugins', 'adapters') to
                their corresponding class implementations.

        Raises:
            ValueError: If the component configuration does not contain exactly one plugin.
        """

        plugin_configs = comp_config.plugin
        if len(plugin_configs) != 1:
            raise ValueError(
                f"Component '{self.COMPONENT_NAME}' must have exactly one plugin, but got {len(plugin_configs)}"
            )
        plugin_name, plugin_config = next(iter(plugin_configs.items()))
        plugin_class = resource_maps["environment_plugins"][plugin_name]

        plugin_kwargs = plugin_config.model_dump(exclude={"adapters"})
        plugin_kwargs.update(
            {role: resource_maps["adapters"][adapter_name] for role, adapter_name in plugin_config.adapters.items()}
        )

        plugin_instance = plugin_class(**plugin_kwargs)
        self.set_plugin(plugin_instance)
        logger.info(f"Plugin '{plugin_name}' for component '{self.COMPONENT_NAME}' initialized successfully.")

    async def post_init(self) -> None:
        """
        Performs post-initialization dependency injection for the plugin.
        """
        if self._plugin and hasattr(self._plugin, "init") and callable(self._plugin.init):
            await self._plugin.init()
        logger.info(f"Actor '{self.COMPONENT_NAME}' and its plugins initialized.")

    def set_plugin(self, plugin: EnvironmentPlugin) -> None:
        """
        Registers a plugin instance with this component.

        Args:
            plugin (EnvironmentPlugin): The plugin instance to register.

        Raises:
            PluginTypeMismatchError: If the plugin's COMPONENT_TYPE does not
                match the component's COMPONENT_NAME.
        """
        if plugin.COMPONENT_TYPE != self.COMPONENT_NAME:
            raise PluginTypeMismatchError(self.COMPONENT_NAME, plugin.COMPONENT_TYPE, plugin.__class__.__name__)

        self._plugin = plugin

    async def forward(self, method_name: str, *args, **kwargs) -> Any:
        """
        Unified method forwarding entry point.

        This method receives a method name and arguments, then calls the
        corresponding method on the registered plugin.

        Args:
            method_name (str): The name of the method to call on the plugin.
            *args: Positional arguments for the plugin method.
            **kwargs: Keyword arguments for the plugin method.

        Returns:
            Any: The return value from the called plugin method.

        Raises:
            RuntimeError: If no plugin is registered with this component.
            AttributeError: If the plugin does not have a method with the given name.
            TypeError: If the attribute with the given name is not a callable method.
        """
        if not self._plugin:
            raise RuntimeError(f"Component '{self.COMPONENT_NAME}' has no plugin registered")

        plugin = self._plugin
        if not hasattr(plugin, method_name):
            raise AttributeError(f"Plugin on component '{self.COMPONENT_NAME}' has no method '{method_name}'")

        method_to_call = getattr(plugin, method_name)
        if not callable(method_to_call):
            raise TypeError(f"Attribute '{method_name}' on plugin is not callable")

        return await method_to_call(*args, **kwargs)

    def remove_plugin(self) -> None:
        """Removes the registered plugin from this component."""
        self._plugin = None

    def get_plugin(self) -> Optional[EnvironmentPlugin]:
        """
        Gets the currently registered plugin.

        Returns:
            Optional[EnvironmentPlugin]: The plugin instance, or None if no
            plugin is registered.
        """
        return self._plugin

    def has_plugin(self) -> bool:
        """
        Checks if a plugin is registered with this component.

        Returns:
            bool: True if a plugin is registered, False otherwise.
        """
        return self._plugin is not None
