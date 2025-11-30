"""Configurations for system modules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from ...types.schemas.message import MessageKind


class MessagerConfig(BaseModel):
    """Configuration for the message bus, defining rules for message flow.

    Attributes:
        allow_self_messages (bool): Whether agents can send messages to themselves.
        allow_kinds (List[MessageKind]): List of allowed message kinds.
        block_empty_content (bool): Whether to block messages with empty content.
        max_content_length (Optional[int]): Maximum allowed length for message content.
        blocked_pairs (List[Tuple[str, str]]): List of (sender, receiver) pairs to block.
        blocked_senders (List[str]): List of sender IDs to block.
        blocked_receivers (List[str]): List of receiver IDs to block.
        blocked_keywords (List[str]): List of keywords; messages containing these will be blocked.
        blocked_regex (List[str]): List of regex patterns; messages matching these will be blocked.
    """

    allow_self_messages: bool = True
    allow_kinds: List[MessageKind] = Field(default_factory=lambda: list(MessageKind))
    block_empty_content: bool = True
    max_content_length: Optional[int] = None
    blocked_pairs: List[Tuple[str, str]] = Field(default_factory=list)
    blocked_senders: List[str] = Field(default_factory=list)
    blocked_receivers: List[str] = Field(default_factory=list)
    blocked_keywords: List[str] = Field(default_factory=list)
    blocked_regex: List[str] = Field(default_factory=list)


class TimerConfig(BaseModel):
    """Configuration for the simulation timer.

    Attributes:
        start_tick (int): The tick at which the simulation starts.
        timeout_ticks (int): The maximum number of ticks before timeout.
    """

    start_tick: int = 0
    timeout_ticks: int


class RecorderConfig(BaseModel):
    """Configuration for the data recorder, typically a database.

    Attributes:
        dbname (str): The name of the database.
        user (str): The username for database access.
        password (str): The password for database access.
        host (str): The database host address.
        port (int): The port number for database access.
    """

    dbname: str
    user: str
    password: str
    host: str
    port: int


class SystemConfig(BaseModel):
    """Top-level configuration for the entire system module."""

    name: str = Field(..., description="The name of the system module.", min_length=1)
    components: Dict[str, Dict[str, Any]] = Field(
        ..., description="A dictionary of all system components and their " "configurations."
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate that the system name is not empty.

        Args:
            v (str): The system name.

        Returns:
            str: The validated system name.

        Raises:
            ValueError: If the name is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("System name cannot be empty.")
        return v
