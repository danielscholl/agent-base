"""Configuration package for agent-base."""

# Import legacy AgentConfig for backward compatibility
from .constants import DEFAULT_GEMINI_MODEL
from .defaults import get_default_config
from .editor import (
    EditorError,
    detect_editor,
    edit_and_validate,
    open_in_editor,
    validate_after_edit,
    wait_for_editor,
)
from .manager import (
    ConfigurationError,
    get_config_path,
    load_config,
    load_config_with_env,
    merge_with_env,
    save_config,
    validate_config,
)
from .schema import AgentSettings, MemoryConfig, ProviderConfig, TelemetryConfig

__all__ = [
    # Constants
    "DEFAULT_GEMINI_MODEL",
    # Schema
    "AgentSettings",
    "ProviderConfig",
    "TelemetryConfig",
    "MemoryConfig",
    # Manager
    "ConfigurationError",
    "get_config_path",
    "load_config",
    "load_config_with_env",
    "save_config",
    "merge_with_env",
    "validate_config",
    # Defaults
    "get_default_config",
    # Editor
    "EditorError",
    "detect_editor",
    "open_in_editor",
    "wait_for_editor",
    "validate_after_edit",
    "edit_and_validate",
]
