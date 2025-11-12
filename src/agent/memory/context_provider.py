"""Memory context provider for Agent Framework integration.

This module provides a ContextProvider that manages conversation memory,
injecting relevant memories before LLM calls and storing new messages after.
"""

import logging
from collections.abc import MutableSequence, Sequence
from typing import Any

from agent_framework import ChatMessage, Context, ContextProvider

logger = logging.getLogger(__name__)


class MemoryContextProvider(ContextProvider):
    """Manage conversation memory using Agent Framework's ContextProvider pattern.

    This context provider:
    - Injects relevant memories before LLM calls (via invoking())
    - Stores new messages after LLM responds (via invoked())
    - Provides conversation history for context continuity

    Example:
        >>> memory_manager = InMemoryStore(config)
        >>> provider = MemoryContextProvider(memory_manager)
        >>> agent = chat_client.create_agent(
        ...     name="Agent",
        ...     instructions="...",
        ...     context_providers=[provider]
        ... )
    """

    def __init__(self, memory_manager: Any, history_limit: int = 20):
        """Initialize context provider with memory manager.

        Args:
            memory_manager: MemoryManager instance for storage/retrieval
            history_limit: Maximum number of memories to inject as context (default: 20)
        """
        self.memory_manager = memory_manager
        self.history_limit = history_limit
        logger.debug("MemoryContextProvider initialized")

    async def invoking(
        self, messages: ChatMessage | MutableSequence[ChatMessage], **kwargs: Any
    ) -> Context:
        """Inject relevant memories before agent invocation.

        Retrieves relevant conversation history from memory using semantic/keyword
        search and injects it as context instructions for the LLM.

        Args:
            messages: Current conversation messages
            **kwargs: Additional context

        Returns:
            Context with conversation history instructions
        """
        try:
            # Convert ChatMessage to dict format for memory manager
            messages_dicts = []
            msg_list = messages if isinstance(messages, MutableSequence) else [messages]
            for msg in msg_list:
                text = self._get_message_text(msg)
                if text:
                    messages_dicts.append(
                        {"role": str(getattr(msg, "role", "user")), "content": text}
                    )

            # Retrieve relevant memories using new method
            result = await self.memory_manager.retrieve_for_context(
                messages_dicts, limit=self.history_limit
            )

            if result.get("success") and result["result"]:
                memories = result["result"]
                logger.debug(f"Injecting {len(memories)} relevant memories into context")

                # Build context from relevant memories
                context_parts = ["Previous conversation history:"]
                for mem in memories:
                    role = mem.get("role", "unknown")
                    content = mem.get("content", "")
                    context_parts.append(f"{role}: {content}")

                context_text = "\n".join(context_parts)
                logger.debug(f"Memory context: {context_text[:200]}...")

                return Context(instructions=context_text)
            else:
                logger.debug("No relevant memories to inject")
                return Context()

        except Exception as e:
            logger.error(f"Error retrieving memories for context: {e}", exc_info=True)
            return Context()

    async def invoked(
        self,
        request_messages: ChatMessage | Sequence[ChatMessage],
        response_messages: ChatMessage | Sequence[ChatMessage] | None = None,
        invoke_exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Store conversation messages after agent invocation.

        Captures both user messages and assistant responses to build
        complete conversation history.

        Args:
            request_messages: Messages sent to the agent
            response_messages: Messages returned by the agent
            invoke_exception: Exception if call failed
            **kwargs: Additional context
        """
        try:
            # Convert to lists for easier processing
            if isinstance(request_messages, ChatMessage):
                request_messages = [request_messages]
            if isinstance(response_messages, ChatMessage):
                response_messages = [response_messages]

            messages_to_store = []

            # Extract user messages
            for msg in request_messages:
                text = self._get_message_text(msg)
                if text:
                    messages_to_store.append(
                        {"role": str(getattr(msg, "role", "user")), "content": text}
                    )

            # Extract assistant responses
            if response_messages:
                for msg in response_messages:
                    text = self._get_message_text(msg)
                    if text:
                        messages_to_store.append(
                            {"role": str(getattr(msg, "role", "assistant")), "content": text}
                        )

            # Store in memory
            if messages_to_store:
                result = await self.memory_manager.add(messages_to_store)
                if result.get("success"):
                    logger.debug(f"Stored {len(messages_to_store)} messages in memory")
                else:
                    logger.warning(f"Failed to store messages: {result.get('message')}")
            else:
                logger.debug("No messages to store")

        except Exception as e:
            logger.error(f"Error storing messages in memory: {e}", exc_info=True)

    def _get_message_text(self, msg: ChatMessage) -> str:
        """Extract text from a ChatMessage.

        Args:
            msg: Chat message

        Returns:
            Message text or empty string
        """
        # Try different attributes the message might have
        if hasattr(msg, "text"):
            return str(msg.text)
        elif hasattr(msg, "content"):
            content = msg.content
            if isinstance(content, str):
                return content
            else:
                return str(content)
        else:
            return str(msg) if msg else ""

    # Note: Serialization is handled by ThreadPersistence.save_memory_state()
    # and MemoryPersistence, not by this ContextProvider.
    # The provider is stateless and just wraps the memory_manager.
