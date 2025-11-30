"""Provider for OpenAI-compatible API endpoints."""

import json
from typing import Any, Dict, List, Optional

from ....toolkit.logger import get_logger
from .provider import ChatModelProvider, EmbeddingModelProvider

logger = get_logger(__name__)

class OpenAIProvider(ChatModelProvider, EmbeddingModelProvider):
    """A provider for OpenAI-compatible API endpoints.

    This class interacts with a remote LLM server or a local vLLM server
    that exposes an OpenAI-compatible API.

    Example `models_config.yaml` for a local vLLM:
    ```yaml
    - name: OpenAIProvider
      model: Qwen3-8B
      base_url: http://127.0.0.1:<PORT>/v1
    ```

    Example for a remote OpenAI-format API:
    ```yaml
    - name: OpenAIProvider
      model: qwen-plus-latest
      api_key: YOUR_API_KEY
      base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    ```

    Attributes:
        base_url (str): The base URL for the API endpoint.
        model (str): The name of the model being served.
        api_key (Optional[str]): The API key for authentication.
    """

    def __init__(self, model_config: Dict[str, Any]):
        """Initializes the OpenAIProvider.

        Args:
            model_config (Dict[str, Any]): A dictionary containing configuration:
                - base_url (str): The base URL of the API endpoint (e.g.,
                  "http://localhost:8000/v1").
                - model (str): The name of the served model.
                - api_key (Optional[str]): The API key, which can be a
                  placeholder like "EMPTY" if not required.
                - sampling_params (Dict): A dictionary of sampling parameters
                  like temperature and max_tokens.
        """
        super().__init__(model_config)

    def get_request_params(
        self,
        user_prompt: str,
        system_prompt: str = "",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Prepares request parameters for the chat completions endpoint.

        This method follows the OpenAI API format.

        Args:
            user_prompt (str): The prompt provided by the user.
            system_prompt (str): An optional system prompt to guide the model.
                If not provided, the default from the config is used.
            **kwargs (Any): Additional sampling parameters to override defaults.

        Returns:
            Dict[str, Any]: A dictionary containing the URL, headers, and JSON
            payload for the request.
        """
        final_system_prompt = system_prompt or self.system_prompt

        messages = []
        if final_system_prompt:
            messages.append({"role": "system", "content": final_system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
        }

        payload.update(self.sampling_params)
        payload.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        return {
            "url": f"{self.base_url}/chat/completions",
            "headers": headers,
            "json": payload,
        }

    def parse_response(self, response: str) -> Optional[str]:
        """Parses the JSON response and extracts the message content.

        The response structure is expected to be identical to the OpenAI API format.

        Args:
            response (str): The raw JSON response from the server.

        Returns:
            Optional[str]: The extracted text content of the message, or None
            if parsing fails.
        """
        try:
            res = json.loads(response)
            final_result = []
            for choice in res.get("choices", []):
                message = choice.get("message", {}).get("content", "").strip()
                final_result.append(message)
            
            return final_result
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"{self} failed to parse response: {e} - Response: {response}")
            return None

    def get_embedding_request_params(self, texts: List[str]) -> Dict[str, Any]:
        """Prepares request parameters for the embeddings endpoint.

        Args:
            texts (List[str]): A list of texts to be embedded.

        Returns:
            Dict[str, Any]: A dictionary containing the URL, headers, and JSON
            payload for the request.
        """
        cleaned_texts = [text.replace("\n", " ") for text in texts]

        payload = {
            "input": cleaned_texts,
            "model": self.model,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        return {
            "url": f"{self.base_url}/embeddings",
            "headers": headers,
            "json": payload,
        }

    def parse_embedding_response(self, response: str) -> Optional[List[List[float]]]:
        """Parses the JSON response from the embeddings endpoint.

        Args:
            response (str): The raw JSON response from the server.

        Returns:
            Optional[List[List[float]]]: A list of embedding vectors, sorted
            by their original index, or None if parsing fails.
        """
        try:
            res = json.loads(response)
            return [d["embedding"] for d in sorted(res["data"], key=lambda x: x["index"])]
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"{self} failed to parse embedding response: {e} - Response: {response}")
            return None
