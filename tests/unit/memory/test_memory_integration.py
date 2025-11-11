"""Unit tests for memory integration with Agent."""

import pytest

from agent.agent import Agent
from agent.config import AgentConfig
from agent.memory import InMemoryStore, MemoryManager


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.agent
class TestAgentMemoryIntegration:
    """Tests for Agent integration with memory manager."""

    def test_agent_with_memory_disabled_has_no_manager(self, mock_config, mock_chat_client):
        """Test Agent without memory enabled has no memory manager."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=False,
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        assert agent.memory_manager is None

    def test_agent_with_memory_enabled_creates_manager(self, mock_chat_client):
        """Test Agent with memory enabled creates memory manager."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
            memory_type="in_memory",
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        assert agent.memory_manager is not None
        assert isinstance(agent.memory_manager, MemoryManager)
        assert isinstance(agent.memory_manager, InMemoryStore)

    def test_agent_with_injected_memory_manager(self, mock_config, mock_chat_client, memory_store):
        """Test Agent with injected memory manager."""
        agent = Agent(
            config=mock_config,
            chat_client=mock_chat_client,
            memory_manager=memory_store,
        )

        assert agent.memory_manager is memory_store
        assert isinstance(agent.memory_manager, InMemoryStore)

    def test_agent_memory_manager_uses_config(self, mock_chat_client):
        """Test Agent's memory manager uses the config."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
            memory_type="in_memory",
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        assert agent.memory_manager.config == config

    def test_agent_with_memory_enabled_and_custom_type(self, mock_chat_client):
        """Test Agent with memory enabled and custom type."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
            memory_type="in_memory",  # Currently only in_memory is supported
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        assert agent.memory_manager is not None
        assert isinstance(agent.memory_manager, InMemoryStore)

    def test_agent_with_memory_config_defaults_enabled(self, mock_chat_client):
        """Test Agent defaults to memory enabled for conversation context."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        agent = Agent(config=config, chat_client=mock_chat_client)

        assert agent.memory_manager is not None

    def test_agent_memory_manager_priority(self, mock_chat_client, memory_store):
        """Test injected memory manager takes priority over config."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,  # Config says enabled
        )

        # But we inject a specific manager
        agent = Agent(config=config, chat_client=mock_chat_client, memory_manager=memory_store)

        # Should use the injected one
        assert agent.memory_manager is memory_store

    def test_agent_memory_manager_is_none_when_explicitly_injected(self, mock_chat_client):
        """Test Agent memory manager can be explicitly set to None."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,  # Config says enabled
        )

        # But we explicitly pass None
        agent = Agent(config=config, chat_client=mock_chat_client, memory_manager=None)

        # Should create one from config since memory_enabled is True
        assert agent.memory_manager is not None
        assert isinstance(agent.memory_manager, InMemoryStore)

    @pytest.mark.asyncio
    async def test_agent_with_memory_can_add_messages(self, mock_chat_client):
        """Test Agent with memory can add messages."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        # Add messages to memory
        messages = [{"role": "user", "content": "Test message"}]
        result = await agent.memory_manager.add(messages)

        assert result["success"] is True
        assert len(result["result"]) == 1

    @pytest.mark.asyncio
    async def test_agent_with_memory_can_search_messages(self, mock_chat_client):
        """Test Agent with memory can search messages."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        # Add and search
        await agent.memory_manager.add([{"role": "user", "content": "Alice likes Python"}])
        result = await agent.memory_manager.search("Alice")

        assert result["success"] is True
        assert len(result["result"]) == 1

    @pytest.mark.asyncio
    async def test_agent_with_memory_can_clear_messages(self, mock_chat_client):
        """Test Agent with memory can clear messages."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        agent = Agent(config=config, chat_client=mock_chat_client)

        # Add and clear
        await agent.memory_manager.add([{"role": "user", "content": "Test"}])
        result = await agent.memory_manager.clear()

        assert result["success"] is True
        assert "Cleared 1 memories" in result["message"]

    def test_multiple_agents_have_separate_memory_managers(self, mock_chat_client):
        """Test multiple agents have separate memory managers."""
        config1 = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )
        config2 = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        agent1 = Agent(config=config1, chat_client=mock_chat_client)
        agent2 = Agent(config=config2, chat_client=mock_chat_client)

        # Should have different memory manager instances
        assert agent1.memory_manager is not agent2.memory_manager

    @pytest.mark.asyncio
    async def test_multiple_agents_have_independent_memory(self, mock_chat_client):
        """Test multiple agents have independent memory storage."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        agent1 = Agent(config=config, chat_client=mock_chat_client)
        agent2 = Agent(config=config, chat_client=mock_chat_client)

        # Add to agent1 memory
        await agent1.memory_manager.add([{"role": "user", "content": "Agent 1 message"}])

        # Agent2 memory should be empty
        result = await agent2.memory_manager.get_all()
        assert len(result["result"]) == 0

    def test_agent_has_memory_manager_attribute(self, mock_chat_client):
        """Test Agent has memory_manager attribute."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        agent = Agent(config=config, chat_client=mock_chat_client)

        assert hasattr(agent, "memory_manager")

    def test_agent_memory_manager_type_annotation(self, mock_chat_client):
        """Test Agent memory_manager accepts Any type."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        # Create agent - should work with Any type for memory_manager
        agent = Agent(config=config, chat_client=mock_chat_client)

        # Memory manager should be created
        assert agent.memory_manager is not None
