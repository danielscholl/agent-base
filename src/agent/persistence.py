"""Thread persistence for Agent.

This module provides functionality to save and load conversation threads,
enabling users to maintain conversation history across sessions.

Adapted from butler-agent for agent-template architecture.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _sanitize_conversation_name(name: str) -> str:
    """Sanitize conversation name to prevent path traversal attacks.

    Args:
        name: User-provided conversation name

    Returns:
        Sanitized name safe for filesystem use

    Raises:
        ValueError: If name is invalid or unsafe

    Example:
        >>> _sanitize_conversation_name("my-session")
        'my-session'
        >>> _sanitize_conversation_name("../etc/passwd")
        ValueError: Invalid conversation name
    """
    # Trim whitespace
    name = name.strip()

    # Check length (1-64 characters)
    if not name or len(name) > 64:
        raise ValueError("Conversation name must be between 1 and 64 characters")

    # Check for valid characters: alphanumeric, underscore, dash, dot
    if not re.match(r"^[A-Za-z0-9._-]+$", name):
        raise ValueError(
            "Conversation name can only contain letters, numbers, underscores, dashes, and dots"
        )

    # Prevent path traversal attempts
    if ".." in name or name.startswith("."):
        raise ValueError("Invalid conversation name: path traversal not allowed")

    # Prevent reserved names
    reserved_names = {"index", "metadata", "con", "prn", "aux", "nul"}
    if name.lower() in reserved_names:
        raise ValueError(f"Reserved name '{name}' cannot be used")

    return name


class ThreadPersistence:
    """Manage conversation thread serialization and storage.

    This class provides thread save/load functionality with:
    - Automatic session directory creation (~/.agent/sessions/)
    - Fallback serialization when framework fails
    - Context summary generation for session resume
    - Session metadata tracking

    Example:
        >>> persistence = ThreadPersistence()
        >>> # Save thread
        >>> await persistence.save_thread(thread, "my-session")
        >>> # Load thread
        >>> thread, context = await persistence.load_thread(agent, "my-session")
    """

    def __init__(self, storage_dir: Path | None = None, memory_dir: Path | None = None):
        """Initialize persistence manager.

        Args:
            storage_dir: Directory for storing conversations
                        (default: ~/.agent/sessions)
            memory_dir: Directory for storing memory state
                       (default: ~/.agent/memory)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".agent" / "sessions"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Memory directory
        if memory_dir is None:
            memory_dir = Path.home() / ".agent" / "memory"
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file tracks all conversations
        self.metadata_file = self.storage_dir / "index.json"
        self._load_metadata()

        logger.debug(f"Thread persistence initialized: {self.storage_dir}")
        logger.debug(f"Memory persistence initialized: {self.memory_dir}")

    def _load_metadata(self) -> None:
        """Load conversation metadata index."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata, starting fresh: {e}")
                self.metadata = {"conversations": {}}
        else:
            self.metadata = {"conversations": {}}
            # Create initial metadata file
            self._save_metadata()

    def _save_metadata(self) -> None:
        """Save conversation metadata index."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise

    def _generate_context_summary(self, messages: list[dict]) -> str:
        """Generate a concise context summary from message history.

        Args:
            messages: List of message dicts with role and content

        Returns:
            Context summary string for AI

        Example:
            >>> messages = [{"role": "user", "content": "Hello"}]
            >>> summary = persistence._generate_context_summary(messages)
            >>> "resuming" in summary.lower()
            True
        """
        if not messages:
            return "Empty session - no previous context."

        summary_parts = ["You are resuming a previous session. Here's what happened:\n"]

        # Track key information
        user_requests = []
        tools_called = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                user_requests.append(content[:200])  # Truncate long messages

            # Track tool calls
            if "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    tools_called.append(tc.get("name", "unknown"))

        # Build summary
        if user_requests:
            summary_parts.append("User requests:")
            for i, req in enumerate(user_requests[:5], 1):  # Max 5
                summary_parts.append(f"{i}. {req}")
            summary_parts.append("")

        if tools_called:
            summary_parts.append(f"Tools used: {', '.join(set(tools_called))}")

        summary_parts.append(f"\nTotal conversation: {len(messages)} messages exchanged.")
        summary_parts.append(
            "\nPlease continue helping the user based on this context. "
            "If the user asks about previous actions, you can reference the above."
        )

        return "\n".join(summary_parts)

    async def _fallback_serialize(self, thread: Any) -> dict:
        """Fallback serialization when thread.serialize() fails.

        Manually extracts messages and converts them to JSON-serializable format.

        Args:
            thread: AgentThread to serialize

        Returns:
            Dictionary with serialized thread data
        """
        messages_data = []

        # Extract messages from message_store (Agent Framework pattern)
        messages = []
        if hasattr(thread, "message_store") and thread.message_store:
            try:
                messages = await thread.message_store.list_messages()
                logger.debug(f"Extracted {len(messages)} messages from message_store")
            except Exception as e:
                logger.warning(f"Failed to list messages from store: {e}")

        if messages:
            for msg in messages:
                # Extract role (might be a Role enum object, convert to string)
                role = getattr(msg, "role", "unknown")
                msg_dict: dict[str, Any] = {"role": str(role) if role else "unknown"}

                # Extract message content
                if hasattr(msg, "text"):
                    msg_dict["content"] = str(msg.text)
                elif hasattr(msg, "content"):
                    # Content can be string or list of content blocks
                    content = msg.content
                    if isinstance(content, str):
                        msg_dict["content"] = content
                    elif isinstance(content, list):
                        # Join content blocks
                        msg_dict["content"] = " ".join(str(block) for block in content)
                    else:
                        msg_dict["content"] = str(content)
                else:
                    msg_dict["content"] = str(msg)

                # Extract tool calls if present
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_calls_data = []
                    for tc in msg.tool_calls:
                        tool_call = {
                            "name": str(getattr(tc, "name", "unknown")),
                            "arguments": str(getattr(tc, "arguments", "")),
                        }
                        tool_calls_data.append(tool_call)
                    msg_dict["tool_calls"] = tool_calls_data

                messages_data.append(msg_dict)

        return {
            "messages": messages_data,
            "metadata": {"fallback": True, "version": "1.0"},
        }

    async def save_thread(
        self,
        thread: Any,
        name: str,
        description: str | None = None,
        messages: list[dict] | None = None,
    ) -> Path:
        """Save a conversation thread.

        Args:
            thread: AgentThread to serialize (can be None for providers without thread support)
            name: Name for this conversation
            description: Optional description
            messages: Optional list of message dicts for manual tracking
                     (used when thread is None or doesn't support serialization)

        Returns:
            Path to saved conversation file

        Raises:
            ValueError: If name is invalid or unsafe
            Exception: If serialization or save fails

        Example:
            >>> persistence = ThreadPersistence()
            >>> path = await persistence.save_thread(thread, "session-1")
            >>> path.exists()
            True
        """
        # Sanitize name for security
        safe_name = _sanitize_conversation_name(name)
        logger.info(f"Saving conversation '{safe_name}'...")

        # Extract first message for preview
        first_message = ""
        message_count = 0
        if hasattr(thread, "message_store") and thread.message_store:
            try:
                messages = await thread.message_store.list_messages()
                if messages is not None:
                    message_count = len(messages)

                    # Try to get first user message
                    for msg in messages:
                        if hasattr(msg, "role") and str(msg.role) == "user":
                            if hasattr(msg, "text"):
                                first_message = str(msg.text)[:100]
                            elif hasattr(msg, "content"):
                                content = msg.content
                                if isinstance(content, str):
                                    first_message = content[:100]
                                else:
                                    first_message = str(content)[:100]
                            break
            except Exception as e:
                logger.warning(f"Failed to extract first message: {e}")

        # Serialize thread
        serialized = None
        try:
            # Try framework serialization first
            if thread and hasattr(thread, "serialize"):
                serialized = await thread.serialize()
                logger.debug("Used framework serialization")
        except Exception as e:
            logger.warning(f"Framework serialization failed: {e}, using fallback")

        # Fallback to manual serialization if needed
        if serialized is None:
            # Use provided messages if available, otherwise extract from thread
            if messages:
                logger.debug(
                    f"Using manually tracked messages for fallback serialization ({len(messages)} messages)"
                )
                serialized = {
                    "messages": messages,
                    "metadata": {"fallback": True, "version": "1.0", "manual_tracking": True},
                }
            else:
                serialized = await self._fallback_serialize(thread)
                logger.debug("Used fallback serialization from thread")

        # Build conversation data
        conversation_data = {
            "name": safe_name,
            "description": description or "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": message_count,
            "first_message": first_message,
            "thread": serialized,
        }

        # Save to file
        file_path = self.storage_dir / f"{safe_name}.json"
        with open(file_path, "w") as f:
            json.dump(conversation_data, f, indent=2)

        # Update metadata
        self.metadata["conversations"][safe_name] = {
            "name": safe_name,
            "description": description or "",
            "created_at": conversation_data["created_at"],
            "updated_at": conversation_data["updated_at"],
            "message_count": message_count,
            "first_message": first_message,
        }
        self._save_metadata()

        logger.info(f"Saved conversation to {file_path}")
        return file_path

    async def load_thread(
        self, agent: Any, name: str, show_history: bool = True
    ) -> tuple[Any, str | None]:
        """Load a conversation thread.

        Args:
            agent: Agent instance to create new thread
            name: Name of conversation to load
            show_history: Whether to display conversation history (default: True)

        Returns:
            Tuple of (thread, context_summary)
            - thread: Loaded or new thread
            - context_summary: Summary for AI if using fallback, None otherwise

        Raises:
            FileNotFoundError: If conversation doesn't exist
            Exception: If deserialization fails

        Example:
            >>> thread, context = await persistence.load_thread(agent, "session-1")
            >>> thread is not None
            True
        """
        safe_name = _sanitize_conversation_name(name)
        file_path = self.storage_dir / f"{safe_name}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Conversation '{safe_name}' not found")

        logger.info(f"Loading conversation '{safe_name}'...")

        with open(file_path) as f:
            data = json.load(f)

        thread_data = data["thread"]

        # Extract messages for context (may or may not display)
        messages = thread_data.get("messages", [])

        # Display conversation history only if requested
        # When memory is enabled, we suppress this since memory handles context
        if show_history and messages:
            from rich.console import Console
            from rich.markdown import Markdown

            console = Console()

            # Small header to indicate resuming (subtle, not intrusive)
            console.print(
                f"\n[dim italic]Resuming session ({len(messages)} messages)[/dim italic]\n"
            )

            # Display in the same format as live conversation for consistency
            for _i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if role == "user":
                    # Match the prompt format exactly: > user_message
                    console.print(f"> {content}")
                    console.print()  # Blank line after user input (like live conversation)
                elif role == "assistant":
                    # Match the agent response format (markdown rendering, no label)
                    console.print(Markdown(content))
                    # Don't add blank line - let CLI handle spacing

        # Check if fallback serialization was used
        if thread_data.get("metadata", {}).get("fallback"):
            logger.info("Loading fallback-serialized session")

            # Generate context summary for AI
            context_summary = self._generate_context_summary(messages)

            # Create new thread (can't deserialize fallback format)
            thread = (
                agent.chat_client.create_thread()
                if hasattr(agent.chat_client, "create_thread")
                else None
            )

            return thread, context_summary
        else:
            # Try framework deserialization
            try:
                if hasattr(agent.chat_client, "deserialize_thread"):
                    thread = await agent.chat_client.deserialize_thread(thread_data)
                    logger.info("Successfully deserialized thread using framework")
                    # Thread has full context, no summary needed
                    return thread, None
                else:
                    # Framework doesn't support deserialization, use fallback
                    logger.warning("Framework doesn't support deserialization, using fallback")
                    context_summary = self._generate_context_summary(messages)
                    thread = (
                        agent.chat_client.create_thread()
                        if hasattr(agent.chat_client, "create_thread")
                        else None
                    )
                    return thread, context_summary
            except Exception as e:
                logger.error(f"Deserialization failed: {e}, using fallback")
                context_summary = self._generate_context_summary(messages)
                thread = (
                    agent.chat_client.create_thread()
                    if hasattr(agent.chat_client, "create_thread")
                    else None
                )
                return thread, context_summary

    def list_sessions(self) -> list[dict]:
        """List all saved conversation sessions.

        Returns:
            List of session metadata dicts

        Example:
            >>> sessions = persistence.list_sessions()
            >>> all("name" in s for s in sessions)
            True
        """
        return list(self.metadata.get("conversations", {}).values())

    def delete_session(self, name: str) -> None:
        """Delete a conversation session.

        Args:
            name: Name of session to delete

        Raises:
            FileNotFoundError: If session doesn't exist

        Example:
            >>> persistence.delete_session("session-1")
        """
        safe_name = _sanitize_conversation_name(name)
        file_path = self.storage_dir / f"{safe_name}.json"

        if not file_path.exists():
            raise FileNotFoundError(f"Session '{safe_name}' not found")

        # Delete file
        file_path.unlink()

        # Remove from metadata
        if safe_name in self.metadata.get("conversations", {}):
            del self.metadata["conversations"][safe_name]
            self._save_metadata()

        logger.info(f"Deleted session '{safe_name}'")

    async def save_memory_state(self, session_name: str, memory_data: list[dict]) -> Path:
        """Save memory state for a session.

        Args:
            session_name: Name of the session
            memory_data: List of memory entries to save

        Returns:
            Path to saved memory file

        Raises:
            ValueError: If session_name is invalid

        Example:
            >>> memories = [{"role": "user", "content": "Hello"}]
            >>> path = await persistence.save_memory_state("session-1", memories)
        """
        from agent.memory.persistence import MemoryPersistence

        safe_name = _sanitize_conversation_name(session_name)
        memory_persistence = MemoryPersistence(storage_dir=self.memory_dir)

        # Get memory file path
        memory_path = memory_persistence.get_memory_path(safe_name)

        # Save memory state
        await memory_persistence.save(memory_data, memory_path)

        # Update session metadata to track memory
        if safe_name in self.metadata.get("conversations", {}):
            self.metadata["conversations"][safe_name]["has_memory"] = True
            self.metadata["conversations"][safe_name]["memory_count"] = len(memory_data)
            self._save_metadata()

        return memory_path

    async def load_memory_state(self, session_name: str) -> list[dict] | None:
        """Load memory state for a session.

        Args:
            session_name: Name of the session

        Returns:
            List of memory entries or None if no memory exists

        Raises:
            ValueError: If session_name is invalid

        Example:
            >>> memories = await persistence.load_memory_state("session-1")
        """
        from agent.memory.persistence import MemoryPersistence

        safe_name = _sanitize_conversation_name(session_name)
        memory_persistence = MemoryPersistence(storage_dir=self.memory_dir)

        # Get memory file path
        memory_path = memory_persistence.get_memory_path(safe_name)

        # Load memory state
        return await memory_persistence.load(memory_path)
