"""Helpers for creating and managing database connection pools."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from ...types.configs import DatabaseConfig
from ..logger import get_logger


logger = get_logger(__name__)


async def create_connection_pools(db_config: DatabaseConfig) -> Dict[str, Dict[str, Any]]:
    """
    Instantiate connection pools as described by the database configuration.

    Args:
        db_config (DatabaseConfig): Pydantic configuration model describing pools and adapters.

    Returns:
        Dict[str, Dict[str, Any]]:
            Mapping of pool names to a dictionary containing the
            'instance' (the pool object) and its 'type' (e.g., 'redis').
    """
    created_pools: Dict[str, Dict[str, Any]] = {}
    if not db_config or not db_config.pools:
        logger.warning("Database config is empty or contains no pools. Returning empty dict.")
        return created_pools

    for pool_name, pool_config in db_config.pools.items():
        logger.info("Creating connection pool '%s' for db type '%s'...", pool_name, pool_config.type)
        pool_instance: Any = None
        try:
            if pool_config.type == "redis":
                try:
                    import redis.asyncio as aioredis
                except ImportError as e:
                    logger.error("aioredis is not installed. Please install it to use Redis connection pools.")
                    raise e

                full_redis_config = {**pool_config.settings, **pool_config.pool_settings}
                pool_instance = aioredis.ConnectionPool(**full_redis_config)
                logger.info("Redis pool '%s' created successfully.", pool_name)

            elif pool_config.type == "postgres":
                try:
                    import asyncpg
                except ImportError as e:
                    logger.error("asyncpg is not installed. Please install it to use PostgreSQL connection pools.")
                    raise e

                full_pg_config = {**pool_config.settings, **pool_config.pool_settings}
                pool_instance = await asyncpg.create_pool(**full_pg_config)
                logger.info("PostgreSQL pool '%s' created successfully.", pool_name)

            else:
                logger.warning("Unsupported database type '%s' for pool '%s'. Skipping.", pool_config.type, pool_name)

            if pool_instance:
                created_pools[pool_name] = {
                    "instance": pool_instance,
                    "type": pool_config.type,
                }
        except Exception as exc:
            logger.error("Failed to create connection pool '%s': %s", pool_name, exc, exc_info=True)

    return created_pools


async def close_connection_pools(pools: Dict[str, Dict[str, Any]]) -> None:
    """
    Close every pool instance in the provided mapping.

    Args:
        pools (Dict[str, Dict[str, Any]]): Mapping returned by `create_connection_pools`.
    """
    logger.info("Closing all database connection pools...")
    if not pools:
        logger.info("No connection pools to close.")
        return

    closing_tasks = []
    for pool_name, pool_info in pools.items():
        task = close_single_pool(
            pool_name=pool_name,
            pool_type=pool_info["type"],  # <-- Pass the type string
            pool_instance=pool_info["instance"],
        )
        closing_tasks.append(task)

    await asyncio.gather(*closing_tasks)
    logger.info("All database connection pools have been closed.")


async def close_single_pool(pool_name: str, pool_type: str, pool_instance: Any) -> None:
    """
    Close a single connection pool instance.

    Args:
        pool_name (str): Friendly name of the pool used for logging.
        pool_type (str): Type of the database (e.g., 'redis', 'postgres').
        pool_instance (Any): Connection pool object created by `create_connection_pools`.
    """
    try:
        logger.info("Closing connection pool '%s'...", pool_name)
        if pool_type == "redis":
            await pool_instance.disconnect()
        elif pool_type == "postgres":
            await pool_instance.close()
        else:
            logger.warning("Unknown pool type for '%s'. Cannot determine how to close it.", pool_name)
            return
        logger.info("Connection pool '%s' closed successfully.", pool_name)
    except Exception as exc:
        logger.error("Error while closing connection pool '%s': %s", pool_name, exc, exc_info=True)
