"""Base class for agent components that delegate to plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, TypeVar, cast

from ....toolkit.logger import get_logger
from ....toolkit.utils.exceptions import PluginTypeMismatchError
from ....types.configs.agent import AgentComponentConfig
from .plugin_base import AgentPlugin

if TYPE_CHECKING:
    from ..agent import Agent

logger = get_logger(__name__)

__all__ = ["AgentComponent"]

PluginType = TypeVar("PluginType", bound=AgentPlugin)


class AgentComponent(Generic[PluginType], ABC):
    """Abstract base class for agent components backed by a single plugin."""

    COMPONENT_NAME: str = "base"

    def __init__(self) -> None:
        """Create an empty component with no plugin assigned."""
        self._agent: Optional["Agent"] = None
        self._plugin: Optional[PluginType] = None

    @property
    def agent(self) -> Optional["Agent"]:
        """
        Return the agent that owns this component.

        Returns:
            Optional[Agent]: Agent instance when attached, otherwise None.
        """
        return self._agent

    async def init(
        self,
        agent: "Agent",
        config: AgentComponentConfig,
        resource_maps: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Initialize the component and construct its plugin instance.

        Args:
            agent ("Agent"): Agent that owns this component.
            config (AgentComponentConfig): Component configuration specifying the plugin.
            resource_maps (Dict[str, Dict[str, Any]]): Registry containing available plugins and adapters.

        Raises:
            ValueError: When no plugin or more than one plugin is defined.
            PluginTypeMismatchError: When the plugin is not compatible with the component.
        """
        self._agent = agent

        plugin_dict = config.plugin
        if len(plugin_dict) != 1:
            raise ValueError(f"Component '{self.COMPONENT_NAME}' expects exactly one plugin, got {len(plugin_dict)}")

        plugin_name = next(iter(plugin_dict))
        plugin_config = plugin_dict[plugin_name]
        plugin_class = resource_maps["agent_plugins"][plugin_name]

        plugin_kwargs = plugin_config.model_dump(exclude={"adapters"})

        if plugin_config.adapters:
            adapters_map = resource_maps.get("adapters", {})
            resolved_adapters: Dict[str, Any] = {}
            for role, adapter_name in plugin_config.adapters.items():
                adapter_instance = adapters_map.get(adapter_name)
                if adapter_instance is None:
                    raise ValueError(f"Adapter '{adapter_name}' not found in resource_maps for plugin '{plugin_name}'.")
                resolved_adapters[role] = adapter_instance
            plugin_kwargs.update(resolved_adapters)

        plugin_instance = cast(PluginType, plugin_class(**plugin_kwargs))
        self.set_plugin(plugin_instance)

    async def post_init(self) -> None:
        """
        Run post-initialization on the plugin after dependencies are injected.

        Raises:
            RuntimeError: When post_init is called before a plugin is set.
        """
        if not self._plugin:
            raise RuntimeError(f"Component '{self.COMPONENT_NAME}' has no plugin assigned during post_init.")
        await self._plugin.init()
        logger.info("Component '%s' completed plugin post-initialization.", self.COMPONENT_NAME)

    def set_plugin(self, plugin: AgentPlugin) -> None:
        """
        Attach a plugin to this component.

        Args:
            plugin (AgentPlugin): Plugin instance to assign.

        Raises:
            PluginTypeMismatchError: When the plugin's component type does not match.
        """
        if plugin.COMPONENT_TYPE != self.COMPONENT_NAME:
            raise PluginTypeMismatchError(self.COMPONENT_NAME, plugin.COMPONENT_TYPE, plugin.__class__.__name__)

        plugin.component = self
        self._plugin = plugin  # type: ignore[assignment]

    def remove_plugin(self) -> None:
        """Detach the currently assigned plugin."""
        if self._plugin:
            self._plugin.component = None  # type: ignore[assignment]
        self._plugin = None

    def get_plugin(self) -> Optional[PluginType]:
        """
        Return the component's plugin if present.

        Returns:
            Optional[PluginType]: Assigned plugin instance.
        """
        return self._plugin

    def has_plugin(self) -> bool:
        """
        Check whether a plugin has been attached.

        Returns:
            bool: True when a plugin is present.
        """
        return self._plugin is not None

    @abstractmethod
    async def execute(self, current_tick: int) -> None:
        """
        Execute component-specific logic for the given tick.

        Args:
            current_tick (int): Simulation tick at which the component executes.
        """

    async def save_to_db(self) -> None:
        """
        Saves the current state of the component's plugin to the database.
        """
        if self._plugin:
            try:
                await self._plugin.save_to_db()
            except NotImplementedError:
                logger.info(
                    f"Plugin '{self._plugin.__class__.__name__}' on component "
                    f"'{self.COMPONENT_NAME}' does not implement 'save_to_db'. Skipping."
                )
            except Exception as e:
                logger.error(
                    f"Error saving state for plugin '{self._plugin.__class__.__name__}' "
                    f"on component '{self.COMPONENT_NAME}': {e}",
                    exc_info=True,
                )

    async def load_from_db(self) -> None:
        """
        Loads the component's plugin state from the database.
        """
        if self._plugin:
            try:
                await self._plugin.load_from_db()
            except NotImplementedError:
                logger.info(
                    f"Plugin '{self._plugin.__class__.__name__}' on component "
                    f"'{self.COMPONENT_NAME}' does not implement 'load_from_db'. Skipping."
                )
            except Exception as e:
                logger.error(
                    f"Error loading state for plugin '{self._plugin.__class__.__name__}' "
                    f"on component '{self.COMPONENT_NAME}': {e}",
                    exc_info=True,
                )
