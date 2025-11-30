"""Configuration models describing database pools and adapters."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class PoolConfig(BaseModel):
    """Settings for an individual connection pool.

    Attributes:
        type (Literal['redis', 'postgres']): The type of the database
            connection pool.
        settings (Dict[str, Any]): Connection settings for the database, such
            as host, port, and credentials.
        pool_settings (Dict[str, Any]): Settings specific to the connection
            pool, such as `min_size` and `max_size`.
    """

    type: Literal["redis", "postgres"]
    settings: Dict[str, Any] = Field(default_factory=dict)
    pool_settings: Dict[str, Any] = Field(default_factory=dict)


class AdapterConfig(BaseModel):
    """Configuration for a database adapter, optionally tied to a pool.

    Attributes:
        class_name (str): The fully qualified class name of the adapter.
        use_pool (Optional[str]): The name of the connection pool to use. If
            not specified, the adapter will manage its own connections.
        settings (Dict[str, Any]): Adapter-specific settings.
    """

    class_name: str
    use_pool: Optional[str] = None
    settings: Dict[str, Any] = Field(default_factory=dict)


class DatabaseConfig(BaseModel):
    """Top-level database configuration loaded from `db_config.yaml`.

    Attributes:
        pools (Dict[str, PoolConfig]): A dictionary mapping pool names to
            their configurations.
        adapters (Dict[str, AdapterConfig]): A dictionary mapping adapter
            names to their configurations.
    """

    pools: Dict[str, PoolConfig]
    adapters: Dict[str, AdapterConfig]
