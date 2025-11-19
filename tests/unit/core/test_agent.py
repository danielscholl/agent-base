"""Unit tests for agent.agent module."""

import pytest

from agent.agent import Agent
from agent.config import AgentConfig
from agent.tools.hello import HelloTools


@pytest.mark.unit
@pytest.mark.agent
class TestAgent:
    """Tests for Agent class."""

    def test_agent_initialization_with_config(self, mock_config, mock_chat_client):
        """Test Agent initializes with config and chat client."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        assert agent.config == mock_config
        assert agent.chat_client == mock_chat_client

    def test_agent_initialization_defaults_to_hello_tools(self, mock_config, mock_chat_client):
        """Test Agent defaults to HelloTools and FileSystemTools if no toolsets provided."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        # Default toolsets: HelloTools + FileSystemTools
        assert len(agent.toolsets) == 2
        assert isinstance(agent.toolsets[0], HelloTools)

    def test_agent_collects_tools_from_toolsets(self, mock_config, mock_chat_client):
        """Test Agent collects all tools from toolsets."""
        agent = Agent(config=mock_config, chat_client=mock_chat_client)

        # Default: HelloTools (2) + FileSystemTools (7) = 9 tools
        assert len(agent.tools) == 9

    def test_agent_creates_agent_with_tools(self, mock_config, mock_chat_client):
        """Test Agent creates agent with tools via chat client."""
        Agent(config=mock_config, chat_client=mock_chat_client)

        # Check that create_agent was called
        assert len(mock_chat_client.created_agents) == 1
        created = mock_chat_client.created_agents[0]
        assert created["name"] == "Agent"
        assert "Helpful AI assistant" in created["instructions"]
        # Default toolsets: HelloTools (2) + FileSystemTools (7) = 9 tools
        assert len(created["tools"]) == 9

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
            Agent(config=config)

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

    @pytest.mark.asyncio
    async def test_agent_run_handles_string_response(self, agent_instance):
        """Test agent.run handles string responses from LLM."""

        # Mock agent returns a plain string (like OpenAI)
        async def mock_run(prompt, thread=None):
            return "Test response"

        agent_instance.agent.run = mock_run

        result = await agent_instance.run("test prompt")

        assert result == "Test response"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_agent_run_handles_object_with_text_attribute(self, agent_instance):
        """Test agent.run handles response objects with text attribute (like Anthropic)."""

        # Mock response object with .text attribute
        class MockResponse:
            def __init__(self):
                self.text = "Response from object"

        async def mock_run(prompt, thread=None):
            return MockResponse()

        agent_instance.agent.run = mock_run

        result = await agent_instance.run("test prompt")

        assert result == "Response from object"
        assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.agent
class TestAgentSystemPrompt:
    """Integration tests for agent creation with different prompt configurations."""

    def test_agent_uses_default_prompt(self, mock_config, mock_chat_client):
        """Test agent gets default prompt when no custom file specified."""
        Agent(config=mock_config, chat_client=mock_chat_client)

        # Verify agent was created with default prompt
        assert len(mock_chat_client.created_agents) == 1
        created = mock_chat_client.created_agents[0]

        # Should contain default prompt content
        assert "<agent>" in created["instructions"]
        assert "Helpful AI assistant" in created["instructions"]

    def test_agent_uses_custom_prompt(
        self, custom_prompt_config, mock_chat_client, custom_prompt_file
    ):
        """Test agent gets custom prompt from file specified in config."""
        Agent(config=custom_prompt_config, chat_client=mock_chat_client)

        # Verify agent was created with custom prompt
        assert len(mock_chat_client.created_agents) == 1
        created = mock_chat_client.created_agents[0]

        # Should contain custom prompt content
        assert "Custom Test Prompt" in created["instructions"]
        assert "test assistant" in created["instructions"]

    def test_agent_instructions_have_placeholders_replaced(
        self, custom_prompt_config, mock_chat_client
    ):
        """Test placeholders are replaced correctly in agent instructions."""
        Agent(config=custom_prompt_config, chat_client=mock_chat_client)

        created = mock_chat_client.created_agents[0]
        instructions = created["instructions"]

        # Verify placeholders are replaced
        assert "{{MODEL}}" not in instructions
        assert "{{PROVIDER}}" not in instructions
        assert "{{DATA_DIR}}" not in instructions
        assert "{{MEMORY_ENABLED}}" not in instructions

        # Verify actual values appear
        assert "OpenAI/gpt-5-mini" in instructions
        assert "openai" in instructions

    def test_agent_creation_succeeds_on_prompt_load_failure(
        self, mock_config, mock_chat_client, caplog
    ):
        """Test agent creation succeeds even if prompt loading fails."""
        # Set invalid custom prompt file
        mock_config.system_prompt_file = "/nonexistent/prompt.md"

        # Agent should still be created (using fallback)
        Agent(config=mock_config, chat_client=mock_chat_client)

        assert len(mock_chat_client.created_agents) == 1
        created = mock_chat_client.created_agents[0]

        # Should have some instructions (from fallback)
        assert len(created["instructions"]) > 0

        # Should log warning
        assert "Failed to load system prompt from AGENT_SYSTEM_PROMPT" in caplog.text

    def test_multiple_agents_with_different_configs(
        self, mock_config, custom_prompt_config, mock_chat_client
    ):
        """Test multiple agents can have different prompt configurations."""
        # Create agent with default config
        Agent(config=mock_config, chat_client=mock_chat_client)

        # Create agent with custom config
        Agent(config=custom_prompt_config, chat_client=mock_chat_client)

        # Verify both were created
        assert len(mock_chat_client.created_agents) == 2

        # First should have default prompt
        assert "<agent>" in mock_chat_client.created_agents[0]["instructions"]

        # Second should have custom prompt
        assert "Custom Test Prompt" in mock_chat_client.created_agents[1]["instructions"]
