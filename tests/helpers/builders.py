"""Test data builders for creating test fixtures.

This module provides builder functions for creating common test objects
with sensible defaults, making tests more readable and maintainable.
"""

from typing import Any

from agent.config import AgentConfig


def build_test_config(
    llm_provider: str = "openai",
    **kwargs: Any,
) -> AgentConfig:
    """Build a test configuration with sensible defaults.

    Args:
        llm_provider: LLM provider to use (default: "openai")
        **kwargs: Additional configuration overrides

    Returns:
        AgentConfig instance configured for testing

    Example:
        >>> config = build_test_config()
        >>> config = build_test_config(llm_provider="anthropic")
        >>> config = build_test_config(openai_model="gpt-4o")
    """
    defaults = {
        "openai": {
            "llm_provider": "openai",
            "openai_api_key": "test-key-openai",
            "openai_model": "gpt-5-mini",
        },
        "anthropic": {
            "llm_provider": "anthropic",
            "anthropic_api_key": "test-key-anthropic",
            "anthropic_model": "claude-haiku-4-5-20251001",
        },
        "azure": {
            "llm_provider": "azure",
            "azure_openai_endpoint": "https://test.openai.azure.com",
            "azure_openai_deployment": "gpt-5-codex",
            "azure_openai_api_version": "2024-10-01-preview",
        },
        "foundry": {
            "llm_provider": "foundry",
            "azure_project_endpoint": "https://test.ai.azure.com/api/projects/test",
            "azure_model_deployment": "gpt-4o",
        },
    }

    provider_defaults = defaults.get(llm_provider, defaults["openai"])
    config_dict = {**provider_defaults, **kwargs}

    return AgentConfig(**config_dict)


def build_success_response(result: Any, message: str = "") -> dict[str, Any]:
    """Build a success response in standard format.

    Args:
        result: The result value
        message: Optional message describing the success

    Returns:
        Success response dictionary

    Example:
        >>> response = build_success_response("Hello, World!", "Greeted successfully")
    """
    return {
        "success": True,
        "result": result,
        "message": message,
    }


def build_error_response(error: str, message: str) -> dict[str, Any]:
    """Build an error response in standard format.

    Args:
        error: Machine-readable error code
        message: Human-readable error message

    Returns:
        Error response dictionary

    Example:
        >>> response = build_error_response("invalid_input", "Input must be non-empty")
    """
    return {
        "success": False,
        "error": error,
        "message": message,
    }
