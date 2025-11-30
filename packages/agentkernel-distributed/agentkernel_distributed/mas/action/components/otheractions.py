"""Generic action component for plugins that do not fit other categories."""

from ..base import ActionComponent

__all__ = ["OtherActionsComponent"]


class OtherActionsComponent(ActionComponent):
    """Manage miscellaneous action plugins using the base component logic."""

    COMPONENT_NAME = "otheractions"

    def __init__(self) -> None:
        """Initialize the otheractions component."""
        super().__init__()
