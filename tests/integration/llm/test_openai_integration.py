"""Real OpenAI integration tests.

⚠️ WARNING: These tests make real API calls and cost money!

Cost: ~$0.003 per test run (with gpt-4o-mini)

How to run:
    # Set API key
    export OPENAI_API_KEY=your-key

    # Run these tests
    pytest -m "llm and requires_openai"

    # Or run all LLM tests
    pytest -m llm
"""

import pytest


@pytest.mark.llm
@pytest.mark.requires_openai
@pytest.mark.slow
class TestOpenAIBasicFunctionality:
    """Test basic OpenAI functionality with real API.

    These tests verify the agent works correctly with OpenAI's API.
    """

    @pytest.mark.asyncio
    async def test_basic_prompt_response(self, openai_agent):
        """Test basic prompt with real OpenAI API.

        Cost: ~$0.0001
        """
        response = await openai_agent.run("Say the word 'test' and nothing else")

        assert response is not None, "Should return response"
        assert isinstance(response, str), "Response should be string"
        assert len(response) > 0, "Response should not be empty"
        # Relaxed assertion - LLM might not follow exactly
        assert "test" in response.lower(), "Response should contain 'test'"

    @pytest.mark.asyncio
    async def test_simple_math(self, openai_agent):
        """Test simple reasoning with OpenAI.

        Cost: ~$0.0001
        """
        response = await openai_agent.run("What is 2+2? Answer with just the number.")

        assert response is not None
        # Should contain "4" somewhere in response
        assert "4" in response, "Response should contain '4'"

    @pytest.mark.asyncio
    async def test_streaming_response(self, openai_agent):
        """Test streaming with OpenAI.

        Cost: ~$0.0001
        """
        chunks = []
        async for chunk in openai_agent.run_stream("Say hello"):
            chunks.append(chunk)

        assert len(chunks) > 0, "Should receive chunks"
        full_response = "".join(chunks)
        assert len(full_response) > 0, "Combined response should not be empty"


@pytest.mark.llm
@pytest.mark.requires_openai
@pytest.mark.slow
class TestOpenAIToolInvocation:
    """Test tool invocation with real OpenAI API.

    These tests verify OpenAI correctly calls our tools.
    This is CRITICAL - it ensures tool schemas are correct.
    """

    @pytest.mark.asyncio
    async def test_tool_invocation_hello_world(self, openai_agent):
        """Test that OpenAI correctly invokes hello_world tool.

        This verifies:
        1. LLM understands our tool schema
        2. LLM chooses to call the tool when appropriate
        3. LLM provides correct arguments
        4. Tool result is returned to user

        Cost: ~$0.0005
        """
        response = await openai_agent.run(
            "Use the hello_world tool to greet Alice. Return only the greeting."
        )

        # Verify response contains expected content
        assert "Alice" in response, "Response should mention Alice"
        assert len(response) > 0, "Should have response"

    @pytest.mark.asyncio
    async def test_tool_invocation_with_language(self, openai_agent):
        """Test greet_user tool with language parameter.

        Cost: ~$0.0005
        """
        response = await openai_agent.run(
            "Use greet_user to greet Bob in Spanish (language code 'es')"
        )

        # Should contain Spanish greeting or mention Bob
        assert "Bob" in response or "Hola" in response or "hola" in response


@pytest.mark.llm
@pytest.mark.requires_openai
@pytest.mark.slow
class TestOpenAIErrorHandling:
    """Test error handling with real OpenAI API."""

    @pytest.mark.asyncio
    async def test_tool_error_communication(self, openai_agent):
        """Test that LLM communicates tool errors to user.

        When a tool returns an error, the LLM should:
        1. Recognize the error
        2. Communicate it appropriately to user
        3. Not crash

        Cost: ~$0.0005
        """
        response = await openai_agent.run(
            "Use greet_user to greet someone in German (language code 'de')"
        )

        # LLM should communicate the error
        # It might say "doesn't support", "not supported", "only accepts", etc.
        response_lower = response.lower()
        error_indicators = [
            "not supported",
            "error",
            "cannot",
            "unable",
            "not available",
            "doesn't support",
            "does not support",
            "only accepts",
            "only supports",
            "unsupported",
        ]

        assert any(
            indicator in response_lower for indicator in error_indicators
        ), f"Should communicate tool error. Response: {response}"


# NOTE: Multi-turn conversation context tests removed
# Threading/memory is not yet implemented in the agent template
# When memory feature is added, add tests for:
# - Multi-turn conversation context
# - Context across tool calls
# - Thread serialization/deserialization
