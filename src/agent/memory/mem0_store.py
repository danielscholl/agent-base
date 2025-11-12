"""Mem0-based semantic memory storage implementation.

This module provides semantic memory storage using mem0's Python library
with support for local Chroma storage and cloud mem0.ai service.
"""

import asyncio
import logging
import re
from datetime import UTC, datetime

from agent.config import AgentConfig
from agent.memory.manager import MemoryManager
from agent.memory.mem0_utils import create_memory_instance

logger = logging.getLogger(__name__)

# Patterns for detecting sensitive data (API keys, tokens, passwords)
SENSITIVE_PATTERNS = [
    re.compile(r"sk[-_][a-zA-Z0-9_]{20,}", re.IGNORECASE),  # API keys (sk_...)
    re.compile(r"bearer\s+[a-zA-Z0-9\-._~+/]+=*", re.IGNORECASE),  # Bearer tokens
    re.compile(r'api[_-]?key["\s:=]+[a-zA-Z0-9\-._~+/]+', re.IGNORECASE),  # API key assignments
    re.compile(r'token["\s:=]+[a-zA-Z0-9\-._~+/]{20,}', re.IGNORECASE),  # Token assignments
    re.compile(r'password["\s:=]+\S+', re.IGNORECASE),  # Password assignments
]


class Mem0Store(MemoryManager):
    """Semantic memory storage using mem0 Python library.

    Integrates mem0 directly into the agent process, reusing the agent's
    existing LLM configuration. Supports local Chroma storage or cloud mem0.ai.

    Attributes:
        config: Agent configuration with mem0 settings
        memory: mem0.Memory instance
        user_id: User namespace for memory isolation
        namespace: Combined user:project namespace

    Example:
        >>> config = AgentConfig.from_env()
        >>> store = Mem0Store(config)
        >>> await store.add([{"role": "user", "content": "My name is Alice"}])
    """

    def __init__(self, config: AgentConfig):
        """Initialize mem0 store with configuration.

        Args:
            config: Agent configuration with mem0 settings

        Raises:
            ValueError: If mem0 configuration is invalid
            ImportError: If mem0ai or chromadb not installed
        """
        super().__init__(config)

        try:
            self.memory = create_memory_instance(config)
            logger.info("Mem0Store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0Store: {e}")
            raise

        # Set up namespacing for user/project isolation
        self.user_id = config.mem0_user_id or "default-user"

        # Build namespace (user:project or just user)
        if config.mem0_project_id:
            self.namespace = f"{self.user_id}:{config.mem0_project_id}"
        else:
            self.namespace = self.user_id

        logger.debug(f"Mem0Store namespace: {self.namespace}")

    def _scrub_sensitive_content(self, content: str) -> tuple[str, bool]:
        """Scrub potential secrets from content before storage.

        Args:
            content: Message content to check

        Returns:
            Tuple of (scrubbed_content, was_modified)
        """
        modified = False

        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(content):
                content = pattern.sub("[REDACTED]", content)
                modified = True

        if modified:
            logger.warning("Detected and redacted potential secrets from content")

        return content, modified

    def _should_save_message(self, msg: dict) -> bool:
        """Check if message should be saved to memory.

        Implements safety gates to prevent storing sensitive data.

        Args:
            msg: Message dict with role, content, and optional metadata

        Returns:
            True if message should be saved, False otherwise
        """
        # Check for explicit opt-out
        metadata = msg.get("metadata", {})
        if metadata.get("save") is False:
            logger.debug(f"Skipping message with save=false: {msg.get('role')}")
            return False

        # Check for explicit opt-in (overrides filters)
        if metadata.get("force_save") is True:
            return True

        # Default: only save user and assistant messages
        role = msg.get("role", "")
        return role in ("user", "assistant")

    async def add(self, messages: list[dict]) -> dict:
        """Add messages to mem0 storage with semantic indexing.

        Messages are automatically indexed with vector embeddings and
        entity extraction for semantic search.

        Args:
            messages: List of message dicts with role and content

        Returns:
            Structured response dict with success status

        Example:
            >>> await store.add([
            ...     {"role": "user", "content": "My name is Alice"},
            ...     {"role": "assistant", "content": "Nice to meet you, Alice!"}
            ... ])
        """
        if not messages:
            return self._create_error_response(
                error="invalid_input", message="No messages provided"
            )

        try:
            # Filter and prepare messages
            messages_to_add = []
            for msg in messages:
                # Validate message structure
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    logger.warning(f"Skipping invalid message: {msg}")
                    continue

                # Apply safety gates
                if not self._should_save_message(msg):
                    continue

                content = msg.get("content", "").strip()
                if not content:
                    continue

                # Scrub sensitive content
                scrubbed_content, was_scrubbed = self._scrub_sensitive_content(content)

                messages_to_add.append({"role": msg["role"], "content": scrubbed_content})

            if not messages_to_add:
                return self._create_success_response(
                    result=[], message="No messages to add after filtering"
                )

            # Add to mem0 (wrapped to avoid blocking event loop)
            await asyncio.to_thread(
                self.memory.add, messages=messages_to_add, user_id=self.namespace
            )

            logger.debug(f"Added {len(messages_to_add)} messages to mem0")

            return self._create_success_response(
                result=messages_to_add, message=f"Added {len(messages_to_add)} messages to memory"
            )

        except Exception as e:
            logger.error(f"Error adding messages to mem0: {e}", exc_info=True)
            return self._create_error_response(
                error="storage_error", message=f"Failed to add messages: {str(e)}"
            )

    async def search(self, query: str, limit: int = 5) -> dict:
        """Search memories by semantic similarity.

        Uses vector embeddings to find semantically similar memories,
        not just keyword matches.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            Structured response dict with matching memories

        Example:
            >>> result = await store.search("authentication errors", limit=5)
            >>> # Will also find memories about "login failures"
        """
        if not query or not query.strip():
            return self._create_error_response(
                error="invalid_query", message="Search query cannot be empty"
            )

        try:
            # Search mem0 with semantic similarity
            results = await asyncio.to_thread(
                self.memory.search, query=query, user_id=self.namespace, limit=limit
            )

            # Convert mem0 results to standardized format
            memories = []
            if results and "results" in results:
                for result in results["results"]:
                    memory = {
                        "id": result.get("id") or result.get("memory_id"),
                        "role": "assistant",  # mem0 doesn't store role separately
                        "content": result.get("memory", ""),
                        "timestamp": result.get("created_at") or result.get("updated_at", ""),
                        "metadata": result.get("metadata", {}),
                        "score": result.get("score"),  # Semantic similarity score
                    }
                    memories.append(memory)

            logger.debug(f"Search for '{query}' returned {len(memories)} results")

            return self._create_success_response(
                result=memories,
                message=f"Found {len(memories)} matching memories for query: {query}",
            )

        except Exception as e:
            logger.error(f"Error searching mem0: {e}", exc_info=True)
            return self._create_error_response(
                error="search_error", message=f"Failed to search memories: {str(e)}"
            )

    async def get_all(self) -> dict:
        """Get all memories from storage for current namespace.

        Returns:
            Structured response dict with all memories
        """
        try:
            # Get all memories for user
            results = await asyncio.to_thread(self.memory.get_all, user_id=self.namespace)

            memories = []
            if results and "results" in results:
                for result in results["results"]:
                    memory = {
                        "id": result.get("id") or result.get("memory_id"),
                        "role": "assistant",
                        "content": result.get("memory", ""),
                        "timestamp": result.get("created_at") or result.get("updated_at", ""),
                        "metadata": result.get("metadata", {}),
                    }
                    memories.append(memory)

            return self._create_success_response(result=memories, message="Retrieved all memories")

        except Exception as e:
            logger.error(f"Error retrieving all memories from mem0: {e}", exc_info=True)
            return self._create_error_response(
                error="retrieval_error", message=f"Failed to retrieve memories: {str(e)}"
            )

    async def get_recent(self, limit: int = 10) -> dict:
        """Get recent memories.

        Args:
            limit: Number of recent memories to retrieve

        Returns:
            Structured response dict with recent memories
        """
        try:
            # Get all and sort by timestamp
            all_result = await self.get_all()

            if not all_result.get("success"):
                return all_result

            memories = all_result["result"]

            # Sort by timestamp (most recent first) with proper datetime parsing
            def parse_timestamp(memory: dict) -> datetime:
                """Parse timestamp with fallback to epoch."""
                timestamp_str = memory.get("timestamp", "")
                try:
                    # Try parsing ISO format
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    # Ensure timezone-aware for comparison
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    return dt
                except (ValueError, AttributeError):
                    # Fallback to epoch (oldest possible time) in UTC
                    return datetime.min.replace(tzinfo=UTC)

            sorted_memories = sorted(memories, key=parse_timestamp, reverse=True)

            # Take most recent N
            recent = sorted_memories[:limit]

            return self._create_success_response(
                result=recent, message=f"Retrieved {len(recent)} recent memories"
            )

        except Exception as e:
            logger.error(f"Error retrieving recent memories: {e}", exc_info=True)
            return self._create_error_response(
                error="retrieval_error", message=f"Failed to retrieve recent memories: {str(e)}"
            )

    async def clear(self) -> dict:
        """Clear all memories from storage for current namespace.

        Returns:
            Structured response dict with success status
        """
        try:
            # Delete all memories for user
            await asyncio.to_thread(self.memory.delete_all, user_id=self.namespace)

            logger.info(f"Cleared all memories for namespace: {self.namespace}")

            return self._create_success_response(
                result=None, message=f"Cleared all memories for namespace: {self.namespace}"
            )

        except Exception as e:
            logger.error(f"Error clearing mem0 memories: {e}", exc_info=True)
            return self._create_error_response(
                error="clear_error", message=f"Failed to clear memories: {str(e)}"
            )

    async def retrieve_for_context(self, messages: list[dict], limit: int = 10) -> dict:
        """Retrieve semantically relevant memories for context injection.

        Overrides default implementation to use mem0's semantic search
        for better relevance matching.

        Args:
            messages: Current conversation messages
            limit: Maximum number of memories to retrieve

        Returns:
            Structured response dict with relevant memories
        """
        # Extract query from latest user message
        query = None
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                query = msg.get("content", "").strip()
                break

        # Use semantic search if we have a query
        if query:
            logger.debug(f"Using semantic search for context: {query[:50]}...")
            return await self.search(query, limit=limit)
        else:
            # Fall back to recent memories
            logger.debug("No query found, using recent memories for context")
            return await self.get_recent(limit=limit)
