"""Model router hook system for extensible event handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, TYPE_CHECKING, Union

from .api.provider import TokenUsage

if TYPE_CHECKING:
    from .router import ModelRouter


@dataclass
class ChatCompleteEvent:
    """Event data passed to post_chat hooks after a successful chat request.
    
    Attributes:
        response: The processed response content (after removing think tags).
        raw_response: The original response from the LLM before processing.
        token_usage: Token usage information if available.
        user_prompt: The original user prompt.
        system_prompt: The system prompt used.
        model_name: The model name used for the request.
        metadata: Additional custom metadata.
    """
    response: Optional[Union[str, List[str]]] = None
    raw_response: Optional[List[str]] = None
    token_usage: Optional[TokenUsage] = None
    user_prompt: str = ""
    system_prompt: str = ""
    model_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatErrorEvent:
    """Event data passed to error hooks when a chat request fails.
    
    Attributes:
        error: The exception that occurred.
        user_prompt: The original user prompt.
        system_prompt: The system prompt used.
        model_name: The model name used for the request.
    """
    error: Exception
    user_prompt: str = ""
    system_prompt: str = ""
    model_name: Optional[str] = None


HookCallback = Callable[[Any], Awaitable[None]]
UserHookFunc = Callable[[Any, Any], Awaitable[None]]


def model_hook(event_type: str):
    """
    Decorator to define a model router hook.
    
    The decorated function receives (event, system) where:
    - event: The hook event (ChatCompleteEvent or ChatErrorEvent)
    - system: The System handle for accessing timer, recorder, etc.
    
    Args:
        event_type: The hook event type ("post_chat" or "on_error").
    
    Usage:
        @model_hook("post_chat")
        async def record_tokens(event: ChatCompleteEvent, system):
            if event.token_usage:
                tick = await system.run("timer", "get_tick")
                await system.run("recorder", "record_event", ...)
        
        # Register directly in RESOURCE_MAPS
        RESOURCE_MAPS = {
            "model_hooks": record_tokens,           # Single hook
            # or
            "model_hooks": [hook1, hook2, hook3],   # Multiple hooks
        }
    
    Event types and their event classes:
        - "post_chat": ChatCompleteEvent
        - "on_error": ChatErrorEvent
    """
    valid_types = ["post_chat", "on_error"]
    if event_type not in valid_types:
        raise ValueError(f"Invalid event_type: {event_type}. Must be one of {valid_types}")
    
    def decorator(func: UserHookFunc) -> UserHookFunc:
        func._model_hook_event_type = event_type
        return func
    return decorator


def register_model_hooks(
    model_router: "ModelRouter",
    hooks: Any,
    system_handle: Any
) -> int:
    """
    Register model hooks from various formats.
    
    This is an internal helper called by MasPod during initialization.
    
    Args:
        model_router: The ModelRouter instance.
        hooks: A single hook function, list of hooks, or None.
        system_handle: The System handle.
        
    Returns:
        int: Number of hooks registered.
        
    Raises:
        ValueError: If a function is not decorated with @model_hook.
    """
    if hooks is None:
        return 0
    
    if not isinstance(hooks, (list, tuple)):
        hooks = [hooks]
    
    count = 0
    for func in hooks:
        if not hasattr(func, '_model_hook_event_type'):
            raise ValueError(
                f"Function '{func.__name__}' is not decorated with @model_hook. "
                "Use @model_hook('post_chat') or @model_hook('on_error')."
            )
        
        event_type = func._model_hook_event_type
        
        def create_wrapper(f: UserHookFunc, sys: Any) -> HookCallback:
            async def wrapper(event: Any) -> None:
                await f(event, sys)
            return wrapper
        
        wrapper = create_wrapper(func, system_handle)
        model_router.register_hook(event_type, wrapper)
        count += 1
    
    return count

