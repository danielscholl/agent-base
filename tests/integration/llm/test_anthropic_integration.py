"""Real Anthropic integration tests.

⚠️ WARNING: These tests make real API calls and cost money!

Cost: ~$0.004 per test run (with claude-sonnet-4-5)

How to run:
    # Set API key
    export ANTHROPIC_API_KEY=your-key

    # Run these tests
    pytest -m "llm and requires_anthropic"
"""

import pytest


@pytest.mark.llm
@pytest.mark.requires_anthropic
@pytest.mark.slow
class TestAnthropicBasicFunctionality:
    """Test basic Anthropic functionality with real API."""

    @pytest.mark.asyncio
    async def test_basic_prompt_response(self, anthropic_agent):
        """Test basic prompt with real Anthropic API.

        Cost: ~$0.0001
        """
        response = await anthropic_agent.run("Say the word 'test' and nothing else")

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        assert "test" in response.lower()

    @pytest.mark.asyncio
    async def test_streaming_response(self, anthropic_agent):
        """Test streaming with Anthropic.

        Cost: ~$0.0002
        """
        chunks = []
        async for chunk in anthropic_agent.run_stream("Say hello in three words"):
            chunks.append(chunk)

        assert len(chunks) > 0, "Should receive chunks"
        full_response = "".join(chunks)
        assert len(full_response) > 0
        assert "hello" in full_response.lower()


@pytest.mark.llm
@pytest.mark.requires_anthropic
@pytest.mark.slow
class TestAnthropicToolInvocation:
    """Test tool invocation with real Anthropic API."""

    @pytest.mark.asyncio
    async def test_tool_invocation_hello_world(self, anthropic_agent):
        """Test that Anthropic correctly invokes hello_world tool.

        Cost: ~$0.0005
        """
        response = await anthropic_agent.run(
            "Use the hello_world tool to greet Alice. Return only the greeting."
        )

        assert "Alice" in response
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_tool_invocation_with_parameters(self, anthropic_agent):
        """Test greet_user tool with language parameter.

        Cost: ~$0.0005
        """
        response = await anthropic_agent.run(
            "Use the greet_user tool to greet Carlos in Spanish (language code 'es')"
        )

        # Should mention Carlos or include Spanish greeting
        assert "Carlos" in response or "Hola" in response or "hola" in response


@pytest.mark.llm
@pytest.mark.requires_anthropic
@pytest.mark.slow
class TestAnthropicErrorHandling:
    """Test error handling with Anthropic."""

    @pytest.mark.asyncio
    async def test_tool_error_communication(self, anthropic_agent):
        """Test that Anthropic communicates tool errors appropriately.

        Cost: ~$0.0005
        """
        response = await anthropic_agent.run(
            "Use greet_user to greet someone in German (language code 'de')"
        )

        # Should communicate the error
        response_lower = response.lower()
        error_indicators = [
            "not supported",
            "error",
            "cannot",
            "unable",
            "not available",
            "doesn't support",
        ]

        assert any(
            indicator in response_lower for indicator in error_indicators
        ), f"Should communicate tool error. Response: {response}"


# NOTE: Multi-turn conversation context tests removed
# Threading/memory is not yet implemented in the agent template
# When memory feature is added, add tests for multi-turn conversations
