"""Communication component implementation for action plugins."""

from ..base import ActionComponent
from ....toolkit.logger import get_logger

logger = get_logger(__name__)

__all__ = ["CommunicationComponent"]


class CommunicationComponent(ActionComponent):
    """A component for managing communication-related action plugins."""

    COMPONENT_NAME = "communication"

    def __init__(self) -> None:
        """Initialize the `CommunicationComponent`."""
        super().__init__()
