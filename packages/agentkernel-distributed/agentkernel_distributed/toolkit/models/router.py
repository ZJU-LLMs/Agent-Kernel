"""Unified client facade for local model routers."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from ...toolkit.logger import get_logger
from .async_router import AsyncModelRouter

logger = get_logger(__name__)


class ModelRouter:
    """Facade that unifies local model router backends."""

    def __init__(self, backend_router: AsyncModelRouter) -> None:
        """
        Create a model router backed by either a local async router.

        Args:
            backend_router (AsyncModelRouter): Instance of `AsyncModelRouter`.
        """
        self._router: AsyncModelRouter = backend_router

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

        response = await self._router.chat(
            user_prompt=sanitized_prompt,
            system_prompt=system_prompt,
            model_name=model_name,
            timeout=timeout,
            **kwargs,
        )
        
        final_response = []
        if response is not None:
            for result in response:
                result = re.sub(r"<think>.*?</think>", "", result, flags=re.S)
                final_response.append(result)

        if len(final_response) == 1:
            return final_response[0]
        
        if final_response == []:
            return None
        
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
