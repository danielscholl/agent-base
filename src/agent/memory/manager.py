"""Abstract base class for memory managers.

This module defines the interface for memory management operations.
"""

from abc import ABC, abstractmethod
from typing import Any

from agent.config import AgentConfig
from agent.utils.responses import create_error_response, create_success_response


class MemoryManager(ABC):
    """Abstract base class for agent memory management.

    Defines the interface for memory operations that all memory implementations
    must support. Follows the AgentToolset pattern with dependency injection
    and structured responses.

    Example:
        >>> class CustomMemory(MemoryManager):
        ...     async def add(self, messages):
        ...         # Implementation
        ...         return self._create_success_response(result=[], message="Added")
    """

    def __init__(self, config: AgentConfig):
        """Initialize memory manager with configuration.

        Args:
            config: Agent configuration with memory settings
        """
        self.config = config

    @abstractmethod
    async def add(self, messages: list[dict]) -> dict:
        """Add messages to memory storage.

        Args:
            messages: List of message dicts with role and content

        Returns:
            Structured response dict with success status

        Example:
            >>> result = await manager.add([
            ...     {"role": "user", "content": "My name is Alice"}
            ... ])
        """
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> dict:
        """Search memories by keyword query.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            Structured response dict with matching memories

        Example:
            >>> result = await manager.search("Alice", limit=5)
        """
        pass

    @abstractmethod
    async def get_all(self) -> dict:
        """Get all memories from storage.

        Returns:
            Structured response dict with all memories

        Example:
            >>> result = await manager.get_all()
        """
        pass

    @abstractmethod
    async def get_recent(self, limit: int = 10) -> dict:
        """Get recent memories.

        Args:
            limit: Number of recent memories to retrieve

        Returns:
            Structured response dict with recent memories

        Example:
            >>> result = await manager.get_recent(limit=10)
        """
        pass

    @abstractmethod
    async def clear(self) -> dict:
        """Clear all memories from storage.

        Returns:
            Structured response dict with success status

        Example:
            >>> result = await manager.clear()
        """
        pass

    async def retrieve_for_context(self, messages: list[dict], limit: int = 10) -> dict:
        """Retrieve memories relevant for context injection.

        Default implementation extracts query from latest user message and searches,
        falling back to recent memories if no query available. Backends can override
        for optimized semantic retrieval.

        Args:
            messages: Current conversation messages (list of dicts with role/content)
            limit: Maximum number of memories to retrieve

        Returns:
            Structured response dict with relevant memories

        Example:
            >>> result = await manager.retrieve_for_context(
            ...     [{"role": "user", "content": "What's my name?"}],
            ...     limit=5
            ... )

        Note:
            Implementations can use different strategies:
            - InMemoryStore: Keyword-based search from current message
            - Mem0Store: Semantic similarity search (future)
        """
        # Extract query from latest user message
        query = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                query = msg.get("content", "").strip()
                break

        # Search if we have a query, otherwise get recent
        if query:
            return await self.search(query, limit=limit)
        else:
            return await self.get_recent(limit=limit)

    def _create_success_response(self, result: Any, message: str = "") -> dict:
        """Create standardized success response.

        Args:
            result: Operation result
            message: Optional success message

        Returns:
            Structured response dict with success=True
        """
        return create_success_response(result, message)

    def _create_error_response(self, error: str, message: str) -> dict:
        """Create standardized error response.

        Args:
            error: Machine-readable error code
            message: Human-friendly error message

        Returns:
            Structured response dict with success=False
        """
        return create_error_response(error, message)
