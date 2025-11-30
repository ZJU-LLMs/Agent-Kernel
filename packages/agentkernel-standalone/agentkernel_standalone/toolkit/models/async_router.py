"""Async model router that multiplexes requests across configured providers."""

from __future__ import annotations

import asyncio
import importlib
import random
import sys
from typing import Dict, List, Optional

import aiohttp

from ...toolkit.logger import get_logger
from .api.provider import ModelProvider

logger = get_logger(__name__)

if sys.platform == "win32":  # pragma: no cover - platform-specific behaviour
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class AsyncModelRouter:
    """
    Client-side router that forwards chat and embedding calls to configured providers.

    The router operates entirely locally and chooses a provider that matches the
    requested capability and optional model name.
    """

    def __init__(self, models_configs: Optional[List[Dict[str, object]]] = None) -> None:
        """
        Initialise the router and load provider implementations from configuration.

        Args:
            models_configs (Optional[List[Dict[str, object]]]): Optional list of provider configuration dictionaries.
        """
        self.providers: List[ModelProvider] = []
        if models_configs:
            for config in models_configs:
                try:
                    provider_name = config["name"]
                    module_name = provider_name.replace("Provider", "").lower()
                    module = importlib.import_module(f".api.{module_name}", package=__package__)
                    provider_class = getattr(module, provider_name)
                    self.providers.append(provider_class(config))
                except (ImportError, AttributeError, KeyError) as exc:
                    logger.warning("Unable to load provider %s: %s", config, exc)

        self.session = aiohttp.ClientSession()

    async def _ensure_session(self) -> None:
        """Ensures the aiohttp session is open, recreating it if necessary."""
        if self.session.closed:
            logger.warning("%s session was closed. Recreating a new session.", self)
            await self.close()
            self.session = aiohttp.ClientSession()

    def _get_target_providers(self, capability: str, model_name: Optional[str] = None) -> List[ModelProvider]:
        """
        Select providers matching the requested capability and optional model.

        Args:
            capability (str): Capability identifier such as ``"chat"`` or ``"embedding"``.
            model_name (Optional[str]): Optional model identifier to filter the provider list.

        Returns:
            List[ModelProvider]: Providers that can fulfil the request.
        """
        if not self.providers:
            logger.warning("%s has no configured providers.", self)
            return []

        capable_providers = [provider for provider in self.providers if capability in provider.capabilities]

        if model_name:
            target_providers = [provider for provider in capable_providers if provider.model == model_name]
            logger.debug(
                "Filtering for model '%s' with capability '%s': %d total -> %d capable -> %d matching.",
                model_name,
                capability,
                len(self.providers),
                len(capable_providers),
                len(target_providers),
            )
        else:
            target_providers = capable_providers
            logger.debug(
                "Filtering for capability '%s': %d total -> %d capable.",
                capability,
                len(self.providers),
                len(target_providers),
            )

        if not target_providers:
            error_msg = f"No configured providers with capability '{capability}'"
            if model_name:
                error_msg += f" and model name '{model_name}' were found."
            else:
                error_msg += " were found."
            logger.error(error_msg)

        return target_providers

    async def chat(
        self,
        user_prompt: str,
        system_prompt: str = "",
        model_name: Optional[str] = None,
        timeout: int = 300,
        **kwargs: object,
    ) -> Optional[str]:
        """
        Execute a chat request against the first provider that succeeds.

        Args:
            user_prompt (str): User prompt passed to the provider.
            system_prompt (str): Optional system prompt. Defaults to an empty string.
            model_name (Optional[str]): Optional model identifier.
            timeout (int): Request timeout in seconds. Defaults to 300 seconds.
            **kwargs (object): Additional provider-specific request parameters.

        Returns:
            Optional[str]: Response payload or None when all providers fail.
        """
        target_providers = self._get_target_providers(capability="chat", model_name=model_name)
        if not target_providers:
            logger.warning("No target providers available for chat request.")
            return None

        retry_delay = 1
        max_delay = 60

        while True:
            await self._ensure_session()

            random.shuffle(target_providers)
            for provider in target_providers:
                params = provider.get_request_params(user_prompt, system_prompt, **kwargs)
                try:
                    logger.debug("Attempting chat request with provider: %s", provider.model)
                    async with self.session.post(
                        url=params["url"],
                        headers=params["headers"],
                        json=params["json"],
                        timeout=timeout,
                    ) as response:
                        response.raise_for_status()
                        return provider.parse_response(await response.text())
                except Exception as exc:
                    logger.warning("%s chat request failed with %s: %s", self, provider.model, exc)
                    continue

            logger.error("All providers failed for chat request. Retrying in %d seconds...", retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

    async def embed_documents(
        self,
        texts: List[str],
        model_name: Optional[str] = None,
        timeout: int = 300,
    ) -> Optional[List[List[float]]]:
        """
        Generate embeddings for a list of documents.

        Args:
            texts (List[str]): Documents to embed.
            model_name (Optional[str]): Optional model identifier.
            timeout (int): Request timeout in seconds. Defaults to 300 seconds.

        Returns:
            Optional[List[List[float]]]: Embeddings or None when all providers fail.
        """
        target_providers = self._get_target_providers(capability="embedding", model_name=model_name)
        if not target_providers:
            logger.warning("No target providers available for embedding request.")
            return None

        retry_delay = 1
        max_delay = 60

        while True:
            await self._ensure_session()

            random.shuffle(target_providers)
            for provider in target_providers:
                params = provider.get_embedding_request_params(texts)
                try:
                    logger.debug("Attempting embedding request with provider: %s", provider.model)
                    async with self.session.post(
                        url=params["url"],
                        headers=params["headers"],
                        json=params["json"],
                        timeout=timeout,
                    ) as response:
                        response.raise_for_status()
                        return provider.parse_embedding_response(await response.text())
                except Exception as exc:
                    logger.error("%s embedding request failed with %s: %s", self, provider.model, exc)
                    continue

            logger.error("All providers failed for embedding request. Retrying in %d seconds...", retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, max_delay)

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as exc:
                logger.error("%s failed to close session: %s", self, exc)

    def __del__(self) -> None:  # pragma: no cover - destructor logging
        """
        Log a warning if the session was not closed explicitly before destruction.
        """
        if self.session and not self.session.closed:
            logger.warning("%s session was not closed explicitly before destruction: %s", self, self.session)

    def get_config(self) -> Dict[str, List[str]]:
        """
        Return a serialisable view of the configured providers.

        Returns:
            Dict[str, List[str]]: Provider string representations keyed by ``providers``.
        """
        return {"providers": [str(provider) for provider in self.providers]}

    def __repr__(self) -> str:
        """
        Return an official string representation of the router instance.

        Returns:
            str: String representation of the object, including provider count.
        """
        return f"[{self.__class__.__name__}] providers={len(self.providers)}"
