"""Generic action component for plugins that do not fit other categories."""

from ..base import ActionComponent

__all__ = ["OtherActionsComponent"]


class OtherActionsComponent(ActionComponent):
    """A component for managing miscellaneous action plugins."""

    COMPONENT_NAME = "otheractions"

    def __init__(self) -> None:
        """Initialize the `OtherActionsComponent`."""
        super().__init__()
