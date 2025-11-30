"""Configurations for environment modules."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, Field, field_validator

from .common import PluginConfig


class EnvironmentComponentConfig(BaseModel):
    """Configuration for a single component within an environment.

    Attributes:
        plugin (Dict[str, PluginConfig]): A dictionary mapping the plugin name to its configuration. Expects exactly one plugin.
    """

    plugin: Dict[str, PluginConfig] = Field(
        ...,
        description="A dictionary mapping the plugin name to its configuration. Expects exactly one plugin.",
    )

    @field_validator("plugin")
    @classmethod
    def must_contain_single_plugin(cls, v: Dict) -> Dict:
        """Validate that the plugin dictionary contains exactly one item.

        Args:
            v (Dict): The dictionary of plugins.

        Returns:
            Dict: The validated dictionary.

        Raises:
            ValueError: If the dictionary does not contain exactly one plugin.
        """
        if len(v) != 1:
            raise ValueError("Environment component must have exactly one plugin.")
        return v


class EnvironmentConfig(BaseModel):
    """Defines the configuration for an entire environment module.

    Attributes:
        name (str): The name of the environment.
        components (Dict[str, EnvironmentComponentConfig]): Configuration for the components within the environment.
    """

    name: str = Field(..., description="The name of the environment.", min_length=1)
    components: Dict[str, EnvironmentComponentConfig] = Field(
        ..., description="Configuration for the components within the environment."
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate that the environment name is not empty.

        Args:
            v (str): The environment name.

        Returns:
            str: The validated environment name.

        Raises:
            ValueError: If the name is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Environment name cannot be empty.")
        return v
