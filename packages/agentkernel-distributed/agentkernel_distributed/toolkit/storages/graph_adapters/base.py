"""Abstract base class for graph database adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..base import DatabaseAdapter


class BaseGraphAdapter(DatabaseAdapter):
    """Shared interface for asynchronous graph store adapters."""

    @abstractmethod
    async def create_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Create a node with the given identifier and property map.

        Args:
            node_id (str): The unique identifier for the node.
            properties (Dict[str, Any]): A dictionary of properties for the node.

        Returns:
            bool: True if the node was created successfully, False otherwise.
        """

    @abstractmethod
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update a node's properties.

        Args:
            node_id (str): The unique identifier for the node.
            properties (Dict[str, Any]): A dictionary of properties to update.

        Returns:
            bool: True if the node was updated successfully, False otherwise.
        """

    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and all associated edges.

        Args:
            node_id (str): The unique identifier for the node.

        Returns:
            bool: True if the node was deleted successfully, False otherwise.
        """

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a node and its stored properties.

        Args:
            node_id (str): The unique identifier for the node.

        Returns:
            Optional[Dict[str, Any]]: A dictionary of the node's properties, or None if not found.
        """

    @abstractmethod
    async def create_edge(self, source_id: str, target_id: str, properties: Dict[str, Any]) -> bool:
        """
        Create a directed edge between two nodes.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.
            properties (Dict[str, Any]): A dictionary of properties for the edge.

        Returns:
            bool: True if the edge was created successfully, False otherwise.
        """

    @abstractmethod
    async def update_edge(self, source_id: str, target_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update an existing edge between two nodes.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.
            properties (Dict[str, Any]): A dictionary of properties to update.

        Returns:
            bool: True if the edge was updated successfully, False otherwise.
        """

    @abstractmethod
    async def delete_edge(self, source_id: str, target_id: str) -> bool:
        """
        Delete a directed edge.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.

        Returns:
            bool: True if the edge was deleted successfully, False otherwise.
        """

    @abstractmethod
    async def get_edge(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Return edge metadata when present.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.

        Returns:
            Optional[Dict[str, Any]]: A dictionary of the edge's properties, or None if not found.
        """

    @abstractmethod
    async def get_node_out_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Return all outgoing edges for the given node.

        Args:
            node_id (str): The unique identifier for the node.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing an outgoing edge.
        """

    @abstractmethod
    async def get_node_in_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Return all incoming edges for the given node.

        Args:
            node_id (str): The unique identifier for the node.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing an incoming edge.
        """

    @abstractmethod
    async def get_total_nodes(self) -> int:
        """
        Return the total number of nodes in the graph.

        Returns:
            int: The total number of nodes.
        """

    @abstractmethod
    async def get_total_edges(self) -> int:
        """
        Return the total number of edges in the graph.

        Returns:
            int: The total number of edges.
        """

    @abstractmethod
    async def snapshot(self) -> str:
        """Creates a snapshot of the current key-value state.

        Returns:
            str: A unique identifier (e.g., a timestamp) for the
                 created snapshot.
        """
        raise NotImplementedError

