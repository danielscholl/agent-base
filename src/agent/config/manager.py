"""Configuration file manager for loading, saving, and managing agent settings."""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schema import AgentSettings


class ConfigurationError(Exception):
    """Raised when configuration operations fail."""

    pass


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to ~/.agent/settings.json
    """
    return Path.home() / ".agent" / "settings.json"


def load_config(config_path: Path | None = None) -> AgentSettings:
    """Load configuration from JSON file.

    Args:
        config_path: Optional path to config file. Defaults to ~/.agent/settings.json

    Returns:
        AgentSettings instance loaded from file, or default settings if file doesn't exist

    Raises:
        ConfigurationError: If file exists but is invalid JSON or fails validation

    Example:
        >>> settings = load_config()
        >>> settings.providers.enabled
        ['local']
    """
    if config_path is None:
        config_path = get_config_path()

    # Return defaults if file doesn't exist
    if not config_path.exists():
        return AgentSettings()

    try:
        with open(config_path) as f:
            data = json.load(f)

        # Validate and load into Pydantic model
        return AgentSettings(**data)

    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in configuration file {config_path}: {e}") from e
    except ValidationError as e:
        raise ConfigurationError(f"Configuration validation failed for {config_path}:\n{e}") from e
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}") from e


def save_config(settings: AgentSettings, config_path: Path | None = None) -> None:
    """Save configuration to JSON file with minimal formatting.

    Uses progressive disclosure: only saves enabled providers and non-null values.
    This creates cleaner, more user-friendly config files (~20 lines vs 100+ lines).

    Sets restrictive permissions (0o600) on POSIX systems to protect API keys.

    Args:
        settings: AgentSettings instance to save
        config_path: Optional path to config file. Defaults to ~/.agent/settings.json

    Raises:
        ConfigurationError: If save operation fails

    Example:
        >>> settings = AgentSettings()
        >>> settings.providers.enabled = ["openai"]
        >>> settings.providers.openai.api_key = "sk-..."
        >>> save_config(settings)
        # Creates minimal config with only openai (not all 6 providers)
    """
    if config_path is None:
        config_path = get_config_path()

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Set restrictive permissions before writing (POSIX only)
        old_umask = os.umask(0o077) if os.name != "nt" else None
        try:
            # Write with minimal formatting (progressive disclosure)
            json_str = settings.model_dump_json_minimal()
            with open(config_path, "w") as f:
                f.write(json_str)

            # Set restrictive permissions on POSIX systems (user read/write only)
            if os.name != "nt":  # Not Windows
                os.chmod(config_path, 0o600)
        finally:
            if old_umask is not None:
                os.umask(old_umask)

    except Exception as e:
        raise ConfigurationError(f"Failed to save configuration to {config_path}: {e}") from e


def merge_with_env(settings: AgentSettings) -> dict[str, Any]:
    """Merge configuration file settings with environment variable overrides.

    Environment variables take precedence over file settings.
    Returns a dictionary that can be used to update provider configs.

    Args:
        settings: AgentSettings instance from file

    Returns:
        Dictionary of environment variable overrides

    Example:
        >>> settings = load_config()
        >>> env_overrides = merge_with_env(settings)
        >>> # Apply overrides to settings if needed
    """
    env_overrides: dict[str, Any] = {}

    # Note: LLM_PROVIDER is read directly in from_combined(), not via merge
    llm_provider = os.getenv("LLM_PROVIDER")

    # OpenAI overrides
    if os.getenv("OPENAI_API_KEY"):
        env_overrides.setdefault("providers", {}).setdefault("openai", {})["api_key"] = os.getenv(
            "OPENAI_API_KEY"
        )
    if os.getenv("AGENT_MODEL") and llm_provider == "openai":
        env_overrides.setdefault("providers", {}).setdefault("openai", {})["model"] = os.getenv(
            "AGENT_MODEL"
        )

    # Anthropic overrides
    if os.getenv("ANTHROPIC_API_KEY"):
        env_overrides.setdefault("providers", {}).setdefault("anthropic", {})["api_key"] = (
            os.getenv("ANTHROPIC_API_KEY")
        )
    if os.getenv("AGENT_MODEL") and llm_provider == "anthropic":
        env_overrides.setdefault("providers", {}).setdefault("anthropic", {})["model"] = os.getenv(
            "AGENT_MODEL"
        )

    # Azure OpenAI overrides
    if os.getenv("AZURE_OPENAI_ENDPOINT"):
        env_overrides.setdefault("providers", {}).setdefault("azure", {})["endpoint"] = os.getenv(
            "AZURE_OPENAI_ENDPOINT"
        )
    if os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"):
        env_overrides.setdefault("providers", {}).setdefault("azure", {})["deployment"] = os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        )
    if os.getenv("AZURE_OPENAI_API_KEY"):
        env_overrides.setdefault("providers", {}).setdefault("azure", {})["api_key"] = os.getenv(
            "AZURE_OPENAI_API_KEY"
        )
    if os.getenv("AZURE_OPENAI_VERSION"):
        env_overrides.setdefault("providers", {}).setdefault("azure", {})["api_version"] = (
            os.getenv("AZURE_OPENAI_VERSION")
        )

    # Azure AI Foundry overrides
    if os.getenv("AZURE_PROJECT_ENDPOINT"):
        env_overrides.setdefault("providers", {}).setdefault("foundry", {})["project_endpoint"] = (
            os.getenv("AZURE_PROJECT_ENDPOINT")
        )
    if os.getenv("AZURE_MODEL_DEPLOYMENT"):
        env_overrides.setdefault("providers", {}).setdefault("foundry", {})["model_deployment"] = (
            os.getenv("AZURE_MODEL_DEPLOYMENT")
        )

    # Gemini overrides
    if os.getenv("GEMINI_API_KEY"):
        env_overrides.setdefault("providers", {}).setdefault("gemini", {})["api_key"] = os.getenv(
            "GEMINI_API_KEY"
        )
    if os.getenv("GEMINI_PROJECT_ID"):
        env_overrides.setdefault("providers", {}).setdefault("gemini", {})["project_id"] = (
            os.getenv("GEMINI_PROJECT_ID")
        )
    if os.getenv("GEMINI_LOCATION"):
        env_overrides.setdefault("providers", {}).setdefault("gemini", {})["location"] = os.getenv(
            "GEMINI_LOCATION"
        )
    if os.getenv("GEMINI_USE_VERTEXAI"):
        env_overrides.setdefault("providers", {}).setdefault("gemini", {})["use_vertexai"] = (
            os.getenv("GEMINI_USE_VERTEXAI", "false").lower() == "true"
        )
    if os.getenv("AGENT_MODEL") and llm_provider == "gemini":
        env_overrides.setdefault("providers", {}).setdefault("gemini", {})["model"] = os.getenv(
            "AGENT_MODEL"
        )

    # Local provider overrides
    if os.getenv("LOCAL_BASE_URL"):
        env_overrides.setdefault("providers", {}).setdefault("local", {})["base_url"] = os.getenv(
            "LOCAL_BASE_URL"
        )
    if os.getenv("AGENT_MODEL") and llm_provider == "local":
        env_overrides.setdefault("providers", {}).setdefault("local", {})["model"] = os.getenv(
            "AGENT_MODEL"
        )

    # Agent config overrides
    if os.getenv("AGENT_DATA_DIR"):
        env_overrides.setdefault("agent", {})["data_dir"] = os.getenv("AGENT_DATA_DIR")

    # Note: AGENT_SKILLS environment variable removed
    # Skills now configured via settings.skills (plugins, disabled_bundled)

    # Telemetry overrides
    if os.getenv("ENABLE_OTEL"):
        env_overrides.setdefault("telemetry", {})["enabled"] = (
            os.getenv("ENABLE_OTEL", "false").lower() == "true"
        )
    if os.getenv("ENABLE_SENSITIVE_DATA"):
        env_overrides.setdefault("telemetry", {})["enable_sensitive_data"] = (
            os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() == "true"
        )
    if os.getenv("OTLP_ENDPOINT"):
        env_overrides.setdefault("telemetry", {})["otlp_endpoint"] = os.getenv("OTLP_ENDPOINT")
    if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        env_overrides.setdefault("telemetry", {})["applicationinsights_connection_string"] = (
            os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        )

    # Memory overrides
    if os.getenv("MEMORY_ENABLED"):
        env_overrides.setdefault("memory", {})["enabled"] = (
            os.getenv("MEMORY_ENABLED", "true").lower() == "true"
        )
    if os.getenv("MEMORY_TYPE"):
        env_overrides.setdefault("memory", {})["type"] = os.getenv("MEMORY_TYPE")
    if os.getenv("MEMORY_HISTORY_LIMIT"):
        try:
            env_overrides.setdefault("memory", {})["history_limit"] = int(
                os.getenv("MEMORY_HISTORY_LIMIT", "20")
            )
        except ValueError:
            # Invalid value, fallback to default
            env_overrides.setdefault("memory", {})["history_limit"] = 20

    # Mem0 overrides
    if os.getenv("MEM0_STORAGE_PATH"):
        env_overrides.setdefault("memory", {}).setdefault("mem0", {})["storage_path"] = os.getenv(
            "MEM0_STORAGE_PATH"
        )
    if os.getenv("MEM0_API_KEY"):
        env_overrides.setdefault("memory", {}).setdefault("mem0", {})["api_key"] = os.getenv(
            "MEM0_API_KEY"
        )
    if os.getenv("MEM0_ORG_ID"):
        env_overrides.setdefault("memory", {}).setdefault("mem0", {})["org_id"] = os.getenv(
            "MEM0_ORG_ID"
        )
    if os.getenv("MEM0_USER_ID"):
        env_overrides.setdefault("memory", {}).setdefault("mem0", {})["user_id"] = os.getenv(
            "MEM0_USER_ID"
        )
    if os.getenv("MEM0_PROJECT_ID"):
        env_overrides.setdefault("memory", {}).setdefault("mem0", {})["project_id"] = os.getenv(
            "MEM0_PROJECT_ID"
        )

    return env_overrides


def validate_config(settings: AgentSettings) -> list[str]:
    """Validate configuration and return list of errors.

    Args:
        settings: AgentSettings instance to validate

    Returns:
        List of validation error messages (empty if valid)

    Example:
        >>> settings = load_config()
        >>> errors = validate_config(settings)
        >>> if errors:
        ...     print("Configuration errors:", errors)
    """
    return settings.validate_enabled_providers()


def migrate_from_env() -> AgentSettings:
    """Create settings.json from current environment variables.

    Reads current .env file and environment variables, creates a new
    AgentSettings instance with those values.

    Returns:
        AgentSettings instance populated from environment

    Example:
        >>> settings = migrate_from_env()
        >>> save_config(settings)
    """
    from dotenv import load_dotenv

    # Load .env file if it exists
    load_dotenv()

    # Determine which provider is configured
    llm_provider = os.getenv("LLM_PROVIDER", "local")
    agent_model = os.getenv("AGENT_MODEL")

    # Build settings dict
    settings_dict: dict[str, Any] = {
        "version": "1.0",
        "providers": {
            "enabled": [llm_provider],
            "local": {
                "enabled": llm_provider == "local",
                "base_url": os.getenv(
                    "LOCAL_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"
                ),
                "model": agent_model if llm_provider == "local" and agent_model else "ai/phi4",
            },
            "openai": {
                "enabled": llm_provider == "openai",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": agent_model if llm_provider == "openai" and agent_model else "gpt-5-mini",
            },
            "anthropic": {
                "enabled": llm_provider == "anthropic",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "model": (
                    agent_model
                    if llm_provider == "anthropic" and agent_model
                    else "claude-haiku-4-5-20251001"
                ),
            },
            "azure": {
                "enabled": llm_provider == "azure",
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                "api_version": os.getenv("AZURE_OPENAI_VERSION", "2025-03-01-preview"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            },
            "foundry": {
                "enabled": llm_provider == "foundry",
                "project_endpoint": os.getenv("AZURE_PROJECT_ENDPOINT"),
                "model_deployment": os.getenv("AZURE_MODEL_DEPLOYMENT"),
            },
            "gemini": {
                "enabled": llm_provider == "gemini",
                "api_key": os.getenv("GEMINI_API_KEY"),
                "model": (
                    agent_model
                    if llm_provider == "gemini" and agent_model
                    else "gemini-2.0-flash-exp"
                ),
                "use_vertexai": os.getenv("GEMINI_USE_VERTEXAI", "false").lower() == "true",
                "project_id": os.getenv("GEMINI_PROJECT_ID"),
                "location": os.getenv("GEMINI_LOCATION"),
            },
        },
        "agent": {
            "data_dir": os.getenv("AGENT_DATA_DIR", "~/.agent"),
            "log_level": "info",
        },
        "telemetry": {
            "enabled": os.getenv("ENABLE_OTEL", "false").lower() == "true",
            "enable_sensitive_data": os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() == "true",
            "otlp_endpoint": os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
            "applicationinsights_connection_string": os.getenv(
                "APPLICATIONINSIGHTS_CONNECTION_STRING"
            ),
        },
        "memory": {
            "enabled": os.getenv("MEMORY_ENABLED", "true").lower() == "true",
            "type": os.getenv("MEMORY_TYPE", "in_memory"),
            "history_limit": int(os.getenv("MEMORY_HISTORY_LIMIT", "20")),
            "mem0": {
                "storage_path": os.getenv("MEM0_STORAGE_PATH"),
                "api_key": os.getenv("MEM0_API_KEY"),
                "org_id": os.getenv("MEM0_ORG_ID"),
                "user_id": os.getenv("MEM0_USER_ID"),
                "project_id": os.getenv("MEM0_PROJECT_ID"),
            },
        },
    }

    return AgentSettings(**settings_dict)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
