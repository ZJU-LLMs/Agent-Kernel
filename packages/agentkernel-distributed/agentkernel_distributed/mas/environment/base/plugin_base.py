"""Base classes for environment plugins."""

from abc import ABC, abstractmethod
from typing import Type

__all__ = [
    "EnvironmentPlugin",
    "RelationPlugin",
    "SpacePlugin",
    "GenericPlugin",
    "create_plugin_class",
]


class EnvironmentPlugin(ABC):
    """Base class for environment plugins."""

    COMPONENT_TYPE = "base"

    def __init__(self) -> None:
        """Instantiate an environment plugin."""
        pass

    async def init(self) -> None:
        """
        (Optional) Post-initialization hook for the plugin.

        Subclasses can override this method to perform async initialization.
        """
        pass

    async def save_to_db(self) -> None:
        """
        (Optional) Save the plugin's persistent state to the database.

        Subclasses that require persistence should override this method.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"Plugin {self.__class__.__name__} does not implement 'save_to_db'")

    async def load_from_db(self) -> None:
        """
        (Optional) Load the plugin's persistent state from the database.

        Subclasses that require persistence should override this method.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"Plugin {self.__class__.__name__} does not implement 'load_from_db'")


class RelationPlugin(EnvironmentPlugin):
    """Base class for relation environment plugins."""

    COMPONENT_TYPE = "relation"


class SpacePlugin(EnvironmentPlugin):
    """Base class for space-time environment plugins."""

    COMPONENT_TYPE = "space"


class GenericPlugin(EnvironmentPlugin):
    """
    Generic plugin base class that allows users to define custom component types.

    This class enables users to create new environment component types without
    modifying the core package. Users should subclass this and set COMPONENT_TYPE
    to their desired component name.

    Example:
        class WeatherPlugin(GenericPlugin):
            COMPONENT_TYPE = "weather"

            def __init__(self, location: str = "default"):
                super().__init__()
                self.location = location

            async def get_weather(self) -> dict:
                return {"temp": 25, "condition": "sunny"}
    """

    COMPONENT_TYPE = "generic"

    def __init__(self) -> None:
        """Instantiate a generic environment plugin."""
        super().__init__()


def create_plugin_class(component_type: str, class_name: str = None) -> Type[EnvironmentPlugin]:
    """
    Factory function to dynamically create a new plugin base class for a custom component type.

    This allows users to create new environment component types at runtime without
    modifying the core package.

    Args:
        component_type (str): The name of the component type (e.g., "weather", "economy").
        class_name (str, optional): The name for the generated class.
            Defaults to "{ComponentType}Plugin" (e.g., "WeatherPlugin").

    Returns:
        Type[EnvironmentPlugin]: A new plugin base class with the specified COMPONENT_TYPE.

    Example:
        # Create a new plugin base class for "weather" component type
        WeatherPlugin = create_plugin_class("weather")

        # Now users can subclass it
        class MyWeatherPlugin(WeatherPlugin):
            async def get_weather(self):
                return {"temp": 25}
    """
    if class_name is None:
        class_name = f"{component_type.capitalize()}Plugin"

    new_class = type(
        class_name,
        (GenericPlugin,),
        {"COMPONENT_TYPE": component_type}
    )
    return new_class
