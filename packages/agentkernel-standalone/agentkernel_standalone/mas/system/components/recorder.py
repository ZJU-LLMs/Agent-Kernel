"""Recorder actor that persists simulation data to PostgreSQL and JSON files.

This is a generic framework component that can be used across different
simulation scenarios. Application-specific event types should be defined
in the application's own modules (e.g., utils/event_types.py).
"""

import json
import os
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import asyncpg
from asyncpg.pool import Pool
from ....toolkit.logger import get_logger
from ....types.configs.system import RecorderConfig
from .base import SystemComponent

logger = get_logger(__name__)

__all__ = ["Recorder", "TrajectoryEvent"]


@dataclass
class TrajectoryEvent:
    """Represents a single event in the simulation trajectory.
    
    This standardized format allows external evaluators to analyze
    the simulation without accessing internal state.
    
    Format:
    {
        "tick": int,                    # Required: simulation tick
        "event_type": str,              # Required: event type string
        "agent_id": str | None,         # Optional: primary agent ID
        "target_id": str | None,        # Optional: secondary agent ID
        "payload": dict                 # Required: event-specific data
    }
    
    Attributes:
        tick: The simulation tick when this event occurred
        event_type: Category of the event (string, application-defined)
        payload: Event-specific data dictionary
        agent_id: Optional primary agent involved in this event
        target_id: Optional secondary agent (e.g., message recipient)
        timestamp: Optional real-world timestamp for performance analysis
    """
    tick: int
    event_type: str
    payload: Dict[str, Any]
    agent_id: Optional[str] = None
    target_id: Optional[str] = None
    timestamp: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Only includes agent_id and target_id if they are set (not None/empty).
        
        Returns:
            Dict[str, Any]: Dictionary representation of the event.
        """
        result = {
            "tick": self.tick,
            "event_type": self.event_type,
        }
        if self.agent_id:
            result["agent_id"] = self.agent_id
        if self.target_id:
            result["target_id"] = self.target_id
        result["payload"] = self.payload
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectoryEvent":
        """Create an event from a dictionary."""
        return cls(
            tick=data.get("tick", 0),
            event_type=data.get("event_type", "CUSTOM"),
            payload=data.get("payload", {}),
            agent_id=data.get("agent_id"),
            target_id=data.get("target_id"),
            timestamp=data.get("timestamp")
        )


class Recorder(SystemComponent):
    """Persist simulation events for analysis and evaluation.
    
    This enhanced Recorder supports:
    1. PostgreSQL database storage (original functionality)
    2. Standardized trajectory JSON files for benchmark evaluation
    3. Real-time event buffering and periodic flushing
    4. LLM usage tracking for computational cost analysis
    
    The trajectory format follows the benchmark specification,
    enabling external evaluators to calculate metrics without
    accessing simulation internals.
    """

    def __init__(self, **kwargs: str) -> None:
        """
        Initialize the recorder with the provided configuration.

        Args:
            **kwargs (str): Fields used to construct a `RecorderConfig`.
                Additional fields:
                - trajectory_dir: Directory for trajectory JSON files
                - buffer_size: Number of events to buffer before flushing
                - enable_db: Whether to enable database recording
        """
        super().__init__(**kwargs)
        
        self.trajectory_dir = kwargs.pop("trajectory_dir", None)
        self.buffer_size = int(kwargs.pop("buffer_size", 100))
        self.enable_db = kwargs.pop("enable_db", True)
        
        if self.enable_db and all(k in kwargs for k in ["dbname", "user", "password", "host", "port"]):
            self.config = RecorderConfig(**kwargs)
            self.db_config: Dict[str, Any] = {
                "database": self.config.dbname,
                "user": self.config.user,
                "password": self.config.password,
                "host": self.config.host,
                "port": self.config.port,
            }
        else:
            self.config = None
            self.db_config = {}
            self.enable_db = False
        
        self.pool: Optional[Pool] = None
        
        self._trajectory_events: List[TrajectoryEvent] = []
        self._trajectory_metadata: Dict[str, Any] = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "framework": "AgentKernel",
        }
        self._event_buffer: List[TrajectoryEvent] = []
        
        self._total_llm_calls: int = 0
        self._prompt_tokens: int = 0
        
        if self.trajectory_dir is None:
            self.trajectory_dir = os.environ.get("MAS_EVENT_LOG_DIR", ".")
        
        self._trajectory_file = os.path.join(
            self.trajectory_dir, 
            f"trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        logger.info(
            "Recorder initialized. DB enabled: %s, Trajectory file: %s",
            self.enable_db,
            self._trajectory_file
        )

    async def post_init(self, *args, **kwargs) -> None:
        """Establish the database connection pool after actor creation."""
        if self.enable_db:
            await self.connect()

    async def connect(self) -> None:
        """Create a connection pool and ensure the schema exists."""
        if not self.enable_db:
            logger.info("Database recording is disabled.")
            return
            
        if self.pool:
            logger.warning("Recorder is already connected to the database.")
            return

        logger.info(
            "Connecting to PostgreSQL at %s:%s...",
            self.db_config.get("host"),
            self.db_config.get("port"),
        )

        try:
            self.pool = await asyncpg.create_pool(**self.db_config, timeout=10)
            await self._initialize_schema()
            logger.info("Recorder connected to PostgreSQL and initialized schema.")
        except Exception as exc:
            logger.error("Recorder failed to connect to PostgreSQL.")
            logger.exception(exc)
            self.pool = None
            self.enable_db = False

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
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trajectory_events (
                    id SERIAL PRIMARY KEY,
                    tick INT NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    agent_id VARCHAR(255),
                    target_id VARCHAR(255),
                    payload JSONB,
                    timestamp DOUBLE PRECISION,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """
            )
            logger.info("Database schema checked/created.")

    async def record(self, table: str, data: Dict[str, Any]) -> None:
        """
        Insert a row into the specified table.

        Args:
            table (str): Target table name.
            data (Dict[str,Any]): Column values keyed by column name.
        """
        if not self.enable_db or not self.pool:
            logger.debug("Database recording skipped (disabled or not connected).")
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

    async def record_event(
        self,
        tick: int,
        event_type: str,
        payload: Dict[str, Any],
        agent_id: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> None:
        """
        Record a standardized trajectory event.
        
        This is the primary method for logging events in the benchmark-compatible
        format. Events are buffered and periodically flushed to both the
        trajectory file and optionally to the database.
        
        Event format:
        {
            "tick": int,                    # Required
            "event_type": str,              # Required
            "agent_id": str,                # Optional, only included if set
            "target_id": str,               # Optional, only included if set
            "payload": dict                 # Required
        }
        
        Args:
            tick: Current simulation tick
            event_type: Type of event (application-defined string)
            payload: Event-specific data dictionary
            agent_id: Optional primary agent ID
            target_id: Optional secondary agent ID
        """
        logger.debug(
            f"Recording event: tick={tick}, event_type={event_type}, agent_id={agent_id}, "
            f"target_id={target_id}, buffer_size={len(self._event_buffer)}/{self.buffer_size}"
        )
        
        event = TrajectoryEvent(
            tick=tick,
            event_type=event_type,
            payload=payload,
            agent_id=agent_id,
            target_id=target_id,
            timestamp=time.time()
        )
        
        self._event_buffer.append(event)
        logger.debug(f"Event added to buffer. New buffer size: {len(self._event_buffer)}/{self.buffer_size}")
        
        if len(self._event_buffer) >= self.buffer_size:
            logger.info(f"Buffer full ({len(self._event_buffer)} >= {self.buffer_size}), flushing...")
            await self._flush_buffer()
    
    async def record_llm_usage(
        self,
        tick: int,
        prompt_tokens: int
    ) -> None:
        """
        Record LLM inference usage for computational cost tracking.
        
        This is a convenience method that records only the input token count.
        
        Args:
            tick: Current simulation tick
            prompt_tokens: Number of input (prompt) tokens
        """
        self._total_llm_calls += 1
        self._prompt_tokens += prompt_tokens
        
        await self.record_event(
            tick=tick,
            event_type="LLM_INFERENCE",
            payload={
                "prompt_tokens": prompt_tokens
            }
        )
    
    async def record_system_config(
        self,
        tick: int,
        config: Dict[str, Any]
    ) -> None:
        """
        Record system configuration for the evaluation.
        
        This should be called at the start of simulation to record
        metadata needed for evaluation.
        
        Args:
            tick: Current simulation tick (usually 0)
            config: System configuration dictionary
        """
        self._trajectory_metadata.update(config)
        
        await self.record_event(
            tick=tick,
            event_type="SYSTEM_CONFIG",
            payload=config
        )
    
    async def _flush_buffer(self) -> None:
        """Flush buffered events to storage."""
        if not self._event_buffer:
            logger.debug("Buffer is empty, nothing to flush.")
            return
        
        num_events = len(self._event_buffer)
        logger.info(f"Flushing {num_events} events to trajectory...")
        
        # Add to trajectory
        self._trajectory_events.extend(self._event_buffer)
        
        # Write to database if enabled
        if self.enable_db and self.pool:
            for event in self._event_buffer:
                try:
                    await self.record(
                        "trajectory_events",
                        {
                            "tick": event.tick,
                            "event_type": event.event_type,
                            "agent_id": event.agent_id,
                            "target_id": event.target_id,
                            "payload": json.dumps(event.payload),
                            "timestamp": event.timestamp
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to record event to database: {e}")
        
        self._event_buffer.clear()
        logger.debug(f"Successfully flushed {num_events} events to trajectory.")
    
    async def save_trajectory(self, path: Optional[str] = None) -> str:
        """
        Save the complete trajectory to a JSON file.
        
        Args:
            path: Optional custom path (uses default if not provided)
            
        Returns:
            Path to the saved trajectory file
        """
        # Flush any remaining buffered events
        await self._flush_buffer()
        
        file_path = path or self._trajectory_file
        
        trajectory = {
            "metadata": {
                **self._trajectory_metadata,
                "saved_at": datetime.now().isoformat(),
                "total_events": len(self._trajectory_events),
                "llm_usage": {
                    "total_calls": self._total_llm_calls,
                    "prompt_tokens": self._prompt_tokens
                }
            },
            "events": [e.to_dict() for e in self._trajectory_events]
        }
        
        try:
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(trajectory, f, ensure_ascii=False, indent=2)
            logger.info("Trajectory saved to: %s", file_path)
        except Exception as e:
            logger.error("Failed to save trajectory: %s", e)
        
        return file_path
    
    async def get_trajectory_events(self) -> List[Dict[str, Any]]:
        """
        Get all trajectory events as dictionaries.
        
        Returns:
            List of event dictionaries
        """
        await self._flush_buffer()
        return [e.to_dict() for e in self._trajectory_events]
    
    async def get_llm_usage_summary(self) -> Dict[str, Any]:
        """
        Get LLM usage summary for cost analysis.
        
        Returns:
            Dictionary with prompt token counts and call statistics
        """
        return {
            "total_calls": self._total_llm_calls,
            "prompt_tokens": self._prompt_tokens,
            "avg_prompt_tokens_per_call": (
                self._prompt_tokens / self._total_llm_calls 
                if self._total_llm_calls > 0 else 0
            )
        }
    
    async def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata field for the trajectory.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self._trajectory_metadata[key] = value

    async def close(self, *args, **kwargs) -> None:
        """Close the database connection pool and save trajectory."""
        # Save trajectory before closing
        try:
            await self.save_trajectory()
        except Exception as e:
            logger.error("Failed to save trajectory on close: %s", e)
        
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Recorder database connection pool closed.")
