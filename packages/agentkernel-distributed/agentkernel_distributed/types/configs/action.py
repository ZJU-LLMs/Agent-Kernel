"""Configurations for action modules in the MAS framework."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field, field_validator

from .common import PluginConfig


class ActionComponentConfig(BaseModel):
    """Configuration for a specific component within an action module.

    Attributes:
        plugins (Dict[str, PluginConfig]): A dictionary mapping plugin names to their configurations.
    """

    plugins: Dict[str, PluginConfig] = Field(
        ..., description="A dictionary mapping plugin names to their configurations."
    )


class ActionConfig(BaseModel):
    """Defines the configuration for an entire action module.

    Attributes:
        name (str): The name of the action module.
        components (Dict[str, ActionComponentConfig]): Configuration for the components within the action module.
    """

    name: str = Field(..., description="The name of the action module.", min_length=1)
    components: Dict[str, ActionComponentConfig] = Field(
        ..., description="Configuration for the components within the action module."
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate that the name is not empty or just whitespace.

        Args:
            v (str): The value of the 'name' field.

        Returns:
            str: The validated name.

        Raises:
            ValueError: If the name is empty or consists only of whitespace.
        """
        if not v or not v.strip():
            raise ValueError("ActionConfig name cannot be empty or contain only whitespace.")
        return v
