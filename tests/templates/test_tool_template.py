"""Template for testing new tool implementations.

INSTRUCTIONS:
1. Copy this file to tests/unit/tools/test_<your_tool_name>.py
2. Replace all instances of:
   - YourToolset → Your actual toolset class name
   - your_tool_function → Your actual tool function name
   - "your_tool" → Your tool module name
3. Add/remove test methods based on your tool's functionality
4. Follow the existing pattern for test organization

This template demonstrates the recommended testing pattern for all tools.
"""

import pytest

from agent.config import AgentConfig
from agent.tools.your_tool import YourToolset  # ← Replace with your import
from tests.helpers import assert_error_response, assert_success_response


@pytest.fixture
def tool_config():
    """Create config for tool testing.

    This fixture provides a basic configuration suitable for unit testing.
    All tests using this fixture will be isolated from real API calls.
    """
    return AgentConfig(llm_provider="openai", openai_api_key="test-key")


@pytest.fixture
def toolset(tool_config):
    """Create toolset instance.

    This fixture provides a configured toolset ready for testing.
    Use this in most tests instead of creating toolsets manually.
    """
    return YourToolset(tool_config)  # ← Replace YourToolset


@pytest.mark.unit
@pytest.mark.tools
class TestYourToolset:  # ← Replace TestYourToolset
    """Tests for YourToolset.

    This test class should cover:
    1. Initialization and configuration
    2. Tool registration (get_tools)
    3. Happy path scenarios for each tool function
    4. Error cases and edge cases
    5. Response format validation
    6. Tool docstrings (important for LLM)
    """

    # ============================================================================
    # Initialization Tests
    # ============================================================================

    def test_initialization(self, tool_config):
        """Test toolset initializes with config."""
        tools = YourToolset(tool_config)  # ← Replace YourToolset

        assert tools.config == tool_config
        assert tools.config.llm_provider == "openai"

    def test_get_tools_returns_expected_count(self, toolset):
        """Test get_tools returns correct number of tools."""
        tools_list = toolset.get_tools()

        # ← Adjust count based on your tool
        assert len(tools_list) == 2, "Expected 2 tools"
        assert all(callable(tool) for tool in tools_list), "All tools must be callable"

    def test_tool_functions_are_registered(self, toolset):
        """Test all expected tool functions are in get_tools list."""
        tools_list = toolset.get_tools()

        # ← Replace with your actual tool functions
        assert toolset.your_tool_function in tools_list
        # Add more assertions for other tools

    # ============================================================================
    # Tool Docstring Tests (Important for LLM)
    # ============================================================================

    def test_tool_docstrings_exist(self, toolset):
        """Test tool functions have docstrings for LLM.

        The LLM uses these docstrings to understand what the tool does,
        so they must be clear and comprehensive.
        """
        # ← Replace with your tool function
        assert toolset.your_tool_function.__doc__ is not None
        assert len(toolset.your_tool_function.__doc__) > 20, "Docstring should be descriptive"

    # ============================================================================
    # Happy Path Tests
    # ============================================================================

    @pytest.mark.asyncio
    @pytest.mark.fast
    async def test_your_tool_function_success(self, toolset):
        """Test your_tool_function with valid input.

        Replace this with actual test for your tool's main functionality.
        """
        # ← Replace with actual function call
        result = await toolset.your_tool_function("valid_input")

        # Validate response format
        assert_success_response(result)

        # ← Add specific assertions for your tool
        assert "expected_value" in result["result"]
        assert result["message"], "Message should describe what happened"

    @pytest.mark.asyncio
    async def test_your_tool_function_with_different_input(self, toolset):
        """Test your_tool_function with different valid input."""
        # ← Add more happy path tests with different inputs
        result = await toolset.your_tool_function("another_valid_input")

        assert_success_response(result)
        # Add specific assertions

    # ============================================================================
    # Error Case Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_your_tool_function_invalid_input(self, toolset):
        """Test your_tool_function with invalid input.

        Tools should return structured error responses, not raise exceptions.
        """
        # ← Replace with actual invalid input
        result = await toolset.your_tool_function("invalid_input")

        # Validate error response format
        assert_error_response(result)

        # ← Add specific error code assertion
        assert result["error"] == "expected_error_code"
        assert "helpful message" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_your_tool_function_missing_required_param(self, toolset):
        """Test your_tool_function with missing required parameter."""
        # If your tool has required parameters, test what happens when missing
        # This might raise TypeError or return error response depending on design
        pass  # ← Implement based on your tool

    # ============================================================================
    # Edge Case Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_your_tool_function_empty_string(self, toolset):
        """Test your_tool_function with empty string input."""
        await toolset.your_tool_function("")

        # Decide: Should empty string be valid or error?
        # ← Implement based on your requirements

    @pytest.mark.asyncio
    async def test_your_tool_function_very_long_input(self, toolset):
        """Test your_tool_function with very long input."""
        long_input = "x" * 10000

        await toolset.your_tool_function(long_input)

        # ← Validate how your tool handles long inputs

    @pytest.mark.asyncio
    async def test_your_tool_function_special_characters(self, toolset):
        """Test your_tool_function with special characters."""
        special_input = "Test with !@#$%^&*()_+ special chars"

        await toolset.your_tool_function(special_input)

        # ← Validate special character handling

    # ============================================================================
    # Response Format Tests
    # ============================================================================

    def test_response_helper_methods(self, toolset):
        """Test response helper methods work correctly."""
        # Test success response format
        success = toolset._create_success_response("test_data", "test message")
        assert success["success"] is True
        assert success["result"] == "test_data"
        assert success["message"] == "test message"

        # Test error response format
        error = toolset._create_error_response("test_error", "error message")
        assert error["success"] is False
        assert error["error"] == "test_error"
        assert error["message"] == "error message"


# ============================================================================
# Additional Test Classes (if needed)
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestYourToolsetIntegration:
    """Integration tests between multiple tools in the same toolset.

    Use this class if your toolset has tools that interact with each other
    or share state.
    """

    @pytest.mark.asyncio
    async def test_tool_composition(self, toolset):
        """Test tools working together."""
        # ← Add tests if tools call each other
        pass


# ============================================================================
# Marker Usage Examples
# ============================================================================
# @pytest.mark.unit           - All tests in this file (fast, isolated)
# @pytest.mark.tools          - Feature area marker
# @pytest.mark.fast           - Tests <100ms
# @pytest.mark.slow           - Tests >1s
# @pytest.mark.asyncio        - Async tests (applied automatically)
