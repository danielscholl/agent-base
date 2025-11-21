"""Base class for Agent toolsets.

This module provides the abstract base class for creating toolsets. Toolsets
encapsulate related tools with shared dependencies, avoiding global state and
enabling dependency injection for testing.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from agent.config import AgentConfig
from agent.utils.responses import create_error_response, create_success_response


class AgentToolset(ABC):
    """Base class for Agent toolsets.

    Toolsets encapsulate related tools with shared dependencies.
    This avoids global state and enables dependency injection for testing.

    Each toolset receives an AgentConfig instance with all necessary
    configuration, making it easy to mock in tests.

    Example:
        >>> class MyTools(AgentToolset):
        ...     def get_tools(self):
        ...         return [self.my_tool]
        ...
        ...     async def my_tool(self, arg: str) -> dict:
        ...         return self._create_success_response(
        ...             result=f"Processed: {arg}",
        ...             message="Tool executed successfully"
        ...         )
    """

    def __init__(self, config: AgentConfig):
        """Initialize toolset with configuration.

        Args:
            config: Agent configuration with LLM settings and paths

        Example:
            >>> config = AgentConfig.from_env()
            >>> tools = HelloTools(config)
        """
        self.config = config

    @abstractmethod
    def get_tools(self) -> list[Callable]:
        """Get list of tool functions.

        Subclasses must implement this method to return their tool functions.
        Tools should be async callables with proper type hints and docstrings
        for LLM consumption.

        Returns:
            List of callable tool functions

        Example:
            >>> def get_tools(self):
            ...     return [self.tool1, self.tool2]
        """
        pass

    def _create_success_response(self, result: Any, message: str = "") -> dict:
        """Create standardized success response.

        All tools should return responses in this format for consistency.
        This makes it easy for the agent to handle tool results uniformly.

        Args:
            result: Tool execution result (can be any type)
            message: Optional success message for logging/display

        Returns:
            Structured response dict with success=True

        Example:
            >>> response = self._create_success_response(
            ...     result="Hello, World!",
            ...     message="Greeting generated"
            ... )
            >>> response
            {'success': True, 'result': 'Hello, World!', 'message': 'Greeting generated'}
        """
        return create_success_response(result, message)

    def _create_error_response(self, error: str, message: str) -> dict:
        """Create standardized error response.

        Tools should use this when they encounter errors rather than raising
        exceptions. This allows the agent to handle errors gracefully and
        provide better feedback.

        Args:
            error: Machine-readable error code (e.g., "resource_not_found")
            message: Human-friendly error message

        Returns:
            Structured response dict with success=False

        Example:
            >>> response = self._create_error_response(
            ...     error="invalid_input",
            ...     message="Name cannot be empty"
            ... )
            >>> response
            {'success': False, 'error': 'invalid_input', 'message': 'Name cannot be empty'}
        """
        return create_error_response(error, message)
