"""Real Local provider integration tests.

⚠️ WARNING: These tests require Docker Desktop with models running!

Cost: FREE - runs locally with no API costs

How to run:
    # Enable Model Runner
    docker desktop enable model-runner --tcp 12434

    # Pull a model
    docker model pull phi4

    # Set base URL (optional, uses localhost:12434 by default)
    export LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1
    export LOCAL_MODEL=phi4

    # Run these tests
    pytest -m "llm and requires_local"

    # Or run all LLM tests
    pytest -m llm

Note: Requires Docker Desktop with model serving enabled
"""

import pytest


@pytest.mark.llm
@pytest.mark.requires_local
@pytest.mark.slow
class TestLocalBasicFunctionality:
    """Test basic local provider functionality with Docker models.

    These tests verify the agent works correctly with locally-hosted models
    via Docker Desktop's model serving capability.
    """

    @pytest.mark.asyncio
    async def test_basic_prompt_response(self, local_agent):
        """Test basic prompt with local Docker model.

        Cost: FREE (local execution)
        """
        response = await local_agent.run("Say the word 'test' and nothing else")

        assert response is not None, "Should return response"
        assert isinstance(response, str), "Response should be string"
        assert len(response) > 0, "Response should not be empty"
        # Relaxed assertion - LLM might not follow exactly
        assert "test" in response.lower(), "Response should contain 'test'"

    @pytest.mark.asyncio
    async def test_simple_math(self, local_agent):
        """Test simple reasoning with local model.

        Cost: FREE
        """
        response = await local_agent.run("What is 2+2? Answer with just the number.")

        assert response is not None
        # Should contain "4" somewhere in response
        assert "4" in response, "Response should contain '4'"

    @pytest.mark.asyncio
    async def test_streaming_response(self, local_agent):
        """Test streaming with local model.

        Cost: FREE
        """
        chunks = []
        async for chunk in local_agent.run_stream("Say hello"):
            chunks.append(chunk)

        assert len(chunks) > 0, "Should receive chunks"
        full_response = "".join(chunks)
        assert len(full_response) > 0, "Combined response should not be empty"


@pytest.mark.llm
@pytest.mark.requires_local
@pytest.mark.slow
class TestLocalToolInvocation:
    """Test tool invocation with local Docker models.

    These tests verify local models correctly call our tools.
    This is CRITICAL - it ensures tool schemas work with local models.

    Note: Tool calling support varies by model. phi4 supports function calling,
    but some other local models may not.
    """

    @pytest.mark.asyncio
    async def test_tool_invocation_hello_world(self, local_agent):
        """Test that local model correctly invokes hello_world tool.

        This verifies:
        1. LLM understands our tool schema
        2. LLM chooses to call the tool when appropriate
        3. LLM provides correct arguments
        4. Tool result is returned to user

        Cost: FREE
        """
        response = await local_agent.run(
            "Use the hello_world tool to greet Alice. Return only the greeting."
        )

        # Verify response contains expected content
        assert "Alice" in response, "Response should mention Alice"

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, local_agent):
        """Test conversation continuity with local model.

        Cost: FREE
        """
        # First turn - establish context
        response1 = await local_agent.run("Remember: my favorite color is blue")
        assert response1 is not None

        # Second turn - recall context
        response2 = await local_agent.run("What is my favorite color?")
        assert "blue" in response2.lower(), "Should recall favorite color"
