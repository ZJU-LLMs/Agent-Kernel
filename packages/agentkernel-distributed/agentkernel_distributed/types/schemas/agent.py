"""Schemas describing agent perception and action state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .action import ActionResult, CallStatus


@dataclass
class PerceptionData:
    """Structured representation of perceptual inputs available to an agent.

    Attributes:
        new_messages (List[Dict[str, Any]]): Newly received messages for the agent.
        chat_history (Dict[str, List[Dict[str, Any]]]): Historical chat messages organized by conversation ID.
        relations (List[Dict[str, Any]]): Information about relationships with other agents or entities.
        surroundings (List[Dict[str, Any]]): Data about the agent's immediate environment.
        extra (Dict[str, Any]): Additional arbitrary perceptual data.
    """

    new_messages: List[Dict[str, Any]] = field(default_factory=list)
    chat_history: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    surroundings: List[Dict[str, Any]] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the perception data to a dictionary.

        Returns:
            Dict[str, Any]: Dataclass fields serialised as a dictionary.
        """
        return asdict(self)


class ActionOutcome(str, Enum):
    """Enumerate the terminal outcome of an action.

    Attributes:
        INTERRUPTED (str): The action was interrupted before completion.
        COMPLETED (str): The action was completed successfully.
        FAILED (str): The action failed to complete successfully.
    """

    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ActionRecord:
    """Historical record describing a completed, failed, or interrupted action.

    Attributes:
        description (str): A textual description of the action performed.
        duration_ticks (int): The duration of the action in ticks.
        outcome (ActionOutcome): The terminal outcome of the action.
        result (ActionResult): The result of the action execution.
        extra (Dict[str, Any]): Additional arbitrary data related to the action.
    """

    description: str
    duration_ticks: int
    outcome: ActionOutcome
    result: ActionResult
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the action record to a dictionary.

        Returns:
            Dict[str, Any]: Dataclass fields serialised as a dictionary.
        """
        return asdict(self)


@dataclass
class CurrentAction:
    """State snapshot for an action that is still in progress.

    Attributes:
        description (str): A textual description of the action being performed.
        total_ticks (int): The total number of ticks allocated for the action.
        remaining_ticks (int): The number of ticks remaining for the action.
        result (ActionResult): The current result status of the action.
        extra (Dict[str, Any]): Additional arbitrary data related to the action.
    """

    description: str
    total_ticks: int
    remaining_ticks: int
    result: ActionResult = field(
        default_factory=lambda: ActionResult(
            method_name="unknown",
            message="Action is in progress.",
            status=CallStatus.SUCCESS,
        )
    )
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the current action to a dictionary.

        Returns:
            Dict[str, Any]: Dataclass fields serialised as a dictionary.
        """
        return asdict(self)
