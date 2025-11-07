"""Custom exceptions for Agent.

This module defines a hierarchy of domain-specific exceptions that provide
clear error handling throughout the agent system.

Exception Hierarchy:
    AgentError (base)
    ├── ConfigurationError
    ├── ToolError
    │   ├── ToolNotFoundError
    │   └── ToolExecutionError
    └── APIError
        └── ResourceNotFoundError
"""


class AgentError(Exception):
    """Base exception for all Agent errors.

    All custom exceptions in the agent system inherit from this base class,
    allowing for catch-all error handling when needed.

    Example:
        >>> try:
        ...     # some agent operation
        ...     pass
        ... except AgentError as e:
        ...     print(f"Agent error: {e}")
    """

    pass


class ConfigurationError(AgentError):
    """Configuration validation or loading errors.

    Raised when configuration is invalid, missing required fields, or
    cannot be loaded from the environment.

    Example:
        >>> raise ConfigurationError("Missing OPENAI_API_KEY environment variable")
    """

    pass


class ToolError(AgentError):
    """Base exception for tool-related errors.

    Parent class for all tool execution and registration errors.
    """

    pass


class ToolNotFoundError(ToolError):
    """Tool not found in registry.

    Raised when attempting to use or invoke a tool that hasn't been
    registered with the agent.

    Example:
        >>> raise ToolNotFoundError("Tool 'search_database' not found")
    """

    pass


class ToolExecutionError(ToolError):
    """Tool execution failed.

    Raised when a tool encounters an error during execution. The error
    message should include details about what went wrong.

    Example:
        >>> raise ToolExecutionError("Failed to connect to API: timeout")
    """

    pass


class APIError(AgentError):
    """API integration errors.

    Raised when external API calls fail or return unexpected responses.
    Future tool integrations will use this for API-related failures.

    Example:
        >>> raise APIError("GitHub API rate limit exceeded")
    """

    pass


class ResourceNotFoundError(APIError):
    """Resource not found in external system.

    Raised when an API request succeeds but the requested resource
    doesn't exist (e.g., 404 responses).

    Example:
        >>> raise ResourceNotFoundError("Repository 'user/repo' not found")
    """

    pass
