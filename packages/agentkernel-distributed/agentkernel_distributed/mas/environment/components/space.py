"""Environment space component."""

from ..base.component_base import EnvironmentComponent

__all__ = ["SpaceComponent"]


class SpaceComponent(EnvironmentComponent):
    """The component that manages spatial environment state."""

    COMPONENT_NAME = "space"

    def __init__(self) -> None:
        """Initialize the space component."""
        super().__init__()
