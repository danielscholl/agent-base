"""Shared response helper functions for tools and managers.

This module provides standardized response formatting used across toolsets
and memory managers. All tools and managers should use these helpers to
ensure consistent response formats for the agent to consume.
"""

from typing import Any


def create_success_response(result: Any, message: str = "") -> dict:
    """Create standardized success response.

    All tools and managers should return responses in this format for consistency.
    This makes it easy for the agent to handle results uniformly.

    Args:
        result: Operation result (can be any type)
        message: Optional success message for logging/display

    Returns:
        Structured response dict with success=True

    Example:
        >>> response = create_success_response(
        ...     result="Hello, World!",
        ...     message="Greeting generated"
        ... )
        >>> response
        {'success': True, 'result': 'Hello, World!', 'message': 'Greeting generated'}
    """
    return {
        "success": True,
        "result": result,
        "message": message,
    }


def create_error_response(error: str, message: str) -> dict:
    """Create standardized error response.

    Tools and managers should use this when they encounter errors rather than
    raising exceptions. This allows the agent to handle errors gracefully and
    provide better feedback.

    Args:
        error: Machine-readable error code (e.g., "resource_not_found")
        message: Human-friendly error message

    Returns:
        Structured response dict with success=False

    Example:
        >>> response = create_error_response(
        ...     error="file_not_found",
        ...     message="The file 'data.txt' does not exist"
        ... )
        >>> response
        {'success': False, 'error': 'file_not_found', 'message': '...'}
    """
    return {
        "success": False,
        "error": error,
        "message": message,
    }
