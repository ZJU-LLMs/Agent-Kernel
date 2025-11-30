"""Abstract base class for asynchronous key-value adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..base import DatabaseAdapter


class BaseKVAdapter(DatabaseAdapter):
    """Abstract base class for a key-value storage adapter.

    This class defines the standard interface for key-value operations.
    """

    @abstractmethod
    async def get(self, key: str, **kwargs) -> Any:
        """Retrieves a value from the storage by its key.

        Args:
            key (str): The key of the item to retrieve.
            **kwargs: Adapter-specific arguments (e.g., 'field' for hash, 'start'/'end' for list).

        Returns:
            Any: The retrieved value, or None if the key is not found.
        """
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: Any, **kwargs) -> bool:
        """Saves a key-value pair to the storage.

        Args:
            key (str): The key of the item to save.
            value (Any): The value to be stored.
            **kwargs: Adapter-specific arguments (e.g., 'field' for hash).

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str, **kwargs) -> bool:
        """Deletes a key-value pair from the storage.

        Args:
            key (str): The key of the item to delete.
            **kwargs: Adapter-specific arguments (e.g., 'field' for hash).

        Returns:
            bool: True if the key was found and deleted, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(self, key: str, value: Any, **kwargs) -> bool:
        """Updates the value of an existing key in the storage.

        Args:
            key (str): The key of the item to update.
            value (Any): The new value to be stored.
            **kwargs: Adapter-specific arguments (e.g., 'field' for hash).

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Checks if a key exists in the storage.

        Args:
            key (str): The key to check for existence.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def snapshot(self) -> str:
        """Creates a snapshot of the current key-value state.

        Returns:
            str: A unique identifier (e.g., a timestamp) for the
                 created snapshot.
        """
        raise NotImplementedError
