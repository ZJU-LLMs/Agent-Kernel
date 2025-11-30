"""Custom exceptions used throughout the MAS toolkit."""

class PluginTypeMismatchError(TypeError):
    """Raised when attempting to attach a plugin to an incompatible component."""
    
    def __init__(self, component_name: str, plugin_component_type: str, plugin_name: str):
        self.component_name = component_name
        self.plugin_component_type = plugin_component_type
        self.plugin_name = plugin_name
        super().__init__(
            f"Plugin '{plugin_name}' belongs to component type '{plugin_component_type}', "
            f"cannot be registered to component '{component_name}'"
        )


class ValidationError(ValueError):
    """Custom exception for validation and resolution errors."""
    pass
