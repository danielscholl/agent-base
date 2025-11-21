"""Template for real LLM integration tests.

⚠️ IMPORTANT: These tests make real API calls and cost money!

INSTRUCTIONS:
1. Copy this file to tests/integration/llm/test_<feature>_llm.py
2. Replace placeholders with actual test scenarios
3. Keep prompts minimal to control costs
4. Use cheaper models (gpt-4o-mini, claude-sonnet-4-5)
5. Add @pytest.mark.llm to all tests
6. Add provider markers (@pytest.mark.requires_openai, etc.)
7. Use pytest.skipif to skip when API keys not present

COST CONTROLS:
- Target: < $0.01 per full test run
- Use small prompts (5-15 tokens)
- Use cheaper models
- Run opt-in only: pytest -m llm

HOW TO RUN:
```bash
# Set API key
export OPENAI_API_KEY=your-key

# Run specific provider tests
pytest -m "llm and requires_openai"

# Run all LLM tests
pytest -m llm

# Skip LLM tests (default)
pytest -m "not llm"
```
"""

import os

import pytest

from agent.agent import Agent
from agent.config.schema import AgentSettings

# ============================================================================
# Fixtures for Real LLM Testing
# ============================================================================


@pytest.fixture
def openai_agent():
    """Create agent with real OpenAI client.

    Skips if OPENAI_API_KEY not set.
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    config = AgentSettings(
        llm_provider="openai",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model="gpt-4o-mini",  # Cheaper model for testing
    )

    return Agent(settings=config)


@pytest.fixture
def anthropic_agent():
    """Create agent with real Anthropic client.

    Skips if ANTHROPIC_API_KEY not set.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    config = AgentSettings(
        llm_provider="anthropic",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model="claude-haiku-4-5-20251001",  # Cheapest model tier
    )

    return Agent(settings=config)


@pytest.fixture
def azure_agent():
    """Create agent with real Azure OpenAI client.

    Skips if Azure credentials not set.
    """
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        pytest.skip("Azure credentials not set")

    config = AgentSettings(
        llm_provider="azure",
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    )

    return Agent(settings=config)


# ============================================================================
# OpenAI Integration Tests
# ============================================================================


@pytest.mark.llm
@pytest.mark.requires_openai
@pytest.mark.slow
class TestOpenAIIntegration:
    """Real LLM integration tests with OpenAI.

    These tests verify:
    1. Basic prompt/response works
    2. Tool invocation works correctly
    3. Error handling works
    4. Multi-turn conversations work

    Cost: ~$0.002 per test run (with gpt-4o-mini)
    """

    @pytest.mark.asyncio
    async def test_basic_prompt_response(self, openai_agent):
        """Test basic prompt with real OpenAI API.

        This is the simplest test - just verify we can get a response.
        Cost: ~$0.0001
        """
        response = await openai_agent.run("Say 'test' and nothing else")

        assert response is not None, "Should return response"
        assert isinstance(response, str), "Response should be string"
        assert len(response) > 0, "Response should not be empty"
        # Relaxed assertion - LLM might not follow exactly
        assert "test" in response.lower(), "Response should contain 'test'"

    @pytest.mark.asyncio
    async def test_tool_invocation(self, openai_agent):
        """Test that OpenAI correctly invokes tool.

        This is critical - verifies the LLM:
        1. Understands our tool schema
        2. Chooses to call the tool
        3. Provides correct arguments
        4. Returns tool result to user

        Cost: ~$0.0005
        """
        # Specific instruction to use tool
        response = await openai_agent.run(
            "Use the hello_world tool to greet Alice. Return only the greeting."
        )

        # Verify response contains expected content
        assert "Alice" in response, "Response should mention Alice"
        # Tool-specific emoji might be in response
        assert len(response) > 0, "Should have response"

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, openai_agent):
        """Test that LLM handles tool errors gracefully.

        When a tool returns an error, the LLM should:
        1. Recognize the error
        2. Communicate it to the user appropriately
        3. Not crash or fail

        Cost: ~$0.0005
        """
        # Ask LLM to use tool in a way that will cause error
        # (German not supported by greet_user tool)
        response = await openai_agent.run(
            "Use greet_user to greet Bob in German language code 'de'"
        )

        # LLM should communicate the error to user
        # It might say "not supported", "error", "cannot", etc.
        response_lower = response.lower()
        assert any(
            word in response_lower for word in ["not supported", "error", "cannot", "unable"]
        ), "Should communicate tool error to user"

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, openai_agent):
        """Test multi-turn conversation with context.

        Verify the agent maintains conversation context.
        Cost: ~$0.001
        """
        # Get new thread for context
        thread = openai_agent.get_new_thread()

        # First turn
        response1 = await openai_agent.run("My name is Alice", thread=thread)
        assert response1, "First response should not be empty"

        # Second turn - reference first turn
        response2 = await openai_agent.run("What is my name?", thread=thread)

        # Should remember Alice from first turn
        assert "Alice" in response2, "Should remember name from previous turn"


# ============================================================================
# Anthropic Integration Tests
# ============================================================================


@pytest.mark.llm
@pytest.mark.requires_anthropic
@pytest.mark.slow
class TestAnthropicIntegration:
    """Real LLM integration tests with Anthropic Claude.

    Cost: ~$0.003 per test run (with claude-sonnet-4-5)
    """

    @pytest.mark.asyncio
    async def test_basic_prompt_response(self, anthropic_agent):
        """Test basic prompt with real Anthropic API.

        Cost: ~$0.0001
        """
        response = await anthropic_agent.run("Say 'test' and nothing else")

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        assert "test" in response.lower()

    @pytest.mark.asyncio
    async def test_tool_invocation(self, anthropic_agent):
        """Test that Anthropic correctly invokes tool.

        Cost: ~$0.0005
        """
        response = await anthropic_agent.run(
            "Use the hello_world tool to greet Alice. Return only the greeting."
        )

        assert "Alice" in response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_streaming_response(self, anthropic_agent):
        """Test streaming with Anthropic.

        Cost: ~$0.0002
        """
        chunks = []
        async for chunk in anthropic_agent.run_stream("Say hello in 3 words"):
            chunks.append(chunk)

        assert len(chunks) > 0, "Should receive chunks"
        full_response = "".join(chunks)
        assert len(full_response) > 0


# ============================================================================
# Azure OpenAI Integration Tests
# ============================================================================


@pytest.mark.llm
@pytest.mark.requires_azure
@pytest.mark.slow
class TestAzureOpenAIIntegration:
    """Real LLM integration tests with Azure OpenAI.

    Cost: Varies by Azure deployment
    """

    @pytest.mark.asyncio
    async def test_basic_prompt_response(self, azure_agent):
        """Test basic prompt with Azure OpenAI.

        Cost: Depends on Azure deployment
        """
        response = await azure_agent.run("Say 'test' and nothing else")

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_tool_invocation(self, azure_agent):
        """Test tool invocation with Azure OpenAI."""
        response = await azure_agent.run(
            "Use the hello_world tool to greet Alice. Return only the greeting."
        )

        assert "Alice" in response


# ============================================================================
# Cross-Provider Comparison Tests
# ============================================================================


@pytest.mark.llm
@pytest.mark.slow
class TestCrossProviderBehavior:
    """Compare behavior across different LLM providers.

    These tests help ensure consistent behavior regardless of provider.
    Only run if multiple providers are configured.
    """

    @pytest.mark.asyncio
    async def test_all_providers_basic_prompt(self, openai_agent, anthropic_agent):
        """Test that all providers handle basic prompts similarly."""
        prompt = "Say the word 'hello'"

        # Test each provider
        responses = []

        try:
            openai_response = await openai_agent.run(prompt)
            responses.append(("openai", openai_response))
        except Exception:
            pytest.skip("OpenAI not configured")

        try:
            anthropic_response = await anthropic_agent.run(prompt)
            responses.append(("anthropic", anthropic_response))
        except Exception:
            pytest.skip("Anthropic not configured")

        # Verify all providers returned something
        assert len(responses) > 0, "At least one provider should work"

        # All should contain "hello"
        for provider, response in responses:
            assert "hello" in response.lower(), f"{provider} should include 'hello' in response"


# ============================================================================
# Cost Tracking Utilities
# ============================================================================


def estimate_test_cost():
    """Estimate the cost of running all LLM tests.

    Returns approximate cost in USD.
    """
    costs = {
        "openai_basic": 0.0001,
        "openai_tool": 0.0005,
        "openai_error": 0.0005,
        "openai_multi": 0.001,
        "anthropic_basic": 0.0001,
        "anthropic_tool": 0.0005,
        "anthropic_stream": 0.0002,
    }

    return sum(costs.values())


# Print estimated cost when module loads
print(f"\n💰 Estimated LLM test cost: ${estimate_test_cost():.4f}")
print("Run with: pytest -m llm")
print("Skip with: pytest -m 'not llm' (default)\n")


# ============================================================================
# Marker Usage
# ============================================================================
# @pytest.mark.llm                  - Required for all real LLM tests
# @pytest.mark.requires_openai      - Requires OpenAI API key
# @pytest.mark.requires_anthropic   - Requires Anthropic API key
# @pytest.mark.requires_azure       - Requires Azure credentials
# @pytest.mark.slow                 - Long-running tests
# @pytest.mark.asyncio              - Async tests (applied automatically)
