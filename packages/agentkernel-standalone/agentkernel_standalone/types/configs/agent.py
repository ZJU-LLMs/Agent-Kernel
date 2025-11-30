"""Configurations for agent templates and individual agents in the MAS framework."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from .common import PluginConfig


class AgentComponentConfig(BaseModel):
    """Configuration for a single component within an agent template.

    Attributes:
        plugin (Dict[str, PluginConfig]): A dictionary mapping the plugin name to its configuration.
    """

    plugin: Dict[str, PluginConfig] = Field(
        ...,
        description="A dictionary mapping the plugin name to its " "configuration. Expects exactly one plugin.",
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
            raise ValueError("Component must have exactly one plugin.")
        return v


class AgentTemplate(BaseModel):
    """Represents a single agent template which can be applied to one or more agents.

    Attributes:
        name (str): The unique name of the agent template.
        agents (Optional[List[str]]): A list of agent IDs that use this template.
        component_order (Optional[List[str]]): The order of components for agents using this template.
        components (Dict[str, AgentComponentConfig]): A dictionary of components configured for this agent template.
    """

    name: str = Field(..., description="The unique name of the agent template.", min_length=1)
    agents: Optional[List[str]] = None
    component_order: Optional[List[str]] = None
    components: Dict[str, AgentComponentConfig] = Field(
        ...,
        description="A dictionary of components configured for this agent " "template.",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        """Validate that the template name is not empty.

        Args:
            v (str): The template name.

        Returns:
            str: The validated template name.

        Raises:
            ValueError: If the name is empty or contains only whitespace.
        """
        if not v or not v.strip():
            raise ValueError("Template name cannot be empty.")
        return v


class AgentTemplateConfig(BaseModel):
    """The main configuration model for the agents_config.yaml file. It holds a list of all defined agent templates.

    Attributes:
        templates (List[AgentTemplate]): A list of agent templates.
    """

    templates: List[AgentTemplate]


class AgentConfig(BaseModel):
    """The main configuration model for a single agent's configuration.It holds the components and their order for a specific agent.

    Attributes:
        id (str): The unique identifier for the agent configuration.
        component_order (Optional[List[str]]): The order of components for this agent.
        components (Dict[str, AgentComponentConfig]): A dictionary of components configured for this agent.
    """

    id: str = Field(..., description="The unique identifier for the agent configuration.")
    component_order: Optional[List[str]] = None
    components: Dict[str, AgentComponentConfig] = Field(
        ...,
        description="A dictionary of components configured for this agent.",
    )
