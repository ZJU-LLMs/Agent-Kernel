"""Graph database adapter implementation using Redis as the backend."""

from redis import asyncio as aioredis
from .base import BaseGraphAdapter
from typing import Dict, Any, List, Optional
from ...logger import get_logger
import json
import datetime as dt

logger = get_logger(__name__)


class RedisGraphAdapter(BaseGraphAdapter):
    """
    Implements an asynchronous graph database adapter using Redis.

    This adapter simulates graph operations (nodes, edges) on top of a standard
    Redis instance using keys, hashes, and sets. It is not a wrapper for
    the RedisGraph module.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0) -> None:
        """
        Initializes the RedisGraphAdapter.

        Args:
            host (str): Redis server host. Defaults to "localhost".
            port (int): Redis server port. Defaults to 6379.
            db (int): Redis database number. Defaults to 0.
        """
        self.host = host
        self.port = port
        self.db = db
        self._client: Optional[aioredis.StrictRedis] = None
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._connected = False

    @property
    def client(self) -> Optional[aioredis.StrictRedis]:
        """Expose the underlying redis client for advanced usage."""
        return self._client

    async def connect(self, config: Dict[str, Any], pool: Optional[aioredis.ConnectionPool] = None) -> None:
        """
        Asynchronously connect to the Redis database.

        This method supports two modes:
        1. Shared connection pool: If a `pool` is provided, the client is created from this pool.
        2. Standalone connection: If `pool` is None, a new standalone connection is created based on `config`.

        Args:
            config (Dict[str, Any]): Configuration for a standalone connection when no pool is used.
            pool (Optional[aioredis.ConnectionPool]): An optional, pre-instantiated `aioredis.ConnectionPool` object.

        Raises:
            ConnectionError: If the connection to Redis fails.
        """
        if self._connected:
            return

        if pool:
            self._pool = pool
            self._client = aioredis.StrictRedis(connection_pool=self._pool)
        else:
            if config:
                self.host = config.get("host", self.host)
                self.port = config.get("port", self.port)
                self.db = config.get("db", self.db)

            self._client = aioredis.StrictRedis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
            )

        try:
            await self._ensure_client().ping()
            self._connected = True
        except Exception as e:
            self._client = None
            self._pool = None
            self._connected = False
            raise ConnectionError(f"Failed to connect to Redis: {e}") from e

    async def disconnect(self) -> None:
        """
        Asynchronously disconnects. If a connection pool is used, this only closes the client
        instance of this adapter and releases the underlying connection back to the pool
        without closing the entire pool.
        """
        if self._client:
            try:
                await self._client.aclose()
            except Exception as e:
                logger.error(f"Exception {e} appears in close redis client.")

        self._client = None
        self._pool = None
        self._connected = False

    async def is_connected(self) -> bool:
        """
        Asynchronously checks if the client is connected.

        Returns:
            bool: True if connected, False otherwise.
        """
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except (aioredis.ConnectionError, aioredis.TimeoutError):
            return False

    async def create_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Creates a new node in the graph.

        Args:
            node_id (str): The unique identifier for the node.
            properties (Dict[str, Any]): A dictionary of properties for the node.

        Returns:
            bool: True if the node was created, False if it already exists.
        """
        client = self._ensure_client()
        key = f"node:{node_id}"
        if await client.exists(key):
            return False
        await self._hset_field_by_field(key, properties)
        await client.sadd("nodes", node_id)
        return True

    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Updates the properties of an existing node.

        Args:
            node_id (str): The identifier of the node to update.
            properties (Dict[str, Any]): The properties to update.

        Returns:
            bool: True if the node was updated, False if it does not exist.
        """
        client = self._ensure_client()
        key = f"node:{node_id}"
        if not await client.exists(key):
            return False
        await self._hset_field_by_field(key, properties)
        return True

    async def delete_node(self, node_id: str) -> bool:
        """
        Deletes a node and all its associated edges.

        Args:
            node_id (str): The identifier of the node to delete.

        Returns:
            bool: True if the node was deleted, False if it did not exist.
        """
        client = self._ensure_client()
        key = f"node:{node_id}"
        if not await client.exists(key):
            return False
        await client.delete(key)
        out_neighbors = await client.smembers(f"node:{node_id}:out_neighbors")
        for target_id in out_neighbors:
            await self.delete_edge(node_id, target_id)
        in_neighbors = await client.smembers(f"node:{node_id}:in_neighbors")
        for source_id in in_neighbors:
            await self.delete_edge(source_id, node_id)
        await client.delete(f"node:{node_id}:out_neighbors", f"node:{node_id}:in_neighbors")
        await client.srem("nodes", node_id)
        return True

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a node's properties.

        Args:
            node_id (str): The identifier of the node to retrieve.

        Returns:
            Optional[Dict[str, Any]]: A dictionary of the node's properties, or None if not found.
        """
        client = self._ensure_client()
        key = f"node:{node_id}"
        if not await client.exists(key):
            return None
        node_data = await client.hgetall(key)
        return self._deserialize_properties(node_data)

    async def create_edge(self, source_id: str, target_id: str, properties: Dict[str, Any]) -> bool:
        """
        Creates a directed edge between two nodes.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.
            properties (Dict[str, Any]): Properties for the edge.

        Returns:
            bool: True if the edge was created, False if it already exists or nodes are missing.
        """
        client = self._ensure_client()
        if not await client.exists(f"node:{source_id}") or not await client.exists(f"node:{target_id}"):
            return False
        edge_key = f"edge:{source_id}:{target_id}"
        if await client.exists(edge_key):
            return False
        await self._hset_field_by_field(edge_key, properties)
        await client.sadd(f"node:{source_id}:out_neighbors", target_id)
        await client.sadd(f"node:{target_id}:in_neighbors", source_id)
        return True

    async def update_edge(self, source_id: str, target_id: str, properties: Dict[str, Any]) -> bool:
        """
        Updates the properties of an existing edge.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.
            properties (Dict[str, Any]): The properties to update.

        Returns:
            bool: True if the edge was updated, False if it does not exist.
        """
        client = self._ensure_client()
        edge_key = f"edge:{source_id}:{target_id}"
        if not await client.exists(edge_key):
            return False
        await self._hset_field_by_field(edge_key, properties)
        return True

    async def delete_edge(self, source_id: str, target_id: str) -> bool:
        """
        Deletes a directed edge.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.

        Returns:
            bool: True if the edge was deleted, False if it did not exist.
        """
        client = self._ensure_client()
        edge_key = f"edge:{source_id}:{target_id}"
        if not await client.exists(edge_key):
            return False
        await client.delete(edge_key)
        await client.srem(f"node:{source_id}:out_neighbors", target_id)
        await client.srem(f"node:{target_id}:in_neighbors", source_id)
        return True

    async def get_edge(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves an edge's properties.

        Args:
            source_id (str): The identifier of the source node.
            target_id (str): The identifier of the target node.

        Returns:
            Optional[Dict[str, Any]]: A dictionary of the edge's properties, or None if not found.
        """
        client = self._ensure_client()
        edge_key = f"edge:{source_id}:{target_id}"
        if not await client.exists(edge_key):
            return None
        edge_data = await client.hgetall(edge_key)
        deserialized_data = self._deserialize_properties(edge_data)
        deserialized_data["source_id"] = source_id
        deserialized_data["target_id"] = target_id
        return deserialized_data

    async def get_node_out_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all outgoing edges for a given node.

        Args:
            node_id (str): The identifier of the node.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing an outgoing edge.
        """
        client = self._ensure_client()
        results = []
        out_neighbors = await client.smembers(f"node:{node_id}:out_neighbors")
        for target_id in out_neighbors:
            edge_data = await self.get_edge(node_id, target_id)
            if edge_data:
                results.append(edge_data)
        return results

    async def get_node_in_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all incoming edges for a given node.

        Args:
            node_id (str): The identifier of the node.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing an incoming edge.
        """
        client = self._ensure_client()
        results = []
        in_neighbors = await client.smembers(f"node:{node_id}:in_neighbors")
        for source_id in in_neighbors:
            edge_data = await self.get_edge(source_id, node_id)
            if edge_data:
                results.append(edge_data)
        return results

    async def get_total_nodes(self) -> int:
        """
        Gets the total number of nodes in the graph.

        Returns:
            int: The total number of nodes.
        """
        client = self._ensure_client()
        return await client.scard("nodes")

    async def get_total_edges(self) -> int:
        """
        Gets the total number of edges in the graph.

        Returns:
            int: The total number of edges.
        """
        client = self._ensure_client()
        count = 0
        async for _ in client.scan_iter("edge:*"):
            count += 1
        return count

    async def incr_node(
        self,
        node_id: str,
        amount: int = 1,
        field: Optional[str] = None,
    ) -> int:
        """
        Atomically increments the integer value of a Redis hash field for a node.

        If the hash field does not exist, it's initialized to 0 before the increment.

        Args:
            node_id (str): The ID of the node.
            field (Optional[str]): The hash field to increment. Must be provided.
            amount (int): The integer value to add (can be negative for decrement). Defaults to 1.

        Returns:
            int: The new integer value after the increment.

        Raises:
            ConnectionError: If the Redis client is not connected.
            ValueError: If the field is not provided or the key stores a non-integer value.
        """
        if field is None:
            raise ValueError("Field must be provided for node increment operation.")

        client = self._ensure_client()
        key = f"node:{node_id}"
        return await client.hincrby(key, field, amount)

    async def import_data(self, data: Dict[str, Any]) -> None:
        """
        Optimized batch import of graph data using a single pipeline.

        Args:
            data (Dict[str, Any]): A dictionary containing 'nodes' and 'edges' to import.
        """
        client = self._ensure_client()
        if not data:
            return

        pipe = client.pipeline(transaction=False)

        nodes_to_add = data.get("nodes", [])
        if nodes_to_add:
            node_ids_to_register = [node["id"] for node in nodes_to_add]
            for node in nodes_to_add:
                node_id = node["id"]
                properties = node.get("properties", {})
                node_key = f"node:{node_id}"
                if properties:
                    for field, value in properties.items():
                        pipe.hset(node_key, field, self._serialize_value(value))
            if node_ids_to_register:
                pipe.sadd("nodes", *node_ids_to_register)

        edges_to_add = data.get("edges", [])
        if edges_to_add:
            for edge in edges_to_add:
                source_id = edge["source_id"]
                target_id = edge["target_id"]
                properties = edge.get("properties", {})
                edge_key = f"edge:{source_id}:{target_id}"
                if properties:
                    for field, value in properties.items():
                        pipe.hset(edge_key, field, self._serialize_value(value))
                pipe.sadd(f"node:{source_id}:out_neighbors", target_id)
                pipe.sadd(f"node:{target_id}:in_neighbors", source_id)

        await pipe.execute()

    async def export_data(self) -> Dict[str, Any]:
        """
        Optimized batch export of graph data.

        Returns:
            Dict[str, Any]: A dictionary containing all 'nodes' and 'edges' from the graph.
        """
        client = self._ensure_client()

        node_ids = await client.smembers("nodes")
        node_keys = [f"node:{node_id}" for node_id in node_ids]
        edge_keys = [key async for key in client.scan_iter("edge:*")]

        all_keys = node_keys + edge_keys
        if not all_keys:
            return {"nodes": [], "edges": []}

        pipe = client.pipeline()
        for key in all_keys:
            pipe.hgetall(key)
        all_data_raw = await pipe.execute()

        nodes = []
        edges = []
        for key, properties_raw in zip(all_keys, all_data_raw):
            if not properties_raw:
                continue

            properties = self._deserialize_properties(properties_raw)
            if key.startswith("node:"):
                node_id = key.split(":", 1)[1]
                nodes.append({"id": node_id, "properties": properties})
            elif key.startswith("edge:"):
                _, source_id, target_id = key.split(":", 2)
                edges.append(
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "properties": properties,
                    }
                )
        return {"nodes": nodes, "edges": edges}

    async def clear(self) -> bool:
        """
        Safely clears all graph-related keys from the current database without affecting
        data managed by other adapters (e.g., KV adapter).

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        client = self._ensure_client()
        try:
            pipe = client.pipeline()
            graph_keys_to_delete = []

            async for key in client.scan_iter(match="node:*"):
                graph_keys_to_delete.append(key)
            async for key in client.scan_iter(match="edge:*"):
                graph_keys_to_delete.append(key)

            graph_keys_to_delete.append("nodes")

            if graph_keys_to_delete:
                pipe.delete(*graph_keys_to_delete)

            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed to clear graph data: {e}")
            return False

    async def snapshot(self, tick: int) -> str:
        """
        Creates a snapshot of the current graph database state, associated
        with a simulation tick.

        It uses `export_data()` to get the entire graph structure, serializes it
        to JSON, and stores it in a key identified by the tick and timestamp.

        Args:
            tick (int): The current simulation tick number.

        Returns:
            The ISO 8601 timestamp string used to identify this snapshot.

        Raises:
            ConnectionError: If the adapter is not connected to Redis.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Adapter is not connected to Redis.")

        client = self._ensure_client()
        now = dt.datetime.now(dt.timezone.utc)
        timestamp_iso = now.isoformat()

        snapshot_data_key = f"history:graph:data:{tick}:{timestamp_iso}"
        snapshots_zset_key = "history:graph:snapshots"

        graph_data = await self.export_data()
        serialized_graph = json.dumps(graph_data)

        pipe = client.pipeline()
        pipe.set(snapshot_data_key, serialized_graph)
        pipe.zadd(snapshots_zset_key, {snapshot_data_key: tick})
        await pipe.execute()

        return timestamp_iso

    async def undo(self, tick: int) -> bool:
        """
        Restores the graph database to the state of the snapshot at or
        just before the specified tick.

        This operation is safe and does not affect non-graph data.

        Args:
            tick (int): The simulation tick to restore to.

        Returns:
            True if the undo operation was successful, False if no
            suitable snapshot was found.

        Raises:
            ConnectionError: If the adapter is not connected to Redis.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Adapter is not connected to Redis.")

        client = self._ensure_client()
        snapshots_zset_key = "history:graph:snapshots"

        # 1. Find and delete all snapshots after the target tick
        future_snapshots = await client.zrangebyscore(snapshots_zset_key, f"({tick}", "+inf")
        if future_snapshots:
            pipe = client.pipeline()
            pipe.delete(*future_snapshots)
            pipe.zrem(snapshots_zset_key, *future_snapshots)
            await pipe.execute()

        # 2. Find the target snapshot to restore to
        target_snapshot_keys = await client.zrevrangebyscore(
            snapshots_zset_key,
            max=tick,
            min="-inf",
            start=0,
            num=1,
        )

        if not target_snapshot_keys:
            logger.warning("No graph snapshot found at or before tick %d", tick)
            return False

        snapshot_to_restore_key = target_snapshot_keys[0]
        logger.info("Restoring graph from snapshot: %s", snapshot_to_restore_key)

        # 3. Clear the current graph state
        await self.clear()

        # 4. Restore data from the target snapshot string
        serialized_graph = await client.get(snapshot_to_restore_key)
        if serialized_graph:
            graph_data = json.loads(serialized_graph)
            await self.import_data(graph_data)
        else:
            logger.info("Graph snapshot %s was empty. Graph cleared.", snapshot_to_restore_key)

        return True

    def _ensure_client(self) -> aioredis.StrictRedis:
        """
        Ensure the Redis client is available.

        Returns:
            aioredis.StrictRedis: The Redis client instance.

        Raises:
            ConnectionError: If the client is not connected.
        """
        if not self._client:
            raise ConnectionError("Redis client is not connected.")
        return self._client

    def _serialize_value(self, value: Any) -> Any:
        """
        Serializes a value for storage in Redis.

        Booleans and complex types (dicts, lists) are JSON-encoded.
        Other primary types are returned as-is.

        Args:
            value: The value to serialize.

        Returns:
            The serialized value.
        """
        if isinstance(value, bool):
            return json.dumps(value)

        if not isinstance(value, (str, int, float, bytes)):
            return json.dumps(value)
        return value

    async def _hset_field_by_field(self, key: str, mapping: Dict[str, Any]) -> None:
        """
        Sets fields in a Redis hash one by one, serializing values.

        Args:
            key: The Redis key for the hash.
            mapping: A dictionary of fields and values to set.
        """
        client = self._ensure_client()
        for field, value in mapping.items():
            serialized_value = self._serialize_value(value)
            await client.hset(key, field, serialized_value)

    def _deserialize_properties(self, props: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserializes all values from a properties dictionary retrieved from Redis.

        Attempts to JSON-decode values; falls back to the raw value on failure.

        Args:
            props: The dictionary of properties with potentially serialized values.

        Returns:
            A dictionary with deserialized values.
        """
        deserialized = {}
        for k, v in props.items():
            try:
                deserialized[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                deserialized[k] = v
        return deserialized
