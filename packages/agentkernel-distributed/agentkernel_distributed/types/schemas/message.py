"""Schema definitions for messages exchanged in the MAS runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class MessageKind(str, Enum):
    """Enumerate the origin and destination classes for a message.

    Attributes:
        FROM_AGENT_TO_AGENT: Message sent from one agent to another agent.
        FROM_AGENT_TO_USER: Message sent from an agent to a user.
        FROM_USER_TO_AGENT: Message sent from a user to an agent.
    """

    FROM_AGENT_TO_AGENT = "from_agent_to_agent"
    FROM_AGENT_TO_USER = "from_agent_to_user"
    FROM_USER_TO_AGENT = "from_user_to_agent"


@dataclass
class Message:
    """Serializable structure representing a message passed within the system.

    Attributes:
        from_id (str): Identifier of the sender.
        to_id (str): Identifier of the recipient.
        kind (MessageKind): The kind of message being sent.
        content (Any): The main content of the message.
        conversation_id (Optional[str]): Identifier for the conversation thread.
        created_at (datetime): Timestamp when the message was created.
        extra (Optional[Dict[str, Any]]): Additional metadata for the message.
    """

    from_id: str
    to_id: str
    kind: MessageKind
    content: Any
    conversation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message into a dictionary suitable for serialisation.

        Returns:
            Dict[str, Any]: Dataclass fields serialised as a dictionary.
        """
        return asdict(self)
