"""Recorder actor that persists simulation data to PostgreSQL."""

from typing import Any, Dict, Optional

import asyncpg
from asyncpg.pool import Pool
from ....toolkit.logger import get_logger
from ....types.configs.system import RecorderConfig
from .base import SystemComponent

logger = get_logger(__name__)

__all__ = ["Recorder"]


class Recorder(SystemComponent):
    """Persist simulation events such as ticks, actions, and messages."""

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize the recorder with the provided configuration.

        Args:
            **kwargs (object): Fields used to construct a `RecorderConfig`.
        """
        super().__init__(**kwargs)
        self.config = RecorderConfig(**kwargs)

        self.db_config: Dict[str, Any] = {
            "database": self.config.dbname,
            "user": self.config.user,
            "password": self.config.password,
            "host": self.config.host,
            "port": self.config.port,
        }
        self.pool: Optional[Pool] = None
        logger.info(
            "Recorder created for db '%s' at %s:%s",
            self.config.dbname,
            self.config.host,
            self.config.port,
        )

    async def post_init(self, *args, **kwargs) -> None:
        """Establish the database connection pool after actor creation."""
        await self.connect()

    async def connect(self) -> None:
        """Create a connection pool and ensure the schema exists."""
        if self.pool:
            logger.warning("Recorder is already connected to the database.")
            return

        logger.info(
            "Connecting to PostgreSQL at %s:%s...",
            self.db_config["host"],
            self.db_config["port"],
        )

        try:
            self.pool = await asyncpg.create_pool(**self.db_config, timeout=10)
            await self._initialize_schema()
            logger.info("Recorder connected to PostgreSQL and initialized schema.")
        except Exception as exc:
            logger.error("Recorder failed to connect to PostgreSQL.")
            logger.exception(exc)
            self.pool = None
            raise

    async def _initialize_schema(self) -> None:
        """Create required tables if they do not already exist."""
        if self.pool is None:
            raise RuntimeError("Database connection pool has not been initialized.")

        async with self.pool.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS simulation_ticks (
                    id SERIAL PRIMARY KEY,
                    tick_number INT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL
                );
            """
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_actions (
                    id SERIAL PRIMARY KEY,
                    tick INT NOT NULL,
                    agent_id VARCHAR(255) NOT NULL,
                    action_name VARCHAR(255),
                    parameters JSONB,
                    status VARCHAR(50),
                    result TEXT,
                    ticks_consumed INT
                );
            """
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    tick INT NOT NULL,
                    from_id VARCHAR(255) NOT NULL,
                    to_id VARCHAR(255) NOT NULL,
                    content TEXT,
                    kind VARCHAR(100),
                    created_at TIMESTAMPTZ
                );
            """
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_states (
                    id SERIAL PRIMARY KEY,
                    tick INT NOT NULL,
                    agent_id VARCHAR(255) NOT NULL,
                    state_key VARCHAR(255) NOT NULL,
                    state_value TEXT
                );
            """
            )
            logger.info("Database schema checked/created.")

    async def record(self, table: str, data: Dict[str, Any]) -> None:
        """
        Insert a row into the specified table.

        Args:
            table (str): Target table name.
            data (Dict[str, Any]): Column values keyed by column name.
        """
        if not self.pool:
            logger.error("Cannot record data, database connection is not available.")
            return

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"${i+1}" for i in range(len(data)))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        try:
            async with self.pool.acquire() as connection:
                await connection.execute(sql, *data.values())
        except Exception as exc:
            logger.error("Failed to record data into table '%s': %s", table, exc)
            logger.error("SQL: %s", sql)
            logger.error("Data: %s", data)

    async def close(self, *args, **kwargs) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Recorder database connection pool closed.")
