"""Core abstractions for action components and plugin orchestration."""

import asyncio
import traceback
from abc import ABC
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from ....toolkit.logger import get_logger
from ....toolkit.models.router import ModelRouter
from ....toolkit.utils.exceptions import PluginTypeMismatchError
from ....types.configs import ActionComponentConfig
from ....types.schemas import ActionResult, CallStatus
from .plugin_base import ActionPlugin

if TYPE_CHECKING:
    from ...controller import BaseController

logger = get_logger(__name__)

__all__ = ["ActionComponent"]


class ActionComponent(ABC):
    """Manage a cohesive set of action plugins and expose their callable methods."""

    COMPONENT_NAME = "base"

    def __init__(self) -> None:
        """Initialize internal registries for plugins and method metadata."""
        self._plugins: Dict[str, ActionPlugin] = {}
        self._methods: Dict[str, Dict[str, Any]] = {}
        self._model: Optional[ModelRouter] = None
        self._controller: Optional["BaseController"] = None

    async def init(self, comp_config: ActionComponentConfig, resource_maps: Dict[str, Dict[str, Any]]) -> None:
        """
        Initialize the component and its plugins from configuration.

        Args:
            comp_config (ActionComponentConfig): Component configuration containing enabled plugins.
            resource_maps (Dict[str, Dict[str, Any]]): Lookup map that provides plugin and adapter classes.
        """
        for plugin_name, plugin_config in comp_config.plugins.items():
            plugin_class = resource_maps["action_plugins"][plugin_name]

            plugin_kwargs = plugin_config.model_dump(exclude={"adapters"})
            plugin_kwargs.update(
                {role: resource_maps["adapters"][adapter_name] for role, adapter_name in plugin_config.adapters.items()}
            )

            plugin_instance = plugin_class(**plugin_kwargs)
            self.add_plugin(plugin_name, plugin_instance)

        await self._prepare_methods()

    async def post_init(
        self, model_router: Optional[ModelRouter] = None, controller: Optional["BaseController"] = None
    ) -> None:
        """
        Perform post-initialization by injecting shared dependencies.

        Args:
            model_router (Optional[ModelRouter]): Handle to the model router actor.
            controller (Optional["BaseController"]): Handle to the controller actor.
        """
        self._model = model_router
        self._controller = controller

        init_tasks = [
            plugin.init(model_router=self._model, controller=self._controller) for plugin in self._plugins.values()
        ]
        try:
            await asyncio.gather(*init_tasks)
            logger.info(f"All plugins in component '{self.COMPONENT_NAME}' have been initialized.")
        except Exception as e:
            logger.error(
                f"A failure occurred during concurrent plugin initialization in component '{self.COMPONENT_NAME}'. Error: {e}"
            )

    def add_plugin(self, name: str, plugin: ActionPlugin) -> None:
        """
        Register a plugin with this component.

        Args:
            name (str): Unique identifier for the plugin.
            plugin (ActionPlugin): Plugin instance to register.

        Raises:
            PluginTypeMismatchError: Raised when the plugin belongs to a different component type.
        """
        if plugin.COMPONENT_TYPE != self.COMPONENT_NAME:
            raise PluginTypeMismatchError(self.COMPONENT_NAME, plugin.COMPONENT_TYPE, plugin.__class__.__name__)
        self._plugins[name] = plugin
        logger.info(f"Plugin '{name}' added to component '{self.COMPONENT_NAME}'.")

    def remove_plugin(self, name: str) -> None:
        """
        Remove a previously registered plugin.

        Args:
            name (str): Identifier of the plugin to remove.
        """
        if name in self._plugins:
            del self._plugins[name]

    def get_plugin(self, name: str) -> Optional[ActionPlugin]:
        """
        Retrieve a plugin by name.

        Args:
            name (str): Identifier of the plugin to retrieve.

        Returns:
            Optional[ActionPlugin]: Plugin instance when found, otherwise None.
        """
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        """
        List identifiers of all loaded plugins.

        Returns:
            List[str]: Collection of registered plugin names.
        """
        return list(self._plugins.keys())

    async def _prepare_methods(self) -> None:
        """
        Collect annotated plugin methods and update the lookup table.

        Raises:
            NameError: Raised when duplicate method names are detected across plugins.
        """
        self._methods = {}

        annotation_types_to_find = ["AgentCall", "ServiceCall"]

        for plugin_name, plugin in self._plugins.items():
            if hasattr(plugin, "prepare"):
                for annotation_type in annotation_types_to_find:
                    prepared_list = await plugin.prepare(annotation_type=annotation_type)
                    if prepared_list:
                        for method_info in prepared_list:
                            method_name = method_info["name"]
                            if method_name not in self._methods:
                                plugin_data = None
                                if annotation_type == "AgentCall":
                                    plugin_data = plugin_name
                                elif annotation_type == "ServiceCall":
                                    plugin_data = [plugin_name]

                                self._methods[method_name] = {
                                    "plugin_name": plugin_data,
                                    "annotation_type": annotation_type,
                                    "method_info": method_info,
                                }
                            else:
                                existing_entry = self._methods[method_name]
                                existing_type = existing_entry["annotation_type"]

                                if existing_type == "AgentCall":
                                    raise NameError(
                                        f"Duplicate method name: '{method_name}' is already registered as an AgentCall "
                                        f"by plugin '{existing_entry['plugin_name']}' and cannot be reused."
                                    )

                                if existing_type == "ServiceCall":
                                    if annotation_type == "ServiceCall":
                                        existing_entry["plugin_name"].append(plugin_name)
                                    else:
                                        raise NameError(
                                            f"Method name conflict: '{method_name}' is already registered as a ServiceCall "
                                            "and cannot be re-registered as an AgentCall."
                                        )

    async def forward(self, method_name: str, arguments: Optional[Dict[str, Any]] = None) -> ActionResult:
        """
        Execute a registered method on the associated plugin.

        Args:
            method_name (str): Name of the method to execute.
            arguments (Optional[Dict[str, Any]]): Keyword arguments to pass to the method.

        Returns:
            ActionResult: Standardized execution outcome.
        """
        if not self._methods:
            await self._prepare_methods()

        args = arguments or {}

        method_data = self._methods.get(method_name)
        if method_data is None:
            return ActionResult.error(
                method_name=method_name,
                message=f"Method '{method_name}' not found in component '{self.COMPONENT_NAME}'.",
            )

        plugin_data = method_data["plugin_name"]

        try:
            if isinstance(plugin_data, str):
                plugin_name = plugin_data
                target_plugin = self._plugins.get(plugin_name)
                if target_plugin is None:
                    return ActionResult.error(
                        method_name=method_name, message=f"Plugin '{plugin_name}' for method '{method_name}' not found."
                    )

                result = await target_plugin.execute(method_name, args)

            elif isinstance(plugin_data, list):
                tasks = []
                plugin_names = plugin_data
                for plugin_name in plugin_names:
                    target_plugin = self._plugins.get(plugin_name)
                    if target_plugin:
                        tasks.append(target_plugin.execute(method_name, args))

                if not tasks:
                    return ActionResult.success(
                        method_name=method_name, message="ServiceCall executed, but no plugins were targeted."
                    )

                results = await asyncio.gather(*tasks, return_exceptions=True)

                all_data = []
                all_errors = []
                for res in results:
                    if isinstance(res, Exception):
                        all_errors.append(str(res))
                    elif isinstance(res, ActionResult) and res.is_error():
                        all_errors.append(res.message)
                    elif isinstance(res, ActionResult):
                        all_data.append(res.data)
                    else:
                        all_data.append(res)

                if all_errors:
                    return ActionResult.error(
                        method_name=method_name,
                        message=f"Errors during broadcast call: {'; '.join(all_errors)}",
                        data=all_data,
                    )
                else:
                    result = ActionResult.success(
                        method_name=method_name, message="Broadcast call successful.", data=all_data
                    )

            else:
                return ActionResult.error(method_name=method_name, message="Invalid plugin routing configuration.")

            return (
                result
                if isinstance(result, ActionResult)
                else ActionResult.error(method_name=method_name, message=str(result))
            )

        except Exception as e:
            logger.error(f"Error executing method '{method_name}': {e}\n{traceback.format_exc()}")
            return ActionResult.error(method_name=method_name, message=str(e))

    def list_methods_names(self, annotation_type: Optional[str] = None) -> List[str]:
        """
        Return method names registered in this component, optionally filtered by annotation type.

        Args:
            annotation_type (Optional[str]): Optional annotation type to filter by (e.g., "AgentCall", "ServiceCall").
                            If None, all method names are returned.

        Returns:
            List[str]: Collection of available method identifiers.
        """
        if annotation_type is None:
            return list(self._methods.keys())

        return [
            method_name
            for method_name, method_data in self._methods.items()
            if method_data.get("annotation_type") == annotation_type
        ]

    async def get_method(
        self,
        method_name: Optional[Union[str, List[str]]] = None,
        annotation_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve schema metadata for one or more methods.

        Args:
            method_name (Optional[Union[str, List[str]]]): Optional single method name or list of method names to fetch.
            annotation_type (Optional[str]): Optional annotation type to filter by (e.g., "AgentCall", "ServiceCall").
                            If None, methods of all types are returned.

        Returns:
            List[Dict[str, Any]]: Method metadata dictionaries for each resolved method.
        """
        if not self._methods:
            await self._prepare_methods()

        def _check_annotation(method_data: Dict[str, Any]) -> bool:
            if annotation_type is None:
                return True

            return method_data.get("annotation_type") == annotation_type

        result = []
        if method_name is None:
            for method_data in self._methods.values():
                if _check_annotation(method_data):
                    result.append(method_data["method_info"].copy())
        else:
            names_to_fetch = [method_name] if isinstance(method_name, str) else method_name

            for name in names_to_fetch:
                method_data = self._methods.get(name)

                if method_data and _check_annotation(method_data):
                    result.append(method_data["method_info"].copy())

        return result

    async def add_method(
        self, plugin_name: str, method_name: str, func: Callable[..., Any], annotation: str = "AgentCall"
    ) -> None:
        """
        Dynamically add a new method to a plugin.

        Args:
            plugin_name (str): Name of the target plugin.
            method_name (str): Name for the newly added method.
            func (Callable[..., Any]): Callable to register on the plugin.
            annotation (str): Annotation tag applied to the callable.

        Raises:
            ValueError: Raised when the target plugin does not exist.
        """
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found in component '{self.COMPONENT_NAME}'.")

        target_plugin = self._plugins[plugin_name]

        if not hasattr(func, "__annotations__"):
            func.__annotations__ = {}
        func.__annotations__["annotation_type"] = annotation
        setattr(target_plugin, method_name, func)

        await self._prepare_methods()
        logger.info(f"Method '{method_name}' added to plugin '{plugin_name}'.")

    async def update_method(self, plugin_name: str, method_name: str, func: Callable[..., Any]) -> None:
        """
        Replace an existing plugin method with a new callable.

        Args:
            plugin_name (str): Name of the target plugin.
            method_name (str): Identifier of the method to replace.
            func (Callable[..., Any]): Callable used to replace the existing method.

        Raises:
            ValueError: Raised when the plugin or method does not exist.
        """
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found in component '{self.COMPONENT_NAME}'.")

        target_plugin = self._plugins[plugin_name]
        if not hasattr(target_plugin, method_name):
            raise ValueError(f"Method '{method_name}' not found in plugin '{plugin_name}'.")

        setattr(target_plugin, method_name, func)
        await self._prepare_methods()
        logger.info(f"Method '{method_name}' in plugin '{plugin_name}' has been updated.")

    async def delete_method(self, plugin_name: str, method_name: str) -> None:
        """
        Remove a dynamic method from a plugin.

        Args:
            plugin_name (str): Name of the target plugin.
            method_name (str): Identifier of the method to remove.

        Raises:
            ValueError: Raised when the plugin or method does not exist.
        """
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found in component '{self.COMPONENT_NAME}'.")

        target_plugin = self._plugins[plugin_name]
        if hasattr(target_plugin, method_name):
            delattr(target_plugin, method_name)
            await self._prepare_methods()
            logger.info(f"Method '{method_name}' deleted from plugin '{plugin_name}'.")
        else:
            raise ValueError(f"Method '{method_name}' not found in plugin '{plugin_name}'.")
