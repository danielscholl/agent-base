"""Template for integration tests.

INSTRUCTIONS:
1. Copy this file to tests/integration/test_<feature>_integration.py
2. Replace placeholders with actual test scenarios
3. Integration tests verify components work together correctly
4. Use MockChatClient to avoid real LLM API calls

Integration tests should cover:
- Agent + Tools interactions
- Middleware + Tools chains
- Full request/response lifecycle
- Cross-component behavior
"""

import pytest

from agent.agent import Agent
from agent.config.schema import AgentSettings
from agent.tools.hello import HelloTools  # ← Replace with your tools
from tests.mocks.mock_client import MockChatClient


@pytest.fixture
def integration_config():
    """Create config for integration testing.

    Integration tests use real configuration but mocked LLM client.
    """
    return AgentSettings(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
    )


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client with predefined response."""
    return MockChatClient(response="Integration test response")


@pytest.fixture
def agent_with_tools(integration_config, mock_llm_client):
    """Create agent with full tool stack for integration testing.

    This fixture provides:
    - Real agent configuration
    - Mocked LLM client (no API calls)
    - Real tools (HelloTools or your custom tools)
    - Real middleware chain
    """
    # ← Replace HelloTools with your toolsets
    toolsets = [HelloTools(integration_config)]

    return Agent(settings=integration_config, chat_client=mock_llm_client, toolsets=toolsets)


@pytest.mark.integration
class TestAgentToolIntegration:
    """Integration tests for Agent + Tools interaction.

    These tests verify that the agent correctly:
    1. Registers tools from toolsets
    2. Creates agent with proper configuration
    3. Executes prompts through full stack
    4. Returns responses correctly
    """

    @pytest.mark.asyncio
    async def test_agent_registers_tools(self, agent_with_tools):
        """Verify agent correctly registers tools from toolsets."""
        # Check tools are registered
        assert len(agent_with_tools.tools) > 0, "Agent should have registered tools"

        # Check tools are callable
        assert all(callable(tool) for tool in agent_with_tools.tools), "All tools must be callable"

        # ← Add specific tool name checks
        tool_names = [tool.__name__ for tool in agent_with_tools.tools]
        assert "hello_world" in tool_names  # ← Replace with your tool names

    @pytest.mark.asyncio
    async def test_agent_creates_with_middleware(self, agent_with_tools):
        """Verify agent creates with middleware chain."""
        assert agent_with_tools.middleware is not None, "Middleware should be configured"
        assert len(agent_with_tools.middleware) > 0, "Should have middleware"

    @pytest.mark.asyncio
    async def test_full_execution_pipeline(self, agent_with_tools):
        """Test complete execution: prompt → agent → tools → response."""
        # Execute through full stack
        response = await agent_with_tools.run("test prompt")

        # Verify response
        assert response is not None, "Should return response"
        assert isinstance(response, str), "Response should be string"
        assert len(response) > 0, "Response should not be empty"

    @pytest.mark.asyncio
    async def test_streaming_execution(self, agent_with_tools):
        """Test streaming execution through full stack."""
        # Collect streamed chunks
        chunks = []
        async for chunk in agent_with_tools.run_stream("test prompt"):
            chunks.append(chunk)

        # Verify streaming works
        assert len(chunks) > 0, "Should receive chunks"
        full_response = "".join(chunks)
        assert len(full_response) > 0, "Combined response should not be empty"


@pytest.mark.integration
class TestMiddlewareToolIntegration:
    """Integration tests for Middleware + Tools interaction.

    These tests verify that middleware:
    1. Tracks tool execution
    2. Emits appropriate events
    3. Handles tool errors correctly
    4. Works with multiple tools
    """

    @pytest.mark.asyncio
    async def test_middleware_tracks_tool_execution(self, agent_with_tools):
        """Verify middleware tracks tool calls."""
        # This test would check that middleware properly tracks
        # tool invocations. Implementation depends on your middleware.

        # Execute agent
        await agent_with_tools.run("test prompt")

        # ← Add assertions about middleware behavior
        # For example, check event emissions, logs, metrics, etc.

    @pytest.mark.asyncio
    async def test_middleware_handles_tool_errors(self, agent_with_tools):
        """Verify middleware handles tool errors gracefully."""
        # Test that middleware properly handles when tools return errors

        # ← Add test implementation based on your middleware


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for different provider configurations.

    These tests verify agent works correctly with different LLM providers.
    All use MockChatClient to avoid real API calls.
    """

    @pytest.mark.asyncio
    async def test_openai_configuration(self, mock_llm_client):
        """Test agent with OpenAI configuration."""
        config = AgentSettings(llm_provider="openai", openai_api_key="test-key")
        agent = Agent(settings=config, chat_client=mock_llm_client)

        response = await agent.run("test")

        assert response
        assert agent.config.llm_provider == "openai"

    @pytest.mark.asyncio
    async def test_anthropic_configuration(self, mock_llm_client):
        """Test agent with Anthropic configuration."""
        config = AgentSettings(llm_provider="anthropic", anthropic_api_key="test-key")
        agent = Agent(settings=config, chat_client=mock_llm_client)

        response = await agent.run("test")

        assert response
        assert agent.config.llm_provider == "anthropic"

    @pytest.mark.asyncio
    async def test_azure_configuration(self, mock_llm_client):
        """Test agent with Azure OpenAI configuration."""
        config = AgentSettings(
            llm_provider="azure",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_deployment="gpt-5-codex",
        )
        agent = Agent(settings=config, chat_client=mock_llm_client)

        response = await agent.run("test")

        assert response
        assert agent.config.llm_provider == "azure"


@pytest.mark.integration
class TestErrorPropagation:
    """Integration tests for error handling across components.

    These tests verify that errors:
    1. Propagate correctly through stack
    2. Are formatted consistently
    3. Don't crash the agent
    4. Provide useful information
    """

    @pytest.mark.asyncio
    async def test_tool_error_propagation(self, agent_with_tools):
        """Test that tool errors propagate correctly."""
        # Test scenario where tool returns error response
        # Verify agent handles it gracefully

        # ← Add implementation

    @pytest.mark.asyncio
    async def test_configuration_error_handling(self):
        """Test handling of invalid configuration."""
        # Test that agent handles bad configuration gracefully

        config = AgentSettings(llm_provider="openai")  # Missing API key

        with pytest.raises(Exception):  # ← Adjust exception type
            config.validate()


@pytest.mark.integration
@pytest.mark.slow
class TestLongRunningOperations:
    """Integration tests for long-running operations.

    Mark as slow so they can be excluded from quick test runs.
    """

    @pytest.mark.asyncio
    async def test_multiple_sequential_calls(self, agent_with_tools):
        """Test agent handles multiple sequential calls."""
        responses = []

        for i in range(5):
            response = await agent_with_tools.run(f"test prompt {i}")
            responses.append(response)

        assert len(responses) == 5
        assert all(responses), "All calls should return responses"

    @pytest.mark.asyncio
    async def test_large_response_handling(self, agent_with_tools):
        """Test agent handles large responses."""
        # Create mock client with large response
        large_response = "x" * 10000
        mock_client = MockChatClient(response=large_response)

        config = AgentSettings(llm_provider="openai", openai_api_key="test-key")
        agent = Agent(settings=config, chat_client=mock_client)

        response = await agent.run("test")

        assert len(response) == 10000


# ============================================================================
# Custom Integration Fixtures
# ============================================================================


@pytest.fixture
def multi_toolset_agent(integration_config, mock_llm_client):
    """Create agent with multiple toolsets.

    Use this fixture to test interactions between multiple toolsets.
    """
    # ← Add your toolsets here
    toolsets = [
        HelloTools(integration_config),
        # YourOtherTools(integration_config),
    ]

    return Agent(settings=integration_config, chat_client=mock_llm_client, toolsets=toolsets)


# ============================================================================
# Marker Usage
# ============================================================================
# @pytest.mark.integration  - All tests in this file
# @pytest.mark.slow         - Long-running tests (>1s)
# @pytest.mark.asyncio      - Async tests (applied automatically)
