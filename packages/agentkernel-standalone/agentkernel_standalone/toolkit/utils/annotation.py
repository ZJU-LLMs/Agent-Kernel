"""Lightweight decorators used to tag agent-callable methods."""

from typing import Any, Callable, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def AgentCall(func: F) -> F:
    """
    Mark a plugin method as callable from an agent.

    The decorated function receives an ``_annotation`` attribute that is used
    when discovering available methods.

    Args:
        func: Function to annotate.

    Returns:
        Callable: The original function with the annotation applied.
    """
    setattr(func, "_annotation", "AgentCall")
    return cast(F, func)


def ServiceCall(func: F) -> F:
    """
    Mark a plugin method as callable for external services or management.

    The decorated function receives an ``_annotation`` attribute that is used
    when discovering available methods.

    Args:
        func: Function to annotate.

    Returns:
        Callable: The original function with the annotation applied.
    """
    setattr(func, "_annotation", "ServiceCall")
    return cast(F, func)
