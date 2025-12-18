from .relation import RelationComponent
from .space import SpaceComponent
from .generic import (
    GenericComponent,
    create_component_class,
    get_or_create_component_class,
    clear_component_registry,
)

__all__ = [
    "RelationComponent",
    "SpaceComponent",
    "GenericComponent",
    "create_component_class",
    "get_or_create_component_class",
    "clear_component_registry",
]
