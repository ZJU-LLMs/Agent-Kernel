"""Redis-backed asynchronous key-value adapter."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from redis import asyncio as aioredis

from ...logger import get_logger
from .base import BaseKVAdapter

from ....types.configs.database import PoolConfig

logger = get_logger(__name__)


class RedisKVAdapter(BaseKVAdapter):
    """Asynchronous key-value adapter using Redis."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0) -> None:
        """
        Initializes the RedisKVAdapter.

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
        Establish a connection using an optional shared connection pool.

        Args:
            config (Dict[str, Any]): Connection configuration applied when no
                pool is provided.
            pool (Optional[aioredis.ConnectionPool]): Optional pre-existing
                Redis connection pool.

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
        except Exception as exc:
            self._client = None
            self._pool = None
            self._connected = False
            raise ConnectionError(f"Failed to connect to Redis: {exc}") from exc

    async def disconnect(self) -> None:
        """Close the client connection, releasing pooled connections when used."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception as exc:
                logger.error("Exception while closing redis client: %s", exc)

        self._client = None

        self._pool = None
        self._connected = False

    async def is_connected(self) -> bool:
        """
        Return True when the adapter has an active connection.

        Returns:
            bool: True if connected, False otherwise.
        """
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except (aioredis.ConnectionError, aioredis.TimeoutError):
            return False

    async def set(self, key: str, value: Any, **kwargs) -> bool:
        """
        Store a value using a representation derived from its Python type.

        Args:
            key (str): Key to set.
            value (Any): Value to store.
            **kwargs:
                field (Optional[str]): Optional hash field; when provided,
                    the value is stored via ``HSET``.

        Returns:
            bool: True when the value is stored successfully.
        """
        client = self._ensure_client()
        field = kwargs.get("field")

        if field:
            result = await client.hset(key, field, self._serialize(value))
            return result >= 0

        dtype = self._detect_type(value)

        if dtype == "string":
            return await client.set(key, self._serialize(value))
        if dtype == "hash":
            serialized_map = {f: self._serialize(v) for f, v in value.items()}
            await self._hset_field_by_field(client, key, serialized_map)
            return True
        if dtype == "list":
            await client.delete(key)
            serialized_values = [self._serialize(v) for v in value]
            if serialized_values:
                return await client.rpush(key, *serialized_values) > 0
            return True

        return False

    async def get(
        self,
        key: str,
        **kwargs,
    ) -> Any:
        """
        Retrieve data while respecting the native Redis storage type.

        Args:
            key (str): Redis key to fetch.
            **kwargs:
                field (Optional[str]): Optional hash field.
                start (int): List-range start index (default 0).
                end (int): List-range end index (default -1).

        Returns:
            Any: Deserialised value or None when the key does not exist.
        """
        client = self._ensure_client()
        field = kwargs.get("field")
        start = kwargs.get("start", 0)
        end = kwargs.get("end", -1)

        redis_type = await client.type(key)

        if redis_type == "string":
            val = await client.get(key)
            return self._deserialize(val)

        if redis_type == "hash":
            if field:
                val = await client.hget(key, field)
                return self._deserialize(val)
            data = await client.hgetall(key)
            return {f: self._deserialize(v) for f, v in data.items()}

        if redis_type == "list":
            values = await client.lrange(key, start, end)
            return [self._deserialize(v) for v in values]

        return None

    async def delete(self, key: str, **kwargs) -> bool:
        """
        Delete a key or hash fields depending on the stored type.

        Args:
            key (str): Redis key to delete.
            **kwargs:
                field (Optional[Union[str, Sequence[str]]]): Optional hash
                    field or fields to delete.

        Returns:
            bool: True when data was deleted.
        """
        client = self._ensure_client()
        field = kwargs.get("field")
        redis_type = await client.type(key)

        if redis_type in ("string", "list"):
            return await client.delete(key) > 0

        if redis_type == "hash":
            if field:
                fields = [field] if isinstance(field, str) else list(field)
                return await client.hdel(key, *fields) > 0
            return await client.delete(key) > 0

        return False

    async def update(self, key: str, value: Any, **kwargs) -> bool:
        """
        Update an existing key or hash field.

        Args:
            key (str): Redis key to update.
            value (Any): Replacement value.
            **kwargs:
                field (Optional[str]): Optional hash field.

        Returns:
            bool: True when the key existed and has been updated.
        """
        client = self._ensure_client()
        if not await client.exists(key):
            return False
        return await self.set(key, value, **kwargs)

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the database.

        Args:
            key (str): A key name to check.

        Returns:
            bool: True if the key exists, False otherwise.
        """
        client = self._ensure_client()
        if not key:
            return False
        return await client.exists(key) > 0

    async def push(self, key: str, *values: Any, left: bool = True) -> int:
        """
        Push values into a list stored at ``key``.

        Args:
            key (str): List key.
            *values (Any): Values appended to the list.
            left (bool): When True push values to the left; otherwise push
                to the right.

        Returns:
            int: New list length.
        """
        client = self._ensure_client()
        serialized_values = [self._serialize(v) for v in values]
        if left:
            return await client.lpush(key, *serialized_values)
        return await client.rpush(key, *serialized_values)

    async def export_data(self, prefix: Optional[Union[str, Iterable[str]]] = None) -> Dict[str, Any]:
        """
        Export data with optional prefix filtering while minimising round-trips.

        Args:
            prefix (Optional[Union[str, Iterable[str]]]): Single prefix
                string or iterable of prefixes.

        Returns:
            Dict[str, Any]: Mapping of keys to deserialised values.
        """
        client = self._ensure_client()

        patterns = ["*"]
        if prefix is not None:
            if isinstance(prefix, str):
                patterns = [f"{prefix}:*"]
            else:
                patterns = [f"{p}:*" for p in prefix]

        keys: List[str] = []
        for pattern in patterns:
            async for key in client.scan_iter(match=pattern):
                if not self._is_reserved_key(key):
                    keys.append(key)

        if not keys:
            return {}

        pipe = client.pipeline()
        for key in keys:
            pipe.type(key)
        key_types = await pipe.execute()

        keys_by_type: Dict[str, List[str]] = {"string": [], "hash": [], "list": []}
        for key, key_type in zip(keys, key_types):
            keys_by_type.setdefault(key_type, []).append(key)

        data: Dict[str, Any] = {}

        string_keys = keys_by_type.get("string", [])
        if string_keys:
            string_values = await client.mget(string_keys)
            for key, value in zip(string_keys, string_values):
                data[key] = self._deserialize(value)

        hash_keys = keys_by_type.get("hash", [])
        list_keys = keys_by_type.get("list", [])
        pipe = client.pipeline()
        for key in hash_keys:
            pipe.hgetall(key)
        for key in list_keys:
            pipe.lrange(key, 0, -1)
        results = await pipe.execute()

        hash_results = results[: len(hash_keys)]
        list_results = results[len(hash_keys) :]

        for key, value_map in zip(hash_keys, hash_results):
            data[key] = {field: self._deserialize(value) for field, value in value_map.items()}
        for key, value_list in zip(list_keys, list_results):
            data[key] = [self._deserialize(value) for value in value_list]

        return data

    async def import_data(self, data: Dict[str, Any]) -> None:
        """
        Import a dictionary of key/value pairs into Redis in a batched fashion.

        Args:
            data (Dict[str, Any]): Mapping of keys to values.
        """
        client = self._ensure_client()
        if not data:
            return

        pipe = client.pipeline(transaction=False)
        mset_payload: Dict[str, Any] = {}

        for key, value in data.items():
            dtype = self._detect_type(value)
            if dtype == "string":
                mset_payload[key] = self._serialize(value)
            elif dtype == "hash":
                for field, field_value in value.items():
                    pipe.hset(key, field, self._serialize(field_value))
            elif dtype == "list":
                pipe.delete(key)
                serialized_values = [self._serialize(v) for v in value]
                if serialized_values:
                    pipe.rpush(key, *serialized_values)

        if mset_payload:
            pipe.mset(mset_payload)

        await pipe.execute()

    async def snapshot(self, tick: int) -> str:
        """
        Persist a snapshot of the current key-value state under the
        ``history:kv`` namespace, associated with a simulation tick.

        Args:
            tick (int): The current simulation tick number.

        Returns:
            str: The ISO 8601 timestamp string used to identify this snapshot.

        Raises:
            ConnectionError: If the adapter is not connected to Redis.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Adapter is not connected to Redis.")

        client = self._client
        now = dt.datetime.now(dt.timezone.utc)
        timestamp_iso = now.isoformat()

        snapshot_data_key = f"history:kv:data:{tick}:{timestamp_iso}"
        snapshots_zset_key = "history:kv:snapshots"

        pipe = client.pipeline()

        async for key in client.scan_iter():
            if self._is_reserved_key(key):
                continue
            value = await self.get(key)
            pipe.hset(snapshot_data_key, key, json.dumps(value))

        pipe.zadd(snapshots_zset_key, {snapshot_data_key: tick})
        await pipe.execute()

        return timestamp_iso

    async def undo(self, tick: int) -> bool:
        """
        Restore key-value data to the most recent snapshot at or before
        the specified ``tick``. If multiple snapshots exist for the
        target tick, the one with the latest physical timestamp is used.

        Args:
            tick (int): The simulation tick to restore to.

        Returns:
            bool: True when a snapshot was located and restored.

        Raises:
            ConnectionError: If the adapter is not connected to Redis.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Adapter is not connected to Redis.")

        client = self._client
        snapshots_zset_key = "history:kv:snapshots"

        # 1. Find and delete all snapshots after the target tick.
        future_snapshots = await client.zrangebyscore(snapshots_zset_key, f"({tick}", "+inf")
        if future_snapshots:
            pipe = client.pipeline()
            pipe.delete(*future_snapshots)
            pipe.zrem(snapshots_zset_key, *future_snapshots)
            await pipe.execute()

        # 2. Find the target snapshot to restore to.
        target_snapshot_keys = await client.zrevrangebyscore(
            snapshots_zset_key,
            max=tick,
            min="-inf",
            start=0,
            num=1,
        )

        if not target_snapshot_keys:
            logger.warning("No snapshot found at or before tick %d", tick)
            return False

        snapshot_to_restore_key = target_snapshot_keys[0]
        logger.info("Restoring from snapshot: %s", snapshot_to_restore_key)

        # 3. Clear the current KV state.
        keys_to_delete = [key async for key in client.scan_iter() if not self._is_reserved_key(key)]
        if keys_to_delete:
            await client.delete(*keys_to_delete)

        # 4. Restore data from the target snapshot Hash.
        snapshot_data = await client.hgetall(snapshot_to_restore_key)
        if not snapshot_data:
            logger.info("Snapshot %s was empty. State cleared.", snapshot_to_restore_key)
            return True

        restoration_data = {key.decode("utf-8"): json.loads(value) for key, value in snapshot_data.items()}

        await self.import_data(restoration_data)

        return True

    async def clear(self) -> bool:
        """
        Safely clears all KV-related keys from the current database.

        This method will not affect data managed by other adapters (e.g.,
        graph adapter) or any historical snapshots.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        if not self._client:
            return False
        try:
            keys_to_delete = [
                key
                async for key in self._client.scan_iter()
                if not (
                    key.startswith("history:") or key.startswith("node:") or key.startswith("edge:") or key == "nodes"
                )
            ]

            if keys_to_delete:
                await self._client.delete(*keys_to_delete)

            return True
        except Exception as e:
            logger.error(f"Error while clearing KV data: {e}")
            return False

    async def incr(self, key: str, amount: int = 1, field: Optional[str] = None) -> int:
        """
        Atomically increment the integer value of a Redis key or hash field.

        If the key does not exist, it will be initialized to 0 before
        performing the increment. This operation is atomic and suitable for
        distributed counter scenarios (e.g., ID generators).

        Args:
            key: Redis key name
            amount: The amount to increment (default is 1). Can be negative
                for decrement.
            field: (Optional) If provided, increment the specified field in a
                hash instead of a string key.

        Returns:
            int: The new value after increment

        Raises:
            ValueError: If the key stores a value that is not an integer
            ConnectionError: If Redis is not connected
        """
        if not self._client:
            raise ConnectionError("Redis client not connected")

        if field is not None:
            return await self._client.hincrby(key, field, amount)
        else:
            if amount == 1:
                return await self._client.incr(key)
            else:
                return await self._client.incrby(key, amount)

    async def publish_event(self, channel: str, message: Dict[str, Any]):
        """
        Publishes an event to the specified channel.

        Args:
            channel (str): The channel to publish to.
            message (Dict[str, Any]): The message to publish (will be
                JSON-serialized).

        Raises:
            ConnectionError: If the adapter is not connected to Redis.
        """
        if not self._connected or not self._client:
            raise ConnectionError("Adapter is not connected to Redis.")

        await self._client.publish(channel, self._serialize(message))

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

    def _detect_type(self, value: Any) -> str:
        """
        Detect the most appropriate Redis type for a given Python value.

        Args:
            value (Any): The value to inspect.

        Returns:
            str: The detected type ('hash', 'list', or 'string').
        """
        if isinstance(value, dict):
            return "hash"
        if isinstance(value, list):
            return "list"
        return "string"

    def _serialize(self, value: Any) -> str:
        """
        Serialize a Python object to a string for Redis storage.

        Args:
            value (Any): The value to serialize.

        Returns:
            str: The serialized string.
        """
        if isinstance(value, (str, bytes)):
            return value
        return json.dumps(value)

    def _deserialize(self, value: Optional[str]) -> Any:
        """
        Deserialize a string from Redis back into a Python object.

        Args:
            value (Optional[str]): The string to deserialize.

        Returns:
            Any: The deserialized Python object.
        """
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def _is_reserved_key(self, key: str) -> bool:
        """
        Check if a key is reserved for internal use.

        Args:
            key (str): The key to check.

        Returns:
            bool: True if the key is reserved, False otherwise.
        """
        if isinstance(key, bytes):
            key = key.decode("utf-8")
        return key.startswith("history:kv:")

    async def _hset_field_by_field(self, client: aioredis.StrictRedis, key: str, data: Dict[str, Any]) -> None:
        """
        Set hash fields one by one to avoid blocking the server with HMSET.

        Args:
            client (aioredis.StrictRedis): The Redis client.
            key (str): The hash key.
            data (Dict[str, Any]): The field-value data to set.
        """
        for field, field_value in data.items():
            await client.hset(key, field, field_value)
