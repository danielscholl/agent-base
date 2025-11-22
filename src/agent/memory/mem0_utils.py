"""Utility functions for mem0 integration.

This module provides helper functions for extracting LLM configuration
from AgentConfig and creating mem0 Memory instances.
"""

import logging
import os
from pathlib import Path
from typing import Any

from agent.config.schema import AgentSettings

logger = logging.getLogger(__name__)

# Providers that mem0 supports
SUPPORTED_PROVIDERS = ["openai", "anthropic", "azure", "gemini", "github"]


def is_provider_compatible(config: AgentSettings) -> tuple[bool, str]:
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


def extract_llm_config(config: AgentSettings) -> dict[str, Any]:
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
        # Allow model override for mem0 (e.g., if project has limited model access)
        openai_mem0_model = os.getenv("MEM0_LLM_MODEL", config.openai_model)

        return {
            "provider": "openai",
            "config": {
                "model": openai_mem0_model,
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
        # Azure OpenAI in mem0 doesn't accept azure_endpoint/api_version
        # Use minimal config with just model and api_key
        # Note: This may not work properly - recommend using OpenAI provider instead

        # Check if user has OpenAI API key available
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if openai_api_key:
            # Use OpenAI provider for better compatibility
            # Use MEM0_LLM_MODEL if set, otherwise try agent's OpenAI model if configured,
            # finally fallback to gpt-4o-mini
            azure_mem0_model_override = os.getenv("MEM0_LLM_MODEL")
            if azure_mem0_model_override:
                azure_mem0_model: str = azure_mem0_model_override
            elif config.openai_api_key:
                # Try to use agent's OpenAI model if it's configured
                azure_mem0_model = config.openai_model
            else:
                # Final fallback
                azure_mem0_model = "gpt-4o-mini"

            logger.info(
                f"Using OpenAI provider for mem0 LLM (model: {azure_mem0_model}). "
                "Azure OpenAI will still be used for agent completions."
            )
            return {
                "provider": "openai",
                "config": {
                    "model": azure_mem0_model,
                    "api_key": openai_api_key,
                    "openai_base_url": "https://api.openai.com/v1",
                },
            }
        else:
            # Azure OpenAI support in mem0 is limited
            logger.warning(
                "Azure OpenAI provider not fully supported by mem0. "
                "Set OPENAI_API_KEY environment variable for reliable mem0 operation. "
                "Falling back to InMemoryStore."
            )
            raise ValueError(
                "mem0 does not fully support Azure OpenAI provider. "
                "Set OPENAI_API_KEY environment variable to use mem0 with OpenAI embeddings/LLM, "
                "or use MEMORY_TYPE=in_memory for provider-independent memory."
            )

    elif config.llm_provider == "gemini":
        return {
            "provider": "gemini",
            "config": {
                "model": config.gemini_model,
                "api_key": config.gemini_api_key,
            },
        }

    elif config.llm_provider == "github":
        # GitHub Models uses OpenAI-compatible API
        # Token may be None if using gh CLI authentication, so we need to get it
        from agent.providers.github.auth import get_github_token

        github_token = config.github_token or get_github_token()

        # Construct base URL matching GitHubChatClient behavior
        # Include /inference path and organization scope if configured
        if config.github_org:
            base_url = f"{config.github_endpoint}/orgs/{config.github_org}/inference"
        else:
            base_url = f"{config.github_endpoint}/inference"

        return {
            "provider": "openai",
            "config": {
                "model": config.github_model,
                "api_key": github_token,
                "openai_base_url": base_url,
            },
        }

    else:
        # Unsupported provider (local, foundry, unknown)
        raise ValueError(
            f"mem0 does not support '{config.llm_provider}' provider. "
            f"Supported providers: {', '.join(SUPPORTED_PROVIDERS)}. "
            "Use MEMORY_TYPE=in_memory for provider-independent memory."
        )


def _create_embedder_config(llm_config: dict[str, Any]) -> dict[str, Any]:
    """Create embedder config from LLM config.

    Args:
        llm_config: LLM configuration dict from extract_llm_config()

    Returns:
        Dict with embedder configuration including provider-specific embedding models
    """
    provider: str = str(llm_config["provider"])
    embedder_config: dict[str, Any]

    # Build embedder config with only the parameters needed for embeddings
    # Different from LLM config because embeddings don't use all the same parameters
    if provider == "azure_openai":
        # Azure OpenAI embeddings in mem0 require special handling
        # Check if OpenAI API key is available for embeddings
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if openai_api_key:
            # Use OpenAI for embeddings (mem0 works better with OpenAI embeddings)
            logger.info(
                "Using OpenAI for embeddings (OPENAI_API_KEY found). "
                "Azure OpenAI will still be used for LLM completions."
            )
            embedder_config = {
                "provider": "openai",
                "config": {
                    "model": get_embedding_model(llm_config),
                    "api_key": openai_api_key,
                },
            }
        else:
            # Fall back to trying Azure, but with minimal config
            # This may not work reliably - recommend setting OPENAI_API_KEY
            logger.warning(
                "Azure OpenAI provider selected but OPENAI_API_KEY not found. "
                "mem0 embeddings work best with OpenAI API. "
                "Set OPENAI_API_KEY environment variable for reliable mem0 operation. "
                "Attempting to use Azure embeddings (may fail)..."
            )
            embedder_config = {
                "provider": "openai",  # Use OpenAI provider format
                "config": {
                    "model": get_embedding_model(llm_config),
                    "api_key": llm_config["config"].get("api_key", ""),
                },
            }
    elif provider == "openai":
        # OpenAI embeddings
        embedder_config = {
            "provider": "openai",
            "config": {
                "model": get_embedding_model(llm_config),
                "api_key": llm_config["config"].get("api_key"),
            },
        }
        # Include custom base_url if set (for GitHub Models compatibility)
        if "openai_base_url" in llm_config["config"]:
            embedder_config["config"]["openai_base_url"] = llm_config["config"]["openai_base_url"]
    elif provider == "anthropic":
        # Anthropic uses Voyage embeddings
        embedder_config = {
            "provider": "anthropic",
            "config": {
                "model": get_embedding_model(llm_config),
                "api_key": llm_config["config"].get("api_key"),
            },
        }
    elif provider == "gemini":
        # Gemini embeddings
        embedder_config = {
            "provider": "gemini",
            "config": {
                "model": get_embedding_model(llm_config),
                "api_key": llm_config["config"].get("api_key"),
            },
        }
    else:
        # Default: copy all config but override model
        embedder_config = {
            "provider": provider,
            "config": llm_config["config"].copy(),
        }
        embedder_config["config"]["model"] = get_embedding_model(llm_config)

    return embedder_config


def get_embedding_model(llm_config: dict[str, Any]) -> str:
    """Get the embedding model name for a given LLM configuration.

    Args:
        llm_config: LLM configuration dict from extract_llm_config()

    Returns:
        The embedding model name (without provider suffixes)
    """
    if llm_config["provider"] == "openai":
        return "text-embedding-3-small"
    elif llm_config["provider"] == "anthropic":
        return "voyage-2"
    elif llm_config["provider"] == "azure_openai":
        return "text-embedding-3-small"
    elif llm_config["provider"] == "gemini":
        return "text-embedding-004"
    else:
        # Default for unknown providers
        return "text-embedding-3-small"


def get_storage_path(config: AgentSettings) -> Path:
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
        from pathlib import Path

        return Path(config.mem0_storage_path)

    # Default to memory_dir/chroma_db
    if config.memory_dir:
        return config.memory_dir / "chroma_db"

    # Fallback to agent_data_dir (should always be set, but handle None gracefully)
    if config.agent_data_dir:
        return config.agent_data_dir / "mem0_data" / "chroma_db"

    # Final fallback to home directory
    return Path.home() / ".agent" / "mem0_data" / "chroma_db"


def create_memory_instance(config: AgentSettings) -> Any:
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

        # Extract LLM config
        llm_config = extract_llm_config(config)

        # Create embedder config (reuse LLM provider credentials)
        embedder_config = _create_embedder_config(llm_config)

        mem0_config = {
            "llm": llm_config,
            "embedder": embedder_config,
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

        # Extract LLM config
        llm_config = extract_llm_config(config)

        # Create embedder config (reuse LLM provider credentials)
        # For embeddings, we use the same provider and credentials as the LLM
        embedder_config = _create_embedder_config(llm_config)

        mem0_config = {
            "llm": llm_config,
            "embedder": embedder_config,
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
