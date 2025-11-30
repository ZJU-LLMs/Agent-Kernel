# packages/agentkernel-standalone/agentkernel_standalone/toolkit/logger/logger.py

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from colorlog import ColoredFormatter

    COLOR_LOG_AVAILABLE = True
except ImportError:
    ColoredFormatter = logging.Formatter  # type: ignore[assignment, misc]
    COLOR_LOG_AVAILABLE = False

# --- Global State ---
_is_configured = False
_setup_lock = threading.Lock()


def _get_default_log_config() -> Dict[str, Any]:
    """Dynamically generate the logging configuration based on environment variables.

    This function reads environment variables to determine the application package name
    and constructs a comprehensive logging configuration dictionary.

    Args:
        None

    Returns:
        Dict[str, Any]: A dictionary containing the complete logging configuration,
            including console settings, file handlers, and filter rules.

    Environment Variables:
        MAS_PROJECT_REL_PATH: The root package name of the user application.
                              Defaults to 'examples.standalone_test'.
    """
    app_package = os.environ.get("MAS_PROJECT_REL_PATH", "examples.standalone_test")

    return {
        "propagate": True,
        "console": {
            "enabled": True,
            "format": (
                "%(log_color)s%(asctime)s | %(levelname)-8s | PID:%(process)d | "
                "%(purple)s%(name)s%(reset)s:%(cyan)s%(funcName)s:%(lineno)d%(reset)s - "
                "%(message_log_color)s%(message)s"
            ),
        },
        "files": [
            {
                "name": "simulation_flow",
                "path": "logs/app/simulation_flow.log",
                "filter": {
                    "include": ["__main__", app_package],
                    "exclude": [
                        f"{app_package}.plugins",
                        f"{app_package}.utils",
                        f"{app_package}.evaluation",
                    ],
                },
            },
            {
                "name": "agent_plan_plugin",
                "path": "logs/app/agent/plan.log",
                "filter": f"{app_package}.plugins.agent.plan",
            },
            {
                "name": "agent_act_plugin",
                "path": "logs/app/agent/invoke.log",
                "filter": f"{app_package}.plugins.agent.invoke",
            },
            {
                "name": "agent_reflect_plugin",
                "path": "logs/app/agent/reflect.log",
                "filter": f"{app_package}.plugins.agent.reflect",
            },
            {
                "name": "agent_perceive_plugin",
                "path": "logs/app/agent/perceive.log",
                "filter": f"{app_package}.plugins.agent.perceive",
            },
            {
                "name": "agent_state_plugin",
                "path": "logs/app/agent/state.log",
                "filter": f"{app_package}.plugins.agent.state",
            },
            {
                "name": "agent_profile_plugin",
                "path": "logs/app/agent/profile.log",
                "filter": f"{app_package}.plugins.agent.profile",
            },
            {
                "name": "action_communication_plugin",
                "path": "logs/app/action/communication.log",
                "filter": f"{app_package}.plugins.action.communication",
            },
            {
                "name": "action_other_plugin",
                "path": "logs/app/action/otheractions.log",
                "filter": f"{app_package}.plugins.action.otheractions",
            },
            {
                "name": "action_tools_plugin",
                "path": "logs/app/action/tools.log",
                "filter": f"{app_package}.plugins.action.tools",
            },
            {
                "name": "env_relation_plugin",
                "path": "logs/app/environment/relation.log",
                "filter": f"{app_package}.plugins.environment.relation",
            },
            {
                "name": "env_space_entity_plugin",
                "path": "logs/app/environment/space.log",
                "filter": f"{app_package}.plugins.environment.space",
            },
            {"name": "app_utils", "path": "logs/app/utils.log", "filter": f"{app_package}.utils"},
            {"name": "app_evaluation", "path": "logs/app/evaluation.log", "filter": f"{app_package}.evaluation"},
            {
                "name": "mas_builder",
                "path": "logs/framework/mas/builder.log",
                "filter": "agentkernel_standalone.mas.builder",
            },
            {"name": "mas_pod", "path": "logs/framework/mas/pod.log", "filter": "agentkernel_standalone.mas.pod"},
            {
                "name": "mas_controller",
                "path": "logs/framework/mas/controller.log",
                "filter": "agentkernel_standalone.mas.controller",
            },
            {
                "name": "mas_system",
                "path": "logs/framework/mas/system.log",
                "filter": "agentkernel_standalone.mas.system",
            },
            {
                "name": "mas_interface",
                "path": "logs/framework/mas/interface.log",
                "filter": "agentkernel_standalone.mas.interface",
            },
            {
                "name": "mas_agent",
                "path": "logs/framework/mas/agent.log",
                "filter": "agentkernel_standalone.mas.agent",
            },
            {
                "name": "mas_action",
                "path": "logs/framework/mas/action.log",
                "filter": "agentkernel_standalone.mas.action",
            },
            {
                "name": "mas_environment",
                "path": "logs/framework/mas/environment.log",
                "filter": "agentkernel_standalone.mas.environment",
            },
            {
                "name": "toolkit_models",
                "path": "logs/framework/toolkit/models.log",
                "filter": "agentkernel_standalone.toolkit.models",
            },
            {
                "name": "toolkit_storages",
                "path": "logs/framework/toolkit/storages.log",
                "filter": "agentkernel_standalone.toolkit.storages",
            },
            {
                "name": "toolkit_generation",
                "path": "logs/framework/toolkit/generation.log",
                "filter": "agentkernel_standalone.toolkit.generation",
            },
            {
                "name": "toolkit_utils",
                "path": "logs/framework/toolkit/utils.log",
                "filter": "agentkernel_standalone.toolkit.utils",
            },
            {
                "name": "framework_other",
                "path": "logs/framework/other.log",
                "filter": {
                    "include": ["agentkernel_standalone"],
                    "exclude": [
                        "agentkernel_standalone.mas",
                        "agentkernel_standalone.toolkit",
                    ],
                },
            },
        ],
        "file_handler_defaults": {
            "format": "%(asctime)s | %(levelname)-8s | PID:%(process)d | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        },
    }


def _make_filter(filter_config: Optional[Union[str, List[str], Dict[str, Any]]]) -> Optional[logging.Filter]:
    """Create a logging filter based on a flexible configuration.

    This factory function can create filters that:
    1. Match a single prefix (if config is a string).
    2. Match any prefix from a list (if config is a list of strings).
    3. Match 'include' prefixes while rejecting 'exclude' prefixes (if config is a dict).

    Args:
        filter_config (Optional[Union[str, List[str], Dict[str, Any]]]): The configuration
            for the filter. Can be a string, a list of strings, or a dictionary with
            'include' and/or 'exclude' keys.

    Returns:
        Optional[logging.Filter]: A logging.Filter instance configured according to
            the rules, or None if the configuration is empty.
    """
    if not filter_config:
        return None

    include_prefixes: List[str] = []
    exclude_prefixes: List[str] = []

    if isinstance(filter_config, str):
        include_prefixes = [filter_config]
    elif isinstance(filter_config, list):
        include_prefixes = filter_config
    elif isinstance(filter_config, dict):
        include_conf = filter_config.get("include", [])
        exclude_conf = filter_config.get("exclude", [])
        include_prefixes = [include_conf] if isinstance(include_conf, str) else include_conf
        exclude_prefixes = [exclude_conf] if isinstance(exclude_conf, str) else exclude_conf
    else:
        return None

    class AdvancedFilter(logging.Filter):
        """A custom filter to handle include/exclude logic for logger names."""

        def __init__(self, include: List[str], exclude: List[str]):
            """Initialize the AdvancedFilter with include and exclude prefixes.

            Args:
                include (List[str]): A list of logger name prefixes to include.
                exclude (List[str]): A list of logger name prefixes to exclude.

            Returns:
                None
            """
            super().__init__()
            self.include = tuple(include)
            self.exclude = tuple(exclude)

        def filter(self, record: logging.LogRecord) -> bool:
            """Determine if a log record should be processed.

            Args:
                record (logging.LogRecord): The log record to evaluate.

            Returns:
                bool: True if the record should be processed, False otherwise.
            """
            if self.exclude and record.name.startswith(self.exclude):
                return False

            if not self.include:
                return True

            return record.name.startswith(self.include)

    return AdvancedFilter(include_prefixes, exclude_prefixes)


def _internal_setup_logging(config: Dict[str, Any]) -> None:
    """Configure the root logger based on the provided configuration dictionary.

    This function sets up console and file handlers for the root logger,
    applies formatters, and configures log levels based on environment variables.

    Args:
        config (Dict[str, Any]): A dictionary containing the logging configuration,
            including console settings, file handler definitions, and filter rules.

    Returns:
        None
    """
    root_logger = logging.getLogger()
    project_path = os.environ.get("MAS_PROJECT_ABS_PATH", ".")

    log_level_str = os.environ.get("MAS_LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    root_logger.setLevel(log_level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    console_cfg = config.get("console", {})
    if console_cfg.get("enabled", True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        use_color = COLOR_LOG_AVAILABLE and is_tty and os.environ.get("NO_COLOR") is None

        formatter: logging.Formatter
        if use_color:
            console_format = console_cfg.get("format")
            formatter = ColoredFormatter(
                fmt=console_format,
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                secondary_log_colors={"message": {"WARNING": "yellow", "ERROR": "red", "CRITICAL": "bold_red"}},
                style="%",
            )
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | PID:%(process)d | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    file_defaults = config.get("file_handler_defaults", {})
    file_format = file_defaults.get("format")

    for file_cfg in config.get("files", []):
        log_path = Path(project_path) / file_cfg["path"]
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S"))

        log_filter = _make_filter(file_cfg.get("filter"))
        if log_filter:
            file_handler.addFilter(log_filter)

        root_logger.addHandler(file_handler)

    propagate = config.get("propagate", True)
    logging.getLogger("agentkernel_standalone").propagate = propagate

    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("faker").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retrieve a logger instance, ensuring the logging system is configured.

    This function ensures thread-safe initialization of the logging system
    on first call, then returns the requested logger.

    Args:
        name (str): The name of the logger to retrieve, typically __name__.

    Returns:
        logging.Logger: A configured logger instance for the given name.
    """
    global _is_configured

    with _setup_lock:
        if not _is_configured:
            config = _get_default_log_config()
            _internal_setup_logging(config)
            _is_configured = True

    return logging.getLogger(name)


__all__ = ["get_logger", "COLOR_LOG_AVAILABLE"]
