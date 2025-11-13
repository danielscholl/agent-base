"""Default configuration values for agent-base."""

from pathlib import Path

from .schema import AgentSettings


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
                "base_url": "http://localhost:12434/engines/llama.cpp/v1",
                "model": "ai/phi4",
            },
            "openai": {
                "enabled": False,
                "api_key": None,
                "model": "gpt-5-mini",
            },
            "anthropic": {
                "enabled": False,
                "api_key": None,
                "model": "claude-haiku-4-5-20251001",
            },
            "azure": {
                "enabled": False,
                "endpoint": None,
                "deployment": None,
                "api_version": "2025-03-01-preview",
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
                "model": "gemini-2.0-flash-exp",
                "use_vertexai": False,
                "project_id": None,
                "location": None,
            },
            "github": {
                "enabled": False,
                "token": None,
                "model": "gpt-5-nano",
                "endpoint": "https://models.inference.ai.azure.com",
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


# Default paths
DEFAULT_CONFIG_PATH = Path.home() / ".agent" / "settings.json"
DEFAULT_DATA_DIR = Path.home() / ".agent"
DEFAULT_MEMORY_DIR = DEFAULT_DATA_DIR / "memory"
DEFAULT_SESSION_DIR = DEFAULT_DATA_DIR / "sessions"

# Default provider settings
DEFAULT_LOCAL_BASE_URL = "http://localhost:12434/engines/llama.cpp/v1"
DEFAULT_LOCAL_MODEL = "ai/phi4"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_AZURE_API_VERSION = "2025-03-01-preview"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"
DEFAULT_GITHUB_MODEL = "gpt-5-nano"

# Default telemetry settings
DEFAULT_OTLP_ENDPOINT = "http://localhost:4317"

# Default memory settings
DEFAULT_MEMORY_TYPE = "in_memory"
DEFAULT_MEMORY_HISTORY_LIMIT = 20
