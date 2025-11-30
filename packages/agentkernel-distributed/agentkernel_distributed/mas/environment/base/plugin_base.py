"""Base classes for environment plugins."""

from abc import ABC, abstractmethod

__all__ = ["EnvironmentPlugin", "RelationPlugin", "SpacePlugin"]


class EnvironmentPlugin(ABC):
    """Base class for environment plugins."""

    COMPONENT_TYPE = "base"

    def __init__(self) -> None:
        """Instantiate an environment plugin."""
        pass

    async def save_to_db(self) -> None:
        """
        (Optional) Save the plugin's persistent state to the database.

        Subclasses that require persistence should override this method.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"Plugin {self.__class__.__name__} does not implement 'save_to_db'")

    async def load_from_db(self) -> None:
        """
        (Optional) Load the plugin's persistent state from the database.

        Subclasses that require persistence should override this method.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError(f"Plugin {self.__class__.__name__} does not implement 'load_from_db'")


class RelationPlugin(EnvironmentPlugin):
    """Base class for relation environment plugins."""

    COMPONENT_TYPE = "relation"


class SpacePlugin(EnvironmentPlugin):
    """Base class for space-time environment plugins."""

    COMPONENT_TYPE = "space"
