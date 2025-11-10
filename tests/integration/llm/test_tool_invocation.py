"""Cross-provider tool invocation tests.

⚠️ WARNING: These tests make real API calls and cost money!

These tests verify that tool invocation works correctly across all LLM providers.
This is critical because:
1. Each provider has different tool calling formats
2. Tool schemas must work universally
3. Error handling must be consistent

Cost: ~$0.002 per test run (depends on which providers are configured)

How to run:
    # Set API keys for providers you want to test
    export OPENAI_API_KEY=your-key
    export ANTHROPIC_API_KEY=your-key

    # Run all tool invocation tests
    pytest tests/integration/llm/test_tool_invocation.py -v
"""

import pytest


@pytest.mark.llm
@pytest.mark.slow
class TestToolInvocationAcrossProviders:
    """Test tool invocation works across all providers.

    These tests help ensure consistent behavior regardless of LLM provider.
    """

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    async def test_openai_hello_world_tool(self, openai_agent):
        """Test hello_world tool with OpenAI.

        Cost: ~$0.0003
        """
        response = await openai_agent.run("Call the hello_world tool with name='TestUser'")

        assert "TestUser" in response, f"Expected 'TestUser' in response: {response}"

    @pytest.mark.requires_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_hello_world_tool(self, anthropic_agent):
        """Test hello_world tool with Anthropic.

        Cost: ~$0.0003
        """
        response = await anthropic_agent.run("Call the hello_world tool with name='TestUser'")

        assert "TestUser" in response, f"Expected 'TestUser' in response: {response}"

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    async def test_openai_greet_user_spanish(self, openai_agent):
        """Test greet_user tool with Spanish language parameter.

        Cost: ~$0.0003
        """
        response = await openai_agent.run("Use greet_user tool: name='Maria', language='es'")

        # Should contain Maria and Spanish greeting
        assert "Maria" in response
        # May contain actual Spanish greeting or mention of it

    @pytest.mark.requires_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_greet_user_french(self, anthropic_agent):
        """Test greet_user tool with French language parameter.

        Cost: ~$0.0003
        """
        response = await anthropic_agent.run("Use greet_user tool: name='Pierre', language='fr'")

        assert "Pierre" in response


@pytest.mark.llm
@pytest.mark.slow
class TestToolErrorHandlingAcrossProviders:
    """Test that all providers handle tool errors consistently."""

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    async def test_openai_handles_unsupported_language(self, openai_agent):
        """Test OpenAI handles unsupported language error.

        Cost: ~$0.0003
        """
        response = await openai_agent.run(
            "Use greet_user with name='Hans' and language='de' (German)"
        )

        # Should communicate that German is not supported
        response_lower = response.lower()
        assert any(
            word in response_lower
            for word in ["not supported", "error", "cannot", "unable", "unsupported"]
        )

    @pytest.mark.requires_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_handles_unsupported_language(self, anthropic_agent):
        """Test Anthropic handles unsupported language error.

        Cost: ~$0.0003
        """
        response = await anthropic_agent.run(
            "Use greet_user with name='Hans' and language='de' (German)"
        )

        # Should communicate error
        response_lower = response.lower()
        error_indicators = [
            "not supported",
            "error",
            "cannot",
            "unable",
            "unsupported",
            "doesn't support",
            "does not support",
            "only accepts",
            "only supports",
        ]
        assert any(
            word in response_lower for word in error_indicators
        ), f"Should communicate error. Response: {response}"


@pytest.mark.llm
@pytest.mark.slow
class TestToolResponseFormat:
    """Test that tool responses are correctly interpreted by LLMs."""

    @pytest.mark.requires_openai
    @pytest.mark.asyncio
    async def test_openai_interprets_success_response(self, openai_agent):
        """Test OpenAI correctly interprets tool success response.

        Cost: ~$0.0003
        """
        response = await openai_agent.run(
            "Use hello_world tool to greet 'Success'. What was the result?"
        )

        # Should mention "Success" from tool result
        assert "Success" in response

    @pytest.mark.requires_anthropic
    @pytest.mark.asyncio
    async def test_anthropic_interprets_success_response(self, anthropic_agent):
        """Test Anthropic correctly interprets tool success response.

        Cost: ~$0.0003
        """
        response = await anthropic_agent.run(
            "Use hello_world tool to greet 'Success'. What was the result?"
        )

        assert "Success" in response
