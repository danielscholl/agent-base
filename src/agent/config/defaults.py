"""Default configuration values for agent-base."""

# Import and re-export all constants for backward compatibility
from .constants import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_AZURE_API_VERSION,
    DEFAULT_CONFIG_PATH,
    DEFAULT_DATA_DIR,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GITHUB_ENDPOINT,
    DEFAULT_GITHUB_MODEL,
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_LOCAL_MODEL,
    DEFAULT_MEMORY_DIR,
    DEFAULT_MEMORY_HISTORY_LIMIT,
    DEFAULT_MEMORY_TYPE,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OTLP_ENDPOINT,
    DEFAULT_SESSION_DIR,
)
from .schema import AgentSettings

__all__ = [
    "get_default_config",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_DATA_DIR",
    "DEFAULT_MEMORY_DIR",
    "DEFAULT_SESSION_DIR",
    "DEFAULT_LOCAL_BASE_URL",
    "DEFAULT_LOCAL_MODEL",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_ANTHROPIC_MODEL",
    "DEFAULT_AZURE_API_VERSION",
    "DEFAULT_GEMINI_MODEL",
    "DEFAULT_GITHUB_MODEL",
    "DEFAULT_GITHUB_ENDPOINT",
    "DEFAULT_OTLP_ENDPOINT",
    "DEFAULT_MEMORY_TYPE",
    "DEFAULT_MEMORY_HISTORY_LIMIT",
]


def get_default_config() -> AgentSettings:
    """Get default configuration settings.

    Returns:
        AgentSettings with sensible defaults:
        - No providers enabled (explicit configuration required)
        - Telemetry disabled
        - In-memory storage for conversation history
        - Data directory at ~/.agent

    Example:
        >>> config = get_default_config()
        >>> config.providers.enabled
        []
        >>> config.telemetry.enabled
        False
    """
    return AgentSettings(
        version="1.0",
        providers={  # type: ignore[arg-type]
            "enabled": [],  # No providers by default - explicit config required
            "local": {
                "base_url": DEFAULT_LOCAL_BASE_URL,
                "model": DEFAULT_LOCAL_MODEL,
            },
            "openai": {
                "enabled": False,
                "api_key": None,
                "model": DEFAULT_OPENAI_MODEL,
            },
            "anthropic": {
                "enabled": False,
                "api_key": None,
                "model": DEFAULT_ANTHROPIC_MODEL,
            },
            "azure": {
                "enabled": False,
                "endpoint": None,
                "deployment": None,
                "api_version": DEFAULT_AZURE_API_VERSION,
                "api_key": None,
            },
            "foundry": {
                "enabled": False,
                "project_endpoint": None,
                "model_deployment": None,
            },
            "gemini": {
                "enabled": False,
                "api_key": None,
                "model": DEFAULT_GEMINI_MODEL,
                "use_vertexai": False,
                "project_id": None,
                "location": None,
            },
            "github": {
                "enabled": False,
                "token": None,
                "model": DEFAULT_GITHUB_MODEL,
                "endpoint": DEFAULT_GITHUB_ENDPOINT,
                "org": None,
            },
        },
        agent={  # type: ignore[arg-type]
            "data_dir": "~/.agent",
            "log_level": "info",
        },
        telemetry={  # type: ignore[arg-type]
            "enabled": False,
            "enable_sensitive_data": False,
            "otlp_endpoint": "http://localhost:4317",
            "applicationinsights_connection_string": None,
        },
        memory={  # type: ignore[arg-type]
            "enabled": True,
            "type": "in_memory",
            "history_limit": 20,
            "mem0": {
                "storage_path": None,
                "api_key": None,
                "org_id": None,
                "user_id": None,
                "project_id": None,
            },
        },
    )
