"""Environment relation component."""

import ray

from ..base.component_base import EnvironmentComponent

__all__ = ["RelationComponent"]


class RelationComponent(EnvironmentComponent):
    """The component that manages relations between agents."""

    COMPONENT_NAME = "relation"

    def __init__(self) -> None:
        """Initialize the relation component."""
        super().__init__()
