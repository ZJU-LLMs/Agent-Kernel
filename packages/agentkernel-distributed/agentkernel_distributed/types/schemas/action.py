"""Standardised action result schema for the MAS runtime."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class CallStatus(str, Enum):
    """Enumeration describing whether an action succeeded or failed.

    Attributes:
        SUCCESS (str): Indicates the action completed successfully.
        ERROR (str): Indicates the action encountered an error.
    """

    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ActionResult:
    """Structured payload returned by action components.

    Attributes:
        method_name (str): Name of the invoked method.
        message (str): Human-readable description of the outcome.
        status (CallStatus): Status of the action (success or error).
        data (Optional[Any]): Optional payload returned by the action.
        extra (Dict[str, Any]): Optional metadata dictionary.
    """

    method_name: str
    message: str
    status: CallStatus = CallStatus.SUCCESS
    data: Optional[Any] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def is_successful(self) -> bool:
        """
        Determine whether the action completed successfully.

        Returns:
            bool: True when the action status is ``CallStatus.SUCCESS``.
        """
        return self.status == CallStatus.SUCCESS

    def is_error(self) -> bool:
        """
        Determine whether the action failed.

        Returns:
            bool: True when the action status is ``CallStatus.ERROR``.
        """
        return self.status == CallStatus.ERROR

    @classmethod
    def success(
        cls,
        method_name: str,
        message: str,
        data: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "ActionResult":
        """
        Create a success result.

        Args:
            method_name (str): Name of the invoked method.
            message (str): Human-readable description of the outcome.
            data (Optional[Any]): Optional payload returned by the action.
            extra (Optional[Dict[str, Any]]): Optional metadata dictionary.

        Returns:
            ActionResult: Result instance representing success.
        """
        return cls(
            status=CallStatus.SUCCESS,
            method_name=method_name,
            message=message,
            data=data,
            extra=extra or {},
        )

    @classmethod
    def error(
        cls,
        method_name: str,
        message: str,
        data: Optional[Any] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "ActionResult":
        """
        Create an error result.

        Args:
            method_name (str): Name of the invoked method.
            message (str): Error description.
            data (Optional[Any]): Optional payload returned by the action.
            extra (Optional[Dict[str, Any]]): Optional metadata dictionary.

        Returns:
            ActionResult: Result instance representing an error.
        """
        return cls(
            status=CallStatus.ERROR,
            method_name=method_name,
            message=message,
            data=data,
            extra=extra or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a dictionary suitable for JSON serialisation.

        Returns:
            Dict[str, Any]: Dataclass fields serialised as a dictionary.
        """
        return asdict(self)
