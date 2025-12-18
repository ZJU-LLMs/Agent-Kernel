"""Generic environment component for dynamic component type creation."""

from typing import Dict, Type

from ..base.component_base import EnvironmentComponent

__all__ = ["GenericComponent", "create_component_class", "get_or_create_component_class"]

# Registry to cache dynamically created component classes
_component_class_registry: Dict[str, Type[EnvironmentComponent]] = {}


class GenericComponent(EnvironmentComponent):
    """
    Generic environment component that can be configured with any component name.

    This class enables users to create new environment component types without
    modifying the core package. The COMPONENT_NAME can be set dynamically.

    Example:
        # Create a generic component for "weather"
        weather_component = GenericComponent("weather")
    """

    COMPONENT_NAME = "generic"

    def __init__(self, component_name: str = None) -> None:
        """
        Initialize the generic component.

        Args:
            component_name (str, optional): The name of the component type.
                If provided, overrides the class-level COMPONENT_NAME.
        """
        if component_name is not None:
            self.COMPONENT_NAME = component_name
        super().__init__()


def create_component_class(component_name: str, class_name: str = None) -> Type[EnvironmentComponent]:
    """
    Factory function to dynamically create a new component class for a custom component type.

    This allows users to create new environment component types at runtime without
    modifying the core package.

    Args:
        component_name (str): The name of the component type (e.g., "weather", "economy").
        class_name (str, optional): The name for the generated class.
            Defaults to "{ComponentName}Component" (e.g., "WeatherComponent").

    Returns:
        Type[EnvironmentComponent]: A new component class with the specified COMPONENT_NAME.

    Example:
        # Create a new component class for "weather" component type
        WeatherComponent = create_component_class("weather")

        # Register it in your registry
        environment_component_class_map["weather"] = WeatherComponent
    """
    if class_name is None:
        class_name = f"{component_name.capitalize()}Component"

    new_class = type(
        class_name,
        (EnvironmentComponent,),
        {"COMPONENT_NAME": component_name}
    )
    return new_class


def get_or_create_component_class(component_name: str) -> Type[EnvironmentComponent]:
    """
    Get an existing component class or create a new one for the given component name.

    This function maintains a registry of dynamically created component classes
    to ensure consistency and avoid creating duplicate classes.

    Args:
        component_name (str): The name of the component type (e.g., "weather", "economy").

    Returns:
        Type[EnvironmentComponent]: The component class for the specified component type.

    Example:
        # Get or create a component class for "weather"
        WeatherComponent = get_or_create_component_class("weather")

        # Calling again returns the same class
        assert get_or_create_component_class("weather") is WeatherComponent
    """
    # Check built-in components first
    if component_name == "relation":
        from .relation import RelationComponent
        return RelationComponent
    elif component_name == "space":
        from .space import SpaceComponent
        return SpaceComponent

    # Check the registry for cached dynamic components
    if component_name in _component_class_registry:
        return _component_class_registry[component_name]

    # Create a new component class and cache it
    new_class = create_component_class(component_name)
    _component_class_registry[component_name] = new_class
    return new_class


def clear_component_registry() -> None:
    """
    Clear the registry of dynamically created component classes.

    This is primarily useful for testing purposes.
    """
    _component_class_registry.clear()

