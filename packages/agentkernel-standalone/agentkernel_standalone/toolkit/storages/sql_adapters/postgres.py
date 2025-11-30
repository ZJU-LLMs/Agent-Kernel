"""PostgreSQL asynchronous adapter implementation."""

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

import asyncpg

from ...logger import get_logger
from .base import BaseSQLAdapter

logger = get_logger(__name__)


class PostgresAdapter(BaseSQLAdapter):
    """Asynchronous database adapter for PostgreSQL.

    This class implements the common relational database interface for
    interacting with a PostgreSQL database.
    """

    def __init__(self):
        """Initializes the PostgresAdapter."""
        self._pool: Optional[asyncpg.Pool] = None
        self._config: Dict[str, Any] = {}

    @property
    def pool(self) -> Optional[asyncpg.Pool]:
        """Exposes the underlying asyncpg.Pool object for advanced operations.

        Returns:
            An asyncpg connection pool instance, allowing users to acquire a
            connection for executing arbitrary database commands.

        Example:
            pg_adapter = PostgresAdapter()
            # ... connect the adapter ...
            async with pg_adapter.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "INSERT INTO users VALUES ($1, $2)", 'bob', 'smith'
                    )
        """
        return self._pool

    async def connect(self, config: Dict[str, Any], pool: Optional[asyncpg.Pool] = None):
        """Connects to the database pool and initializes the schema.

        Args:
            config: Configuration dictionary for the adapter.
            pool: An existing asyncpg connection pool.

        Raises:
            ValueError: If the connection pool is not provided.
        """
        if not pool:
            raise ValueError("PostgresAdapter requires an asyncpg connection pool.")
        self._pool = pool
        self._config = config
        await self._initialize_schema_from_config()
        logger.info("PostgresAdapter connected to the pool and initialized the schema.")

    async def disconnect(self):
        """Disconnects from the database.

        For adapters using a shared pool, this is a no-op as the pool is
        managed externally.
        """
        pass

    async def is_connected(self) -> bool:
        """Checks if the adapter is connected to a pool."""
        return self._pool is not None

    async def _initialize_schema_from_config(self):
        """Creates all specified tables based on a simplified schema config."""
        schema_config = self._config.get("schema")
        if not isinstance(schema_config, dict):
            logger.warning("No 'schema' definition found in adapter config; skipping auto-creation.")
            return

        logger.info("Initializing database schema from configuration...")
        for table_name, table_info in schema_config.items():
            try:
                columns = table_info["columns"]
                await self.create_table(table_name, columns, if_not_exists=True)
                logger.info(f"Table '{table_name}' checked/created.")
            except KeyError as e:
                logger.error(f"Schema config for '{table_name}' is malformed, missing key: {e}")
            except Exception as e:
                logger.error(f"Error creating table '{table_name}': {e}")
                raise
        logger.info("Database schema initialization complete.")

    def _get_connection(self) -> asyncpg.pool.PoolAcquireContext:
        """Internal helper to get a connection and perform necessary checks."""
        if not self.is_connected() or self._pool is None:
            raise RuntimeError("Database is not connected.")
        return self._pool.acquire()

    # --- Schema Management ---

    async def table_exists(self, table_name: str) -> bool:
        """Checks if a table exists in the public schema.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        query = """
        SELECT EXISTS (
           SELECT FROM information_schema.tables
           WHERE table_schema = 'public' AND table_name = $1
        );
        """
        async with self._get_connection() as conn:
            return await conn.fetchval(query, table_name)

    async def create_table(
        self,
        table_name: str,
        columns: Dict[str, str],
        primary_key: Optional[str] = None,
        if_not_exists: bool = True,
    ):
        """Creates a new table in the database.

        Args:
            table_name (str): The name of the table to create.
            columns (Dict[str, str]): A dictionary mapping column names to their
                data types.
            primary_key (Optional[str]): The name of the primary key column.
            if_not_exists (bool): If True, adds "IF NOT EXISTS" to the SQL
                statement.
        """
        cols_defs = ", ".join(f'"{k}" {v}' for k, v in columns.items())
        pk_def = f', PRIMARY KEY ("{primary_key}")' if primary_key else ""
        exists_clause = "IF NOT EXISTS" if if_not_exists else ""
        query = f'CREATE TABLE {exists_clause} "{table_name}" ({cols_defs}{pk_def});'

        async with self._get_connection() as conn:
            await conn.execute(query)
        logger.info(f"Table '{table_name}' created successfully.")

    async def drop_table(self, table_name: str, if_exists: bool = True):
        """Drops a table from the database.

        Args:
            table_name (str): The name of the table to drop.
            if_exists (bool): If True, adds "IF EXISTS" to the SQL statement.
        """
        exists_clause = "IF EXISTS" if if_exists else ""
        query = f'DROP TABLE {exists_clause} "{table_name}";'
        async with self._get_connection() as conn:
            await conn.execute(query)
        logger.info(f"Table '{table_name}' has been dropped.")

    # --- CRUD Operations ---

    async def insert(self, table_name: str, records: Sequence[Dict[str, Any]]) -> int:
        """Inserts multiple records into a table.

        Args:
            table_name (str): The name of the table.
            records (Sequence[Dict[str, Any]]): A sequence of records to insert.

        Returns:
            int: The number of records inserted.
        """
        if not records:
            return 0

        first_record = records[0]
        columns = first_record.keys()
        cols_str = ", ".join(f'"{col}"' for col in columns)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))

        query = f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders});'

        data_to_insert = [[rec.get(col) for col in columns] for rec in records]

        async with self._get_connection() as conn:
            await conn.executemany(query, data_to_insert)
        return len(records)

    async def select(
        self,
        table_name: str,
        columns: Optional[Sequence[str]] = None,
        where: Optional[Tuple[str, Sequence[Any]]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Selects records from a table with optional filtering and pagination.

        Args:
            table_name (str): The name of the table.
            columns (Optional[Sequence[str]]): A sequence of column names to
                return. Returns all if None.
            where (Optional[Tuple[str, Sequence[Any]]]): A tuple containing the
                WHERE clause and its parameters.
            order_by (Optional[str]): The ORDER BY clause.
            limit (Optional[int]): The maximum number of records to return.
            offset (Optional[int]): The number of records to skip.

        Returns:
            List[Dict[str, Any]]: A list of records matching the query.
        """
        cols_str = ", ".join(f'"{col}"' for col in columns) if columns else "*"
        query = f'SELECT {cols_str} FROM "{table_name}"'
        params: List[Any] = []

        if where:
            where_clause, where_params = where
            query += f" WHERE {where_clause}"
            params.extend(where_params)

        if order_by:
            query += f" ORDER BY {order_by}"

        if limit is not None:
            params.append(limit)
            query += f" LIMIT ${len(params)}"

        if offset is not None:
            params.append(offset)
            query += f" OFFSET ${len(params)}"

        async with self._get_connection() as conn:
            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]

    async def update(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: Tuple[str, Sequence[Any]],
    ) -> int:
        """Updates records in a table based on a where clause.

        Args:
            table_name (str): The name of the table.
            data (Dict[str, Any]): A dictionary of columns to update.
            where (Tuple[str, Sequence[Any]]): A tuple containing the WHERE
                clause and its parameters.

        Returns:
            int: The number of records updated.
        """
        set_clause = ", ".join(f'"{col}" = ${i + 1}' for i, col in enumerate(data.keys()))
        params = list(data.values())

        where_clause, where_params = where
        adjusted_where_clause = where_clause
        start_index = len(params) + 1
        for i in range(len(where_params)):
            adjusted_where_clause = adjusted_where_clause.replace(f"${i + 1}", f"${start_index + i}")

        params.extend(where_params)

        query = f'UPDATE "{table_name}" SET {set_clause} WHERE {adjusted_where_clause};'

        async with self._get_connection() as conn:
            status = await conn.execute(query, *params)
            return int(status.split()[-1]) if status.startswith("UPDATE") else 0

    async def delete(self, table_name: str, where: Tuple[str, Sequence[Any]]) -> int:
        """Deletes records from a table based on a where clause.

        Args:
            table_name (str): The name of the table.
            where (Tuple[str, Sequence[Any]]): A tuple containing the WHERE
                clause and its parameters.

        Returns:
            int: The number of records deleted.
        """
        where_clause, params = where
        query = f'DELETE FROM "{table_name}" WHERE {where_clause};'

        async with self._get_connection() as conn:
            status = await conn.execute(query, *params)
            return int(status.split()[-1]) if status.startswith("DELETE") else 0

    async def import_data(self, data: Sequence[Dict[str, Any]]) -> None:
        """Efficiently bulk-imports data using PostgreSQL's COPY command.

        Args:
            data: A sequence of dictionaries where keys match table columns.
        """
        table_name = self._config.get("table_name")
        if not table_name:
            raise ValueError("Adapter config requires 'table_name' for import_data.")

        if not data:
            return

        first_record = data[0]
        columns = list(first_record.keys())
        records_as_tuples = [tuple(rec.get(col) for col in columns) for rec in data]

        try:
            async with self._get_connection() as conn:
                await conn.copy_records_to_table(table_name, records=records_as_tuples, columns=columns)
            logger.info(f"Successfully imported {len(data)} records into '{table_name}'.")
        except Exception as e:
            logger.error(f"Failed to bulk-import data into '{table_name}': {e}")

    async def export_data(self, order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Exports all data from the configured table.

        Args:
            order_by: An optional string to specify the sorting order
                (e.g., "timestamp DESC").

        Returns:
            A list of dictionaries containing all rows.
        """
        table_name = self._config.get("table_name")
        if not table_name:
            raise ValueError("Adapter config requires 'table_name' for export_data.")
        return await self.select(table_name, order_by=order_by)

    async def execute_raw_sql(self, query: str, *params: Any) -> str:
        """Executes a raw SQL command that does not return results (e.g., DDL).

        Args:
            query (str): The SQL query to execute.
            *params (Any): The parameters for the query.

        Returns:
            The execution status string.
        """
        async with self._get_connection() as conn:
            return await conn.execute(query, *params)

    async def fetch_raw_sql(self, query: str, *params: Any) -> List[Dict[str, Any]]:
        """Executes a raw SELECT query that returns results.

        Args:
            query (str): The SQL query to execute.
            *params (Any): The parameters for the query.

        Returns:
            A list of records.
        """
        async with self._get_connection() as conn:
            results = await conn.fetch(query, *params)
            return [dict(row) for row in results]

    async def clear(self) -> bool:
        """Clears the table. Not implemented.

        Returns:
            bool: True when data was cleared successfully.
        """
        raise NotImplementedError

    async def undo(self, timestamp: str) -> bool:
        """Restores the key-value state to a snapshot at or before the given
        timestamp.

        Args:
            timestamp (str): The ISO 8601 timestamp to restore to. This
                identifier should correspond to the one generated by `snapshot`.

        Returns:
            bool: True if the restoration was successful, False otherwise.
        """
        raise NotImplementedError
