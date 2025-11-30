"""Base class for all system components."""

from abc import ABC, abstractmethod


class SystemComponent(ABC):
    """Base class for all system components."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the system component."""
        pass

    @abstractmethod
    async def post_init(self, *args, **kwargs) -> None:
        """Run post-initialization tasks."""
        pass

    @abstractmethod
    async def close(self, *args, **kwargs) -> None:
        """Close the component and release resources."""
        pass
