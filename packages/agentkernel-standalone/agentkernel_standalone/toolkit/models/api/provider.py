"""Abstract base classes for model providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class TokenUsage:
    """Token usage information from LLM API response.
    
    Attributes:
        prompt_tokens: Number of tokens in the input prompt.
        completion_tokens: Number of tokens in the generated response.
        total_tokens: Total number of tokens (prompt + completion).
    """
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self):
        """Calculate total_tokens if not provided."""
        if self.total_tokens == 0 and (self.prompt_tokens > 0 or self.completion_tokens > 0):
            self.total_tokens = self.prompt_tokens + self.completion_tokens


ChatResponseWithUsage = Tuple[Optional[List[str]], Optional[TokenUsage]]


class ModelProvider(ABC):
    """Abstract base class for a generic model provider.

    This class defines the basic interface for a model provider, including
    configuration and capabilities.

    Args:
        model_config (Dict[str, Any]): Configuration dictionary for the model.
            Must contain 'base_url' and 'model'.

    Attributes:
        base_url (str): The base URL of the model API.
        model (str): The name of the model.
        api_key (Optional[str]): The API key for authentication.
        capabilities (List[str]): A list of capabilities the model supports,
            e.g., 'chat', 'embedding'.
        config (Dict[str, Any]): The original model configuration.

    Raises:
        ValueError: If required parameters are missing from the configuration.
    """

    def __init__(self, model_config: Dict[str, Any]):
        required_params = ["base_url", "model"]
        missing = [p for p in required_params if not model_config.get(p)]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        self.base_url: str = model_config["base_url"]
        self.model: str = model_config["model"]
        self.api_key: str | None = model_config.get("api_key")
        self.capabilities: List[str] = model_config.get("capabilities", ["chat"])
        self.config: Dict[str, Any] = model_config

    def __str__(self) -> str:
        """Returns a string representation of the model provider."""
        return (
            f"[{self.__class__.__name__}] "
            f"model={self.model}, "
            f"capabilities={self.capabilities}, "
            f"base_url={self.base_url}, "
            f"api_key={'***' if self.api_key else 'None'}"
        )

    def __repr__(self) -> str:
        """Returns a detailed string representation of the model provider."""
        return self.__str__()


class ChatModelProvider(ModelProvider):
    """Abstract base class for a chat model provider."""

    def __init__(self, model_config: Dict[str, Any]):
        super().__init__(model_config)
        self.system_prompt: str = model_config.get("system_prompt", "")
        self.sampling_params: Dict[str, Any] = model_config.get("sampling_params", {})

    @abstractmethod
    def get_request_params(self, user_prompt: str, system_prompt: str | None = None, **kwargs: Any) -> Dict[str, Any]:
        """Constructs the request parameters for a chat API call.

        Args:
            user_prompt (str): The prompt from the user.
            system_prompt (Optional[str]): An optional system-level prompt.
            **kwargs (Any): Additional sampling parameters.

        Returns:
            Dict[str, Any]: A dictionary of parameters for the API request.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_response(self, response: str) -> str:
        """Parses the raw response from the chat API.

        Args:
            response (str): The raw response string from the API.

        Returns:
            str: The extracted message content.
        """
        raise NotImplementedError
    
    def parse_response_with_usage(self, response: str) -> ChatResponseWithUsage:
        """Parses the raw response and extracts both content and token usage.

        Args:
            response (str): The raw response string from the API.

        Returns:
            ChatResponseWithUsage: A tuple of (content, token_usage).
                Default implementation returns (parse_response result, None).
        """
        content = self.parse_response(response)
        return (content if isinstance(content, list) else [content] if content else None, None)


class EmbeddingModelProvider(ModelProvider):
    """Abstract base class for an embedding model provider."""

    @abstractmethod
    def get_embedding_request_params(self, texts: List[str]) -> Dict[str, Any]:
        """Constructs the request parameters for an embedding API call.

        Args:
            texts (List[str]): A list of texts to be embedded.

        Returns:
            Dict[str, Any]: A dictionary of parameters for the API request.
        """
        raise NotImplementedError

    @abstractmethod
    def parse_embedding_response(self, response: str) -> List[List[float]]:
        """Parses the raw response from the embedding API.

        Args:
            response (str): The raw response string from the API.

        Returns:
            List[List[float]]: A list of embedding vectors.
        """
        raise NotImplementedError
