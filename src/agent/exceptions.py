"""Custom exceptions for agent errors.

This module provides a hierarchy of exception classes for better error handling
and user-friendly error messages.
"""


class AgentError(Exception):
    """Base exception for all agent errors.

    This is the root of the exception hierarchy. All custom agent exceptions
    should inherit from this class.
    """

    pass


class ProviderAPIError(AgentError):
    """Provider API error (500, 503, 529).

    Raised when the LLM provider's API returns a server error, indicating
    a temporary issue on the provider's side.

    Attributes:
        provider: Provider name (anthropic, openai, azure, etc.)
        status_code: HTTP status code
        message: Error message
        request_id: Provider's request ID for debugging (optional)
        model: Model name used in the request (optional)
        original_error: Original exception from the provider SDK (optional)
    """

    def __init__(
        self,
        provider: str,
        status_code: int,
        message: str,
        request_id: str | None = None,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize ProviderAPIError.

        Args:
            provider: Provider name (anthropic, openai, azure, etc.)
            status_code: HTTP status code
            message: Error message
            request_id: Provider's request ID for debugging
            model: Model name used in the request
            original_error: Original exception from the provider SDK
        """
        self.provider = provider
        self.status_code = status_code
        self.request_id = request_id
        self.model = model
        self.original_error = original_error
        super().__init__(message)


class ProviderAuthError(AgentError):
    """Provider authentication error (401, 403).

    Raised when the provider rejects the API key or authentication credentials.

    Attributes:
        provider: Provider name (anthropic, openai, azure, etc.)
        status_code: HTTP status code
        message: Error message
        model: Model name used in the request (optional)
        original_error: Original exception from the provider SDK (optional)
    """

    def __init__(
        self,
        provider: str,
        status_code: int,
        message: str,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize ProviderAuthError.

        Args:
            provider: Provider name (anthropic, openai, azure, etc.)
            status_code: HTTP status code
            message: Error message
            model: Model name used in the request
            original_error: Original exception from the provider SDK
        """
        self.provider = provider
        self.status_code = status_code
        self.model = model
        self.original_error = original_error
        super().__init__(message)


class ProviderRateLimitError(AgentError):
    """Provider rate limit error (429).

    Raised when the provider's rate limit is exceeded.

    Attributes:
        provider: Provider name (anthropic, openai, azure, etc.)
        status_code: HTTP status code
        message: Error message
        retry_after: Seconds to wait before retrying (optional)
        model: Model name used in the request (optional)
        original_error: Original exception from the provider SDK (optional)
    """

    def __init__(
        self,
        provider: str,
        status_code: int,
        message: str,
        retry_after: int | None = None,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize ProviderRateLimitError.

        Args:
            provider: Provider name (anthropic, openai, azure, etc.)
            status_code: HTTP status code
            message: Error message
            retry_after: Seconds to wait before retrying
            model: Model name used in the request
            original_error: Original exception from the provider SDK
        """
        self.provider = provider
        self.status_code = status_code
        self.retry_after = retry_after
        self.model = model
        self.original_error = original_error
        super().__init__(message)


class ProviderModelNotFoundError(AgentError):
    """Provider model not found error (404).

    Raised when the specified model doesn't exist or isn't available.

    Attributes:
        provider: Provider name (anthropic, openai, azure, etc.)
        status_code: HTTP status code
        message: Error message
        model: Model name that wasn't found
        original_error: Original exception from the provider SDK (optional)
    """

    def __init__(
        self,
        provider: str,
        status_code: int,
        message: str,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize ProviderModelNotFoundError.

        Args:
            provider: Provider name (anthropic, openai, azure, etc.)
            status_code: HTTP status code
            message: Error message
            model: Model name that wasn't found
            original_error: Original exception from the provider SDK
        """
        self.provider = provider
        self.status_code = status_code
        self.model = model
        self.original_error = original_error
        super().__init__(message)


class ProviderTimeoutError(AgentError):
    """Provider timeout error.

    Raised when a request to the provider times out or has network issues.

    Attributes:
        provider: Provider name (anthropic, openai, azure, etc.)
        message: Error message
        model: Model name used in the request (optional)
        original_error: Original exception from the provider SDK (optional)
    """

    def __init__(
        self,
        provider: str,
        message: str,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize ProviderTimeoutError.

        Args:
            provider: Provider name (anthropic, openai, azure, etc.)
            message: Error message
            model: Model name used in the request
            original_error: Original exception from the provider SDK
        """
        self.provider = provider
        self.model = model
        self.original_error = original_error
        super().__init__(message)


class AgentConfigError(AgentError):
    """Agent configuration error.

    Raised when there's an issue with the agent's configuration.

    This is kept for backward compatibility but is not part of the provider
    error handling system.
    """

    pass
