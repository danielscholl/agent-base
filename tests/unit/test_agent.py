"""Unit tests for agent.agent module."""

import pytest

from agent.agent import Agent
from agent.config import AgentConfig
from agent.tools.hello import HelloTools


class TestAgent:
    """Tests for Agent class."""

    def test_agent_initialization_with_config(self, mock_config, mock_chat_client):
        """Test Agent initializes with config and chat client."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        assert agent.config == mock_config
        assert agent.chat_client == mock_chat_client

    def test_agent_initialization_defaults_to_hello_tools(self, mock_config, mock_chat_client):
        """Test Agent defaults to HelloTools if no toolsets provided."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        assert len(agent.toolsets) == 1
        assert isinstance(agent.toolsets[0], HelloTools)

    def test_agent_collects_tools_from_toolsets(self, mock_config, mock_chat_client):
        """Test Agent collects all tools from toolsets."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        # HelloTools has 2 tools
        assert len(agent.tools) == 2

    def test_agent_creates_agent_with_tools(self, mock_config, mock_chat_client):
        """Test Agent creates agent with tools via chat client."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        # Check that create_agent was called
        assert len(mock_chat_client.created_agents) == 1
        created = mock_chat_client.created_agents[0]
        assert created["name"] == "Agent"
        assert "helpful AI assistant" in created["instructions"]
        assert len(created["tools"]) == 2

    def test_agent_with_custom_toolsets(self, mock_config, mock_chat_client):
        """Test Agent with custom toolsets."""
        hello_tools = HelloTools(mock_config)

        agent = Agent(config=mock_config, chat_client=mock_chat_client, toolsets=[hello_tools])

        assert len(agent.toolsets) == 1
        assert agent.toolsets[0] == hello_tools

    def test_agent_with_multiple_toolsets(self, mock_config, mock_chat_client):
        """Test Agent with multiple toolsets."""
        tools1 = HelloTools(mock_config)
        tools2 = HelloTools(mock_config)

        agent = Agent(config=mock_config, chat_client=mock_chat_client, toolsets=[tools1, tools2])

        assert len(agent.toolsets) == 2
        # Should have 4 tools (2 from each HelloTools)
        assert len(agent.tools) == 4

    @pytest.mark.asyncio
    async def test_agent_run(self, agent_instance):
        """Test Agent.run returns response."""
        response = await agent_instance.run("Say hello")

        assert response == "Hello from mock!"

    @pytest.mark.asyncio
    async def test_agent_run_stream(self, agent_instance):
        """Test Agent.run_stream yields response chunks."""
        chunks = []
        async for chunk in agent_instance.run_stream("Say hello"):
            chunks.append(chunk)

        # MockAgent splits response by words
        assert len(chunks) == 3  # "Hello", "from", "mock!"
        assert "".join(chunks) == "Hello from mock! "

    def test_agent_config_defaults_to_from_env(self, mock_chat_client):
        """Test Agent loads config from env if not provided."""
        # This will use environment variables
        agent = Agent(chat_client=mock_chat_client)

        assert agent.config is not None
        assert isinstance(agent.config, AgentConfig)

    def test_create_chat_client_raises_for_unknown_provider(self):
        """Test _create_chat_client raises ValueError for unknown provider."""
        config = AgentConfig(llm_provider="invalid_provider", openai_api_key="test")

        with pytest.raises(ValueError, match="Unknown provider: invalid_provider"):
            agent = Agent(config=config)

    def test_agent_has_agent_attribute(self, agent_instance):
        """Test Agent has agent attribute after initialization."""
        assert hasattr(agent_instance, "agent")
        assert agent_instance.agent is not None

    def test_agent_tools_is_list(self, agent_instance):
        """Test Agent.tools is a list."""
        assert isinstance(agent_instance.tools, list)

    def test_agent_toolsets_is_list(self, agent_instance):
        """Test Agent.toolsets is a list."""
        assert isinstance(agent_instance.toolsets, list)
