"""Schema definitions for events emitted through the MAS interface."""

import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """High-level categories for published events.

    Attributes:
        SIMULATION: Events related to the overall simulation.
        AGENT: Events related to individual agents.
        ENVIRONMENT: Events related to the environment or world.
    """

    SIMULATION = "simulation"
    AGENT = "agent"
    ENVIRONMENT = "environment"


class AgentEvent(str, Enum):
    """Canonical event names related to agents.

    Attributes:
        MOVED: Event indicating an agent has moved.
        STATE_CHANGED: Event indicating an agent's state has changed.
        DIALOGUE_SENT: Event indicating a dialogue message has been sent between agents.
    """

    MOVED = "agent_moved"
    STATE_CHANGED = "state_changed"
    DIALOGUE_SENT = "dialogue_sent"


class AgentStatePayload(BaseModel):
    """Payload published when an agent changes its state.

    Attributes:
        agent_id: The unique identifier of the agent.
        status_text: A textual description of the agent's current status.
        status_emoji: An emoji representing the agent's current status.
    """

    agent_id: str
    status_text: str
    status_emoji: str


class AgentMovePayload(BaseModel):
    """Payload describing an agent movement.

    Attributes:
        agent_id: The unique identifier of the agent.
        destination_id: The unique identifier of the destination location.
        position: The new position of the agent as a list of coordinates.
    """

    agent_id: str
    destination_id: str
    position: List[float]


class AgentDialoguePayload(BaseModel):
    """Payload representing a dialogue message between agents.

    Attributes:
        from_id: The unique identifier of the sending agent.
        to_id: The unique identifier of the receiving agent.
        content: The content of the dialogue message.
    """

    from_id: str
    to_id: str
    content: str


class SimulationEvent(BaseModel):
    """Envelope describing an event emitted by the simulation.

    Attributes:
        category: The high-level category of the event.
        name: The specific name of the event.
        payload: The data associated with the event.
        timestamp: The UTC timestamp when the event was created.
        tick: The simulation tick at which the event occurred.
    """

    category: EventCategory
    name: str
    payload: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    tick: int
