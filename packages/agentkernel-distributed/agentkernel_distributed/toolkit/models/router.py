"""Unified client facade for local model routers."""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from ...toolkit.logger import get_logger
from .async_router import AsyncModelRouter
from .hook import (
    ChatCompleteEvent,
    ChatErrorEvent,
    HookCallback,
    model_hook,
    register_model_hooks,
)

logger = get_logger(__name__)

__all__ = [
    "ModelRouter",
    "ChatCompleteEvent",
    "ChatErrorEvent",
    "HookCallback",
    "model_hook",
    "register_model_hooks",
]


class ModelRouter:
    """Facade that unifies local model router backends.
    
    Supports a hook system for extensibility:
    - post_chat: Called after successful chat completion with ChatCompleteEvent
    - on_error: Called when an error occurs with ChatErrorEvent
    
    Example:
        async def my_hook(event: ChatCompleteEvent):
            print(f"Tokens used: {event.token_usage.prompt_tokens}")
        
        router = ModelRouter(backend)
        router.register_hook("post_chat", my_hook)
    """
    
    HOOK_POST_CHAT = "post_chat"
    HOOK_ON_ERROR = "on_error"

    def __init__(self, backend_router: AsyncModelRouter) -> None:
        """
        Create a model router backed by a local async router.

        Args:
            backend_router (AsyncModelRouter): Instance of `AsyncModelRouter`.
        """
        self._router: AsyncModelRouter = backend_router
        self._hooks: Dict[str, List[HookCallback]] = {
            self.HOOK_POST_CHAT: [],
            self.HOOK_ON_ERROR: [],
        }
    
    def register_hook(self, event_type: str, callback: HookCallback) -> None:
        """
        Register a hook callback for a specific event type.
        
        Args:
            event_type (str): The event type to hook into. 
                Supported: "post_chat", "on_error"
            callback (HookCallback): Async callback function.
                - For "post_chat": receives ChatCompleteEvent
                - For "on_error": receives ChatErrorEvent
        
        Raises:
            ValueError: If the event type is not supported.
            
        Example:
            async def log_tokens(event: ChatCompleteEvent):
                if event.token_usage:
                    print(f"Used {event.token_usage.prompt_tokens} tokens")
            
            router.register_hook("post_chat", log_tokens)
        """
        if event_type not in self._hooks:
            raise ValueError(
                f"Unknown event type: {event_type}. "
                f"Supported types: {list(self._hooks.keys())}"
            )
        self._hooks[event_type].append(callback)
        logger.debug("Hook registered for '%s'. Total hooks: %d", 
                     event_type, len(self._hooks[event_type]))
    
    def unregister_hook(self, event_type: str, callback: HookCallback) -> bool:
        """
        Remove a previously registered hook callback.
        
        Args:
            event_type (str): The event type.
            callback (HookCallback): The callback to remove.
            
        Returns:
            bool: True if the callback was found and removed.
        """
        if event_type not in self._hooks:
            return False
        try:
            self._hooks[event_type].remove(callback)
            logger.debug("Hook unregistered for '%s'. Total hooks: %d", 
                         event_type, len(self._hooks[event_type]))
            return True
        except ValueError:
            return False
    
    def clear_hooks(self, event_type: Optional[str] = None) -> None:
        """
        Clear all hooks for a specific event type, or all hooks if not specified.
        
        Args:
            event_type (Optional[str]): Event type to clear. If None, clears all hooks.
        """
        if event_type is None:
            for key in self._hooks:
                self._hooks[key].clear()
            logger.debug("All hooks cleared.")
        elif event_type in self._hooks:
            self._hooks[event_type].clear()
            logger.debug("Hooks cleared for '%s'.", event_type)
    
    async def _trigger_hooks(self, event_type: str, event_data: Any) -> None:
        """
        Trigger all registered hooks for an event type.
        
        Args:
            event_type (str): The event type.
            event_data (Any): The event data to pass to callbacks.
        """
        if event_type not in self._hooks:
            return
        
        for callback in self._hooks[event_type]:
            try:
                await callback(event_data)
            except Exception as exc:
                logger.warning("Hook callback failed for '%s': %s", event_type, exc)

    async def chat(
        self,
        user_prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
        timeout: int = 300,
        **kwargs: Union[str, float, int],
    ) -> Optional[str]:
        """
        Send a chat request to the configured LLM backend.

        Args:
            user_prompt (str): Prompt text provided by the user.
            system_prompt (str): Optional system prompt steering the LLM behaviour. Defaults to an empty string.
            model_name (Optional[str]): Optional identifier for the model to use.
            timeout (int): Maximum time to wait for a response in seconds. Defaults to 300 seconds.
            **kwargs (Union[str, float, int]): Additional sampling parameters forwarded to the backend.

        Returns:
            Optional[str]: Response string or None if the request failed.
        """
        sanitized_prompt = f"{user_prompt} /no_think"

        try:
            response, token_usage = await self._router.chat(
                user_prompt=sanitized_prompt,
                system_prompt=system_prompt,
                model_name=model_name,
                timeout=timeout,
                **kwargs,
            )
        except Exception as exc:
            error_event = ChatErrorEvent(
                error=exc,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                model_name=model_name,
            )
            await self._trigger_hooks(self.HOOK_ON_ERROR, error_event)
            raise
        
        final_response: Optional[Union[str, List[str]]] = None
        processed_results = []
        
        if response is not None:
            for result in response:
                result = re.sub(r"<think>.*?</think>", "", result, flags=re.S)
                processed_results.append(result)

            if len(processed_results) == 1:
                final_response = processed_results[0]
            elif len(processed_results) > 1:
                final_response = processed_results
        
        chat_event = ChatCompleteEvent(
            response=final_response,
            raw_response=response,
            token_usage=token_usage,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model_name=model_name,
        )
        await self._trigger_hooks(self.HOOK_POST_CHAT, chat_event)
        
        return final_response

    async def embed(
        self,
        texts: Union[str, List[str]],
        model_name: Optional[str] = None,
        timeout: int = 300,
    ) -> Union[Optional[List[float]], Optional[List[List[float]]]]:
        """
        Generate embeddings for the provided text or texts.

        Args:
            texts (Union[str, List[str]]): Single string or list of strings to embed.
            model_name (Optional[str]): Optional identifier for the embedding model.
            timeout (int): Maximum time to wait for the response in seconds. Defaults to 300 seconds.

        Returns:
            Union[Optional[List[float]], Optional[List[List[float]]]]: Optional embedding vector
                or list of vectors depending on the input.
        """
        is_single_string = isinstance(texts, str)
        input_texts = [texts] if is_single_string else list(texts)
        if not input_texts:
            return [] if not is_single_string else None

        if not hasattr(self._router, "embed_documents"):
            raise NotImplementedError("The local backend does not implement 'embed_documents'.")
        embeddings = await self._router.embed_documents(
            texts=input_texts,
            model_name=model_name,
            timeout=timeout,
        )

        if embeddings is None:
            return None

        return embeddings[0] if is_single_string else embeddings

    async def close(self) -> None:
        """Release resources held by the underlying backend."""
        logger.info("Closing ModelRouter (backend: %s)...", "Local")

        await self._router.close()
        logger.info("ModelRouter closed.")

    async def get_config(self) -> Dict[str, Any]:
        """
        Retrieve configuration or status information from the backend router.

        Returns:
            Dict[str, Any]: Backend configuration data.
        """

        return self._router.get_config()

    def __repr__(self) -> str:
        """
        Return an official representation of the ModelRouter instance.

        Returns:
            str: String representation of the object, including backend type.
        """
        backend_type = "Local"
        return f"ModelRouter(backend={backend_type}, router_instance={self._router})"
