"""Environment space component."""

from ..base.component_base import EnvironmentComponent

__all__ = ["SpaceComponent"]


class SpaceComponent(EnvironmentComponent):
    """A component that manages the spatial and temporal state of the environment."""

    COMPONENT_NAME = "space"

    def __init__(self) -> None:
        """Initialize the `SpaceComponent`."""
        super().__init__()
