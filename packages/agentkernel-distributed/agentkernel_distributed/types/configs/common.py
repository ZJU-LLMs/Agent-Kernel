"""Common plugin configuration model."""

from typing import Dict

from pydantic import BaseModel, ConfigDict


class PluginConfig(BaseModel):
    """A generic model for plugin configurations.

    This model defines a flexible structure for plugin settings, allowing for
    a dictionary of adapters and any other custom fields. The `extra='allow'`
    configuration enables the model to accept arbitrary additional fields not

    explicitly defined.

    Attributes:
        adapters (Dict[str, str]): A dictionary mapping adapter names to their
            respective configurations or identifiers. Defaults to an empty
            dictionary.
    """

    adapters: Dict[str, str] = {}

    model_config = ConfigDict(extra="allow")
