"""Configurations for model providers."""

from typing import List, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class ModelProviderConfig(BaseModel):
    """Configuration for a single model provider.

    This class defines the settings required to configure a model provider,
    including its name, the specific model to use, authentication credentials,
    and capabilities.

    Attributes:
        name (str): The name of the provider class (e.g., 'QwenProvider').
        model (str): The specific model name to use (e.g., 'qwen-plus-latest').
        api_key (Optional[str]): The API key for authentication.
        base_url (str): The base URL of the API endpoint.
        capabilities (List[str]): A list of capabilities, such as 'chat' or
            'embedding'. Defaults to ['chat'].
    """

    name: str = Field(
        ...,
        description="The name of the provider class, e.g., 'QwenProvider'.",
        min_length=1,
    )
    model: str = Field(
        ...,
        description="The specific model name to use, e.g., 'qwen-plus-latest'.",
        min_length=1,
    )
    api_key: Optional[str] = Field(
        default=None,
        description="The API key for authenticating with the provider's service.",
        min_length=1,
    )
    base_url: str = Field(..., description="The base URL of the API endpoint.", min_length=1)

    capabilities: List[str] = Field(
        default=["chat"],
        description="A list of capabilities supported by this model. Can be " "'chat', 'embedding', or both.",
    )

    @field_validator("name", "model", "base_url")
    @classmethod
    def check_not_empty(cls, v: str, info: ValidationInfo) -> str:
        """Ensure critical string fields are not empty or just whitespace.

        Args:
            v (str): The value of the field being validated.
            info (ValidationInfo): Pydantic validation info.

        Returns:
            str: The validated string value.

        Raises:
            ValueError: If the string is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError(f"Field '{info.field_name}' cannot be empty or contain only " "whitespace.")
        return v


ModelConfig = List[ModelProviderConfig]
