"""Utility functions for mem0 integration.

This module provides helper functions for extracting LLM configuration
from AgentConfig and creating mem0 Memory instances.
"""

import logging
from pathlib import Path
from typing import Any

from agent.config import AgentConfig

logger = logging.getLogger(__name__)

# Providers that mem0 supports
SUPPORTED_PROVIDERS = ["openai", "anthropic", "azure", "gemini"]


def is_provider_compatible(config: AgentConfig) -> tuple[bool, str]:
    """Check if LLM provider is compatible with mem0.

    Args:
        config: Agent configuration with LLM settings

    Returns:
        Tuple of (is_compatible, reason_if_not)

    Example:
        >>> config = AgentConfig(llm_provider="local")
        >>> is_compatible, reason = is_provider_compatible(config)
        >>> # (False, "local provider not supported by mem0")
    """
    if config.llm_provider in SUPPORTED_PROVIDERS:
        return True, ""
    elif config.llm_provider == "local":
        return False, "local provider not supported by mem0 (requires cloud LLM API)"
    elif config.llm_provider == "foundry":
        return False, "foundry provider not yet tested with mem0"
    else:
        return False, f"unknown provider '{config.llm_provider}'"


def extract_llm_config(config: AgentConfig) -> dict[str, Any]:
    """Extract LLM configuration from AgentConfig for mem0.

    Converts agent's LLM configuration to mem0-compatible format,
    enabling mem0 to reuse the same LLM provider and model as the agent.

    Args:
        config: Agent configuration with LLM settings

    Returns:
        Dict with mem0 LLM configuration

    Example:
        >>> config = AgentConfig(llm_provider="openai", openai_api_key="sk-...")
        >>> llm_config = extract_llm_config(config)
        >>> # {"provider": "openai", "config": {"model": "gpt-4o-mini", "api_key": "sk-..."}}
    """
    # Map agent providers to mem0 providers
    if config.llm_provider == "openai":
        return {
            "provider": "openai",
            "config": {
                "model": config.openai_model,
                "api_key": config.openai_api_key,
                "openai_base_url": "https://api.openai.com/v1",  # Force direct OpenAI API
            },
        }

    elif config.llm_provider == "anthropic":
        return {
            "provider": "anthropic",
            "config": {
                "model": config.anthropic_model,
                "api_key": config.anthropic_api_key,
            },
        }

    elif config.llm_provider == "azure":
        return {
            "provider": "azure_openai",
            "config": {
                "model": config.azure_model_deployment or config.openai_model,
                "api_key": config.azure_openai_api_key,
                "azure_endpoint": config.azure_openai_endpoint,
                "api_version": config.azure_openai_api_version or "2024-10-21",
            },
        }

    elif config.llm_provider == "gemini":
        return {
            "provider": "gemini",
            "config": {
                "model": config.gemini_model,
                "api_key": config.gemini_api_key,
            },
        }

    else:
        # Unsupported provider (local, foundry, unknown)
        raise ValueError(
            f"mem0 does not support '{config.llm_provider}' provider. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}. "
            "Use MEMORY_TYPE=in_memory for provider-independent memory."
        )


def get_storage_path(config: AgentConfig) -> Path:
    """Get the storage path for local Chroma database.

    Args:
        config: Agent configuration

    Returns:
        Path to Chroma database directory

    Example:
        >>> path = get_storage_path(config)
        >>> # /Users/daniel/.agent/mem0_data/chroma_db
    """
    if config.mem0_storage_path:
        return config.mem0_storage_path

    # Default to memory_dir/chroma_db
    if config.memory_dir:
        return config.memory_dir / "chroma_db"

    # Fallback to agent_data_dir (should always be set, but handle None gracefully)
    if config.agent_data_dir:
        return config.agent_data_dir / "mem0_data" / "chroma_db"

    # Final fallback to home directory
    return Path.home() / ".agent" / "mem0_data" / "chroma_db"


def create_memory_instance(config: AgentConfig) -> Any:
    """Create mem0 Memory instance with proper configuration.

    Uses Memory.from_config for both local (Chroma) and cloud (mem0.ai) modes,
    ensuring consistent API across both deployment options.

    Args:
        config: Agent configuration with mem0 and LLM settings

    Returns:
        Configured mem0.Memory instance

    Raises:
        ImportError: If mem0ai or chromadb packages not installed
        ValueError: If configuration is invalid

    Example:
        >>> config = AgentConfig.from_env()
        >>> memory = create_memory_instance(config)
    """
    try:
        from mem0 import Memory  # type: ignore[import-untyped]
    except ImportError:
        raise ImportError(
            "mem0ai package not installed. "
            "Install with: uv pip install -e '.[mem0]' (or pip install -e '.[mem0]')"
        )

    # Determine if using cloud or local mode
    is_cloud_mode = bool(config.mem0_api_key and config.mem0_org_id)

    if is_cloud_mode:
        # Cloud mode - use mem0.ai service
        logger.info("Initializing mem0 in cloud mode (mem0.ai)")
        mem0_config = {
            "llm": extract_llm_config(config),
            "vector_store": {
                "provider": "mem0",
                "config": {
                    "api_key": config.mem0_api_key,
                    "org_id": config.mem0_org_id,
                },
            },
        }
    else:
        # Local mode - use Chroma file-based storage
        storage_path = get_storage_path(config)
        logger.info(f"Initializing mem0 in local mode: {storage_path}")

        # Ensure storage directory exists
        storage_path.mkdir(parents=True, exist_ok=True)

        mem0_config = {
            "llm": extract_llm_config(config),
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "path": str(storage_path),
                    "collection_name": "agent_memories",
                },
            },
        }

    try:
        memory = Memory.from_config(mem0_config)
        logger.debug(
            f"mem0 Memory instance created successfully ({'cloud' if is_cloud_mode else 'local'} mode)"
        )
        return memory
    except Exception as e:
        raise ValueError(f"Failed to initialize mem0 Memory: {e}")
