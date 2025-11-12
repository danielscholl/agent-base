"""Memory management for Agent conversations.

This module provides in-memory and semantic (mem0) storage capabilities for
maintaining conversation context across multiple interactions, enabling agents
to remember preferences, recall previous conversations, and provide personalized
experiences.

Key Components:
    - MemoryManager: Abstract base class for memory operations
    - InMemoryStore: In-memory implementation with keyword search
    - Mem0Store: Semantic memory with vector-based search (optional)
    - MemoryPersistence: Serialization and persistence utilities

Example:
    >>> from agent.memory import create_memory_manager
    >>> memory = create_memory_manager(config)
    >>> await memory.add([{"role": "user", "content": "Hello"}])
"""

import logging
from typing import TYPE_CHECKING

from agent.memory.context_provider import MemoryContextProvider
from agent.memory.manager import MemoryManager
from agent.memory.store import InMemoryStore

# Conditional import for optional mem0 dependency
try:
    from agent.memory.mem0_store import Mem0Store
except ImportError:
    # mem0 not available, but that's okay - it's optional
    pass

if TYPE_CHECKING:
    from agent.config import AgentConfig

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryManager",
    "InMemoryStore",
    "MemoryContextProvider",
    "create_memory_manager",
]

# Only export Mem0Store if it's available
try:
    from agent.memory.mem0_store import Mem0Store  # noqa: F401

    __all__.append("Mem0Store")
except ImportError:
    # Mem0Store is optional; ignore if mem0ai package not installed
    pass


def create_memory_manager(config: "AgentConfig") -> MemoryManager:
    """Factory function to create memory manager based on config.

    Routes to appropriate memory backend based on config.memory_type:
    - "in_memory": InMemoryStore (keyword search, ephemeral)
    - "mem0": Mem0Store (semantic search, persistent)

    Falls back to InMemoryStore if mem0 initialization fails or provider is incompatible.

    Args:
        config: AgentConfig instance with memory settings

    Returns:
        MemoryManager instance

    Example:
        >>> config = AgentConfig(memory_enabled=True, memory_type="mem0")
        >>> manager = create_memory_manager(config)
    """
    if config.memory_type == "mem0":
        # Check provider compatibility first
        try:
            from agent.memory.mem0_utils import is_provider_compatible

            is_compatible, reason = is_provider_compatible(config)
            if not is_compatible:
                logger.warning(
                    f"mem0 not available: {reason}. "
                    f"Falling back to InMemoryStore. "
                    f"To use mem0, switch to a supported provider (openai, anthropic, azure, gemini)."
                )
                return InMemoryStore(config)
        except ImportError:
            # mem0_utils not available, continue and let Mem0Store import fail
            pass

        try:
            # Lazy import to avoid dependency if not using mem0
            from agent.memory.mem0_store import Mem0Store

            logger.info("Creating Mem0Store for semantic memory")
            return Mem0Store(config)
        except Exception as e:
            logger.warning(
                f"Failed to initialize Mem0Store: {e}. "
                "Falling back to InMemoryStore. "
                "Ensure mem0ai package is installed: uv pip install -e '.[mem0]'"
            )
            # Fall back to InMemoryStore
            return InMemoryStore(config)
    else:
        # Default to InMemoryStore
        logger.debug(f"Creating InMemoryStore for memory type: {config.memory_type}")
        return InMemoryStore(config)
