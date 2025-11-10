"""Custom assertions for testing agent functionality.

This module provides reusable assertions for common test scenarios,
particularly for validating tool response formats and agent behavior.
"""

from typing import Any


def assert_success_response(response: dict[str, Any]) -> None:
    """Assert that a response follows the success format.

    Args:
        response: The response dictionary to validate

    Raises:
        AssertionError: If response doesn't match expected success format

    Example:
        >>> result = await tool.hello_world("Alice")
        >>> assert_success_response(result)
    """
    assert isinstance(response, dict), f"Response must be dict, got {type(response)}"
    assert "success" in response, "Response missing 'success' field"
    assert response["success"] is True, f"Expected success=True, got {response['success']}"
    assert "result" in response, "Success response missing 'result' field"
    assert "message" in response, "Success response missing 'message' field"


def assert_error_response(response: dict[str, Any], error_code: str | None = None) -> None:
    """Assert that a response follows the error format.

    Args:
        response: The response dictionary to validate
        error_code: Optional specific error code to check for

    Raises:
        AssertionError: If response doesn't match expected error format

    Example:
        >>> result = await tool.greet_user("Test", "invalid")
        >>> assert_error_response(result, "unsupported_language")
    """
    assert isinstance(response, dict), f"Response must be dict, got {type(response)}"
    assert "success" in response, "Response missing 'success' field"
    assert response["success"] is False, f"Expected success=False, got {response['success']}"
    assert "error" in response, "Error response missing 'error' field"
    assert "message" in response, "Error response missing 'message' field"

    if error_code is not None:
        actual_code = response.get("error")
        assert actual_code == error_code, f"Expected error code '{error_code}', got '{actual_code}'"


def assert_tool_response_format(response: dict[str, Any]) -> None:
    """Assert that a response follows the standard tool response format.

    This checks for the presence of required fields but doesn't validate
    whether it's a success or error response.

    Args:
        response: The response dictionary to validate

    Raises:
        AssertionError: If response doesn't have required fields

    Example:
        >>> result = await tool.some_function()
        >>> assert_tool_response_format(result)
    """
    assert isinstance(response, dict), f"Response must be dict, got {type(response)}"
    assert "success" in response, "Response missing 'success' field"
    assert isinstance(
        response["success"], bool
    ), f"success must be bool, got {type(response['success'])}"

    # Check for appropriate fields based on success value
    if response["success"]:
        assert "result" in response, "Success response must have 'result' field"
    else:
        assert "error" in response, "Error response must have 'error' field"

    assert "message" in response, "Response must have 'message' field"


def assert_response_contains(response: dict[str, Any], text: str) -> None:
    """Assert that a response result or message contains specific text.

    Args:
        response: The response dictionary
        text: Text that should appear in result or message

    Raises:
        AssertionError: If text not found in response

    Example:
        >>> result = await tool.hello_world("Alice")
        >>> assert_response_contains(result, "Alice")
    """
    assert_tool_response_format(response)

    result_str = str(response.get("result", ""))
    message_str = str(response.get("message", ""))

    assert (
        text in result_str or text in message_str
    ), f"'{text}' not found in response. Result: {result_str}, Message: {message_str}"
