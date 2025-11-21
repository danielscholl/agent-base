"""Unit tests for memory integration with Agent."""

import pytest
from agent_framework import ChatMessage

from agent.agent import Agent
from agent.config.schema import AgentSettings
from agent.memory import InMemoryStore, MemoryManager
from agent.memory.context_provider import MemoryContextProvider


def _create_test_config(memory_enabled=True, memory_type="in_memory"):
    """Helper to create test config with proper API."""
    config = AgentSettings()
    config.providers.enabled = ["openai"]
    config.providers.openai.api_key = "test"
    config.memory.enabled = memory_enabled
    config.memory.type = memory_type
    return config


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.agent
class TestAgentMemoryIntegration:
    """Tests for Agent integration with memory manager."""

    def test_agent_with_memory_disabled_has_no_manager(self, mock_settings, mock_chat_client):
        """Test Agent without memory enabled has no memory manager."""
        config = _create_test_config(memory_enabled=False)

        agent = Agent(settings=config, chat_client=mock_chat_client)

        assert agent.memory_manager is None

    def test_agent_with_memory_enabled_creates_manager(self, mock_chat_client):
        """Test Agent with memory enabled creates memory manager."""
        config = _create_test_config(memory_enabled=True, memory_type="in_memory")

        agent = Agent(settings=config, chat_client=mock_chat_client)

        assert agent.memory_manager is not None
        assert isinstance(agent.memory_manager, MemoryManager)
        assert isinstance(agent.memory_manager, InMemoryStore)

    def test_agent_with_injected_memory_manager(
        self, mock_settings, mock_chat_client, memory_store
    ):
        """Test Agent with injected memory manager."""
        agent = Agent(
            settings=mock_settings,
            chat_client=mock_chat_client,
            memory_manager=memory_store,
        )

        assert agent.memory_manager is memory_store
        assert isinstance(agent.memory_manager, InMemoryStore)

    def test_agent_memory_manager_uses_config(self, mock_chat_client):
        """Test Agent's memory manager uses the config."""
        config = _create_test_config(memory_enabled=True, memory_type="in_memory")

        agent = Agent(settings=config, chat_client=mock_chat_client)

        assert agent.memory_manager.config == config

    def test_agent_with_memory_enabled_and_custom_type(self, mock_chat_client):
        """Test Agent with memory enabled and custom type."""
        config = _create_test_config(memory_enabled=True, memory_type="in_memory")

        agent = Agent(settings=config, chat_client=mock_chat_client)

        assert agent.memory_manager is not None
        assert isinstance(agent.memory_manager, InMemoryStore)

    def test_agent_with_memory_config_defaults_enabled(self, mock_chat_client):
        """Test Agent defaults to memory enabled for conversation context."""
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test"

        agent = Agent(settings=config, chat_client=mock_chat_client)

        assert agent.memory_manager is not None

    def test_agent_memory_manager_priority(self, mock_chat_client, memory_store):
        """Test injected memory manager takes priority over config."""
        config = _create_test_config(memory_enabled=True)

        # But we inject a specific manager
        agent = Agent(settings=config, chat_client=mock_chat_client, memory_manager=memory_store)

        # Should use the injected one
        assert agent.memory_manager is memory_store

    def test_agent_memory_manager_is_none_when_explicitly_injected(self, mock_chat_client):
        """Test Agent memory manager can be explicitly set to None."""
        config = _create_test_config(memory_enabled=True)

        # But we explicitly pass None
        agent = Agent(settings=config, chat_client=mock_chat_client, memory_manager=None)

        # Should create one from config since memory_enabled is True
        assert agent.memory_manager is not None
        assert isinstance(agent.memory_manager, InMemoryStore)

    @pytest.mark.asyncio
    async def test_agent_with_memory_can_add_messages(self, mock_chat_client):
        """Test Agent with memory can add messages."""
        config = _create_test_config(memory_enabled=True)

        agent = Agent(settings=config, chat_client=mock_chat_client)

        # Add messages to memory
        messages = [{"role": "user", "content": "Test message"}]
        result = await agent.memory_manager.add(messages)

        assert result["success"] is True
        assert len(result["result"]) == 1

    @pytest.mark.asyncio
    async def test_agent_with_memory_can_search_messages(self, mock_chat_client):
        """Test Agent with memory can search messages."""
        config = _create_test_config(memory_enabled=True)

        agent = Agent(settings=config, chat_client=mock_chat_client)

        # Add and search
        await agent.memory_manager.add([{"role": "user", "content": "Alice likes Python"}])
        result = await agent.memory_manager.search("Alice")

        assert result["success"] is True
        assert len(result["result"]) == 1

    @pytest.mark.asyncio
    async def test_agent_with_memory_can_clear_messages(self, mock_chat_client):
        """Test Agent with memory can clear messages."""
        config = _create_test_config(memory_enabled=True)

        agent = Agent(settings=config, chat_client=mock_chat_client)

        # Add and clear
        await agent.memory_manager.add([{"role": "user", "content": "Test"}])
        result = await agent.memory_manager.clear()

        assert result["success"] is True
        assert "Cleared 1 memories" in result["message"]

    def test_multiple_agents_have_separate_memory_managers(self, mock_chat_client):
        """Test multiple agents have separate memory managers."""
        config1 = _create_test_config(memory_enabled=True)
        config2 = _create_test_config(memory_enabled=True)

        agent1 = Agent(settings=config1, chat_client=mock_chat_client)
        agent2 = Agent(settings=config2, chat_client=mock_chat_client)

        # Should have different memory manager instances
        assert agent1.memory_manager is not agent2.memory_manager

    @pytest.mark.asyncio
    async def test_multiple_agents_have_independent_memory(self, mock_chat_client):
        """Test multiple agents have independent memory storage."""
        config = _create_test_config(memory_enabled=True)

        agent1 = Agent(settings=config, chat_client=mock_chat_client)
        agent2 = Agent(settings=config, chat_client=mock_chat_client)

        # Add to agent1 memory
        await agent1.memory_manager.add([{"role": "user", "content": "Agent 1 message"}])

        # Agent2 memory should be empty
        result = await agent2.memory_manager.get_all()
        assert len(result["result"]) == 0

    def test_agent_has_memory_manager_attribute(self, mock_chat_client):
        """Test Agent has memory_manager attribute."""
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test"

        agent = Agent(settings=config, chat_client=mock_chat_client)

        assert hasattr(agent, "memory_manager")

    def test_agent_memory_manager_type_annotation(self, mock_chat_client):
        """Test Agent memory_manager accepts Any type."""
        config = _create_test_config(memory_enabled=True)

        # Create agent - should work with Any type for memory_manager
        agent = Agent(settings=config, chat_client=mock_chat_client)

        # Memory manager should be created
        assert agent.memory_manager is not None


@pytest.mark.unit
@pytest.mark.memory
class TestMemoryContextProvider:
    """Tests for MemoryContextProvider integration."""

    @pytest.mark.asyncio
    async def test_context_provider_uses_retrieve_for_context(self, memory_config):
        """Verify ContextProvider calls retrieve_for_context and retrieves relevant memories."""
        store = InMemoryStore(memory_config)
        provider = MemoryContextProvider(store, history_limit=5)

        # Add some memories
        await store.add(
            [
                {"role": "user", "content": "My name is Bob"},
                {"role": "assistant", "content": "Nice to meet you, Bob!"},
                {"role": "user", "content": "I like Python programming"},
                {"role": "assistant", "content": "Python is a great language!"},
            ]
        )

        # Create messages asking about the name
        current_msgs = [ChatMessage(role="user", content="What's my name?")]

        # Call invoking() and verify it retrieves relevant context
        context = await provider.invoking(current_msgs)

        assert context.instructions is not None
        # Should find relevant memory about Bob
        assert "Bob" in context.instructions
        assert "name" in context.instructions.lower()

    @pytest.mark.asyncio
    async def test_context_provider_retrieves_keyword_relevant_memories(self, memory_config):
        """Verify ContextProvider retrieves memories based on keyword matching."""
        store = InMemoryStore(memory_config)
        provider = MemoryContextProvider(store, history_limit=5)

        # Add memories with distinct keywords
        await store.add(
            [
                {"role": "user", "content": "Python is my favorite programming language"},
                {"role": "assistant", "content": "Python is great for many tasks!"},
                {"role": "user", "content": "I also like JavaScript"},
                {"role": "assistant", "content": "JavaScript is versatile!"},
            ]
        )

        # Ask about Python - should retrieve Python-related memories
        current_msgs = [ChatMessage(role="user", content="Tell me about Python")]

        context = await provider.invoking(current_msgs)

        assert context.instructions is not None
        # Should find Python-related memories based on keyword match
        assert "Python" in context.instructions

    @pytest.mark.asyncio
    async def test_context_provider_handles_no_memories(self, memory_config):
        """Verify ContextProvider handles case with no stored memories."""
        store = InMemoryStore(memory_config)
        provider = MemoryContextProvider(store, history_limit=5)

        # No memories stored yet
        current_msgs = [ChatMessage(role="user", content="Hello")]

        context = await provider.invoking(current_msgs)

        # Should return empty context when no memories
        assert context.instructions is None or context.instructions == ""

    @pytest.mark.asyncio
    async def test_context_provider_respects_history_limit(self, memory_config):
        """Verify ContextProvider respects history_limit parameter."""
        store = InMemoryStore(memory_config)
        provider = MemoryContextProvider(store, history_limit=2)

        # Add many memories
        messages = [{"role": "user", "content": f"Python message {i}"} for i in range(10)]
        await store.add(messages)

        # Ask about Python - should limit results
        current_msgs = [ChatMessage(role="user", content="Tell me about Python")]

        context = await provider.invoking(current_msgs)

        assert context.instructions is not None
        # Count number of memory entries in context (should be limited)
        # Each memory appears as "user: Python message N"
        memory_count = context.instructions.count("user:")
        assert memory_count <= 2  # Should respect limit=2
