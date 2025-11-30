"""Top-level configuration models for the MAS runtime."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .action import ActionComponentConfig, ActionConfig
from .agent import AgentComponentConfig, AgentConfig, AgentTemplate, AgentTemplateConfig
from .common import PluginConfig
from .database import AdapterConfig, DatabaseConfig, PoolConfig
from .environment import EnvironmentComponentConfig, EnvironmentConfig
from .model import ModelConfig, ModelProviderConfig
from .system import MessagerConfig, RecorderConfig, SystemConfig, TimerConfig


class SimulationSettings(BaseModel):
    """Simulation scope configuration such as pod sizing and tick limits."""

    max_ticks: int = Field(..., ge=0)


class ConfigPaths(BaseModel):
    """File paths pointing at sub-configuration files."""

    environment: str
    actions: str
    agent_templates: str
    system: str
    database: str
    models: str


class DataSources(BaseModel):
    """
    Mapping of data keys to file paths used when loading simulation data.

    Extra fields are permitted so data source keys can be customised.
    """

    model_config = ConfigDict(extra="allow")


class APIServerConfig(BaseModel):
    """Configuration for the optional API server used by examples."""

    host: str = "127.0.0.1"
    port: int = 8000


class PodConfig(BaseModel):
    """Configuration bundle used when constructing pod instances."""

    agent_templates: Optional[AgentTemplateConfig] = None
    agents: List[AgentConfig] = Field(..., description="List of agent configurations for this pod.")
    actions: Optional[ActionConfig] = None
    environment: Optional[EnvironmentConfig] = None
    database: Optional[DatabaseConfig] = None


class Config(BaseModel):
    """Root object representing a fully materialised simulation configuration."""

    simulation: SimulationSettings
    configs: ConfigPaths
    data: DataSources
    api_server: Optional[APIServerConfig] = None

    environment: Optional[EnvironmentConfig] = None
    actions: Optional[ActionConfig] = None
    agent_templates: Optional[AgentTemplateConfig] = None
    database: Optional[DatabaseConfig] = None
    models: Optional[ModelConfig] = None
    system: Optional[SystemConfig] = None

    agents: Optional[List[AgentConfig]] = None
    loaded_data: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "Config",
    "PodConfig",
    "SimulationSettings",
    "ConfigPaths",
    "DataSources",
    "AgentConfig",
    "AgentTemplate",
    "AgentComponentConfig",
    "AgentTemplateConfig",
    "ActionConfig",
    "ActionComponentConfig",
    "EnvironmentConfig",
    "EnvironmentComponentConfig",
    "SystemConfig",
    "MessagerConfig",
    "RecorderConfig",
    "TimerConfig",
    "ModelProviderConfig",
    "ModelConfig",
    "DatabaseConfig",
    "PoolConfig",
    "AdapterConfig",
    "PluginConfig",
    "APIServerConfig",
]
