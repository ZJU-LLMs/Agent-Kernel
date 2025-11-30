"""Environment relation component."""

from ..base.component_base import EnvironmentComponent

__all__ = ["RelationComponent"]


class RelationComponent(EnvironmentComponent):
    """A component that manages relationships between agents."""

    COMPONENT_NAME = "relation"

    def __init__(self) -> None:
        """Initialize the `RelationComponent`."""
        super().__init__()
