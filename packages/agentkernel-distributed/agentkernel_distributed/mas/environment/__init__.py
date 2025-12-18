from .environment import Environment
from .base import (
    EnvironmentComponent,
    EnvironmentPlugin,
    RelationPlugin,
    SpacePlugin,
    GenericPlugin,
    create_plugin_class,
)
from .components import (
    RelationComponent,
    SpaceComponent,
    GenericComponent,
    create_component_class,
    get_or_create_component_class,
    clear_component_registry,
)

__all__ = [
    # Core classes
    "Environment",
    "EnvironmentComponent",
    "EnvironmentPlugin",
    # Built-in plugin base classes
    "RelationPlugin",
    "SpacePlugin",
    # Built-in component classes
    "RelationComponent",
    "SpaceComponent",
    # Dynamic creation support
    "GenericPlugin",
    "GenericComponent",
    "create_plugin_class",
    "create_component_class",
    "get_or_create_component_class",
    "clear_component_registry",
]
