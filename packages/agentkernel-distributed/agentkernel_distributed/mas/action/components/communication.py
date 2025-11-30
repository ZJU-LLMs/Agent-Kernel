"""Communication component implementation for communication plugins."""

from ..base import ActionComponent
from ....toolkit.logger import get_logger

logger = get_logger(__name__)

__all__ = ["CommunicationComponent"]


class CommunicationComponent(ActionComponent):
    """Component responsible for managing communication plugins."""

    COMPONENT_NAME = "communication"

    def __init__(self) -> None:
        """Initialize the communication component."""
        super().__init__()
