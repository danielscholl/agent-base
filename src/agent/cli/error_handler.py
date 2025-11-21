"""Error handler for provider API errors.

This module provides error classification, formatting, and display for LLM provider
API errors. It converts cryptic SDK exceptions into user-friendly error messages
with actionable troubleshooting steps.
"""

import logging

from agent.config.schema import AgentSettings
from agent.exceptions import (
    AgentError,
    ProviderAPIError,
    ProviderAuthError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = logging.getLogger(__name__)


def classify_anthropic_error(
    error: Exception, config: AgentSettings | None = None
) -> AgentError | None:
    """Classify Anthropic SDK exceptions into our exception types.

    Args:
        error: Exception from Anthropic SDK
        config: Agent configuration (for model name)

    Returns:
        Classified AgentError or None if can't classify
    """
    try:
        # Import anthropic module to check exception types
        import anthropic
    except ImportError:
        return None

    model = config.anthropic_model if config else None

    # Check for APIStatusError (HTTP errors)
    if isinstance(error, anthropic.APIStatusError):
        status_code = error.status_code
        message = str(error)
        request_id = getattr(error, "request_id", None)

        # Extract error details from response body if available
        if hasattr(error, "body") and isinstance(error.body, dict):
            body = error.body
            if "error" in body and isinstance(body["error"], dict):
                error_dict = body["error"]
                message = error_dict.get("message", message)

        # Classify by status code
        if status_code in (500, 503, 529):  # 529 is Anthropic's overloaded status
            return ProviderAPIError(
                provider="anthropic",
                status_code=status_code,
                message=message,
                request_id=request_id,
                model=model,
                original_error=error,
            )
        elif status_code in (401, 403):
            return ProviderAuthError(
                provider="anthropic",
                status_code=status_code,
                message=message,
                model=model,
                original_error=error,
            )
        elif status_code == 429:
            retry_after = getattr(error.response, "headers", {}).get("retry-after")
            retry_after_int = int(retry_after) if retry_after and retry_after.isdigit() else None
            return ProviderRateLimitError(
                provider="anthropic",
                status_code=status_code,
                message=message,
                retry_after=retry_after_int,
                model=model,
                original_error=error,
            )
        elif status_code == 404:
            return ProviderModelNotFoundError(
                provider="anthropic",
                status_code=status_code,
                message=message,
                model=model,
                original_error=error,
            )

    # Check for connection errors (network issues, timeouts)
    elif isinstance(error, anthropic.APIConnectionError):
        return ProviderTimeoutError(
            provider="anthropic",
            message=str(error),
            model=model,
            original_error=error,
        )

    return None


def classify_openai_error(
    error: Exception, config: AgentSettings | None = None
) -> AgentError | None:
    """Classify OpenAI SDK exceptions into our exception types.

    Args:
        error: Exception from OpenAI SDK
        config: Agent configuration (for model name)

    Returns:
        Classified AgentError or None if can't classify
    """
    try:
        # Import openai module to check exception types
        import openai
    except ImportError:
        return None

    # Determine model based on provider
    model = None
    if config:
        if config.llm_provider == "openai":
            model = config.openai_model
        elif config.llm_provider == "azure":
            model = config.azure_openai_deployment
        elif config.llm_provider == "github":
            model = config.github_model

    provider = config.llm_provider if config else "openai"

    # Check for specific OpenAI error types
    if isinstance(error, openai.AuthenticationError):
        return ProviderAuthError(
            provider=provider,
            status_code=401,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(error, openai.RateLimitError):
        return ProviderRateLimitError(
            provider=provider,
            status_code=429,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(error, openai.APIConnectionError):
        return ProviderTimeoutError(
            provider=provider,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(error, openai.APIStatusError):
        status_code = error.status_code
        message = str(error)

        if status_code in (500, 503):
            return ProviderAPIError(
                provider=provider,
                status_code=status_code,
                message=message,
                model=model,
                original_error=error,
            )
        elif status_code == 404:
            return ProviderModelNotFoundError(
                provider=provider,
                status_code=status_code,
                message=message,
                model=model,
                original_error=error,
            )

    return None


def classify_gemini_error(
    error: Exception, config: AgentSettings | None = None
) -> AgentError | None:
    """Classify Google Gemini exceptions into our exception types.

    Args:
        error: Exception from Google SDK
        config: Agent configuration (for model name)

    Returns:
        Classified AgentError or None if can't classify
    """
    try:
        # Import google.api_core for exception types
        from google.api_core import exceptions as google_exceptions
    except ImportError:
        return None

    model = config.gemini_model if config else None

    # Check for specific Google API exceptions
    if isinstance(error, google_exceptions.Unauthenticated):
        return ProviderAuthError(
            provider="gemini",
            status_code=401,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(error, google_exceptions.ResourceExhausted):
        return ProviderRateLimitError(
            provider="gemini",
            status_code=429,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(error, google_exceptions.NotFound):
        return ProviderModelNotFoundError(
            provider="gemini",
            status_code=404,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(
        error, (google_exceptions.InternalServerError, google_exceptions.ServiceUnavailable)
    ):
        status_code = 500 if isinstance(error, google_exceptions.InternalServerError) else 503
        return ProviderAPIError(
            provider="gemini",
            status_code=status_code,
            message=str(error),
            model=model,
            original_error=error,
        )
    elif isinstance(error, (google_exceptions.DeadlineExceeded, google_exceptions.Aborted)):
        return ProviderTimeoutError(
            provider="gemini",
            message=str(error),
            model=model,
            original_error=error,
        )

    return None


def classify_provider_error(
    error: Exception, config: AgentSettings | None = None
) -> AgentError | None:
    """Classify any provider exception into our exception types.

    This is the main dispatch function that tries all provider-specific classifiers.

    Args:
        error: Exception from any provider SDK
        config: Agent configuration (for provider and model info)

    Returns:
        Classified AgentError or None if can't classify
    """
    # Try Anthropic classifier
    classified = classify_anthropic_error(error, config)
    if classified:
        return classified

    # Try OpenAI classifier (handles openai, azure, github)
    classified = classify_openai_error(error, config)
    if classified:
        return classified

    # Try Gemini classifier
    classified = classify_gemini_error(error, config)
    if classified:
        return classified

    # Unknown error - can't classify
    return None


# ============================================================================
# Error Formatting
# ============================================================================


# Provider status pages
PROVIDER_STATUS_PAGES = {
    "anthropic": "https://status.anthropic.com",
    "openai": "https://status.openai.com",
    "azure": "https://status.azure.com",
    "gemini": "https://status.cloud.google.com",
    "github": "https://www.githubstatus.com",
    "local": None,
    "foundry": "https://status.azure.com",
}

# Alternative providers for suggestions
PROVIDER_ALTERNATIVES = {
    "anthropic": ["openai", "github"],
    "openai": ["anthropic", "github"],
    "azure": ["anthropic", "openai"],
    "gemini": ["anthropic", "openai"],
    "github": ["anthropic", "openai"],
    "local": ["github", "anthropic"],
    "foundry": ["anthropic", "openai"],
}

# Provider console URLs for API keys
PROVIDER_CONSOLE_URLS = {
    "anthropic": "https://console.anthropic.com/settings/keys",
    "openai": "https://platform.openai.com/api-keys",
    "azure": "https://portal.azure.com",
    "gemini": "https://makersuite.google.com/app/apikey",
    "github": "https://github.com/settings/tokens",
}


def _get_provider_display_name(provider: str) -> str:
    """Get user-friendly provider display name.

    Args:
        provider: Provider name (anthropic, openai, etc.)

    Returns:
        Display name (Anthropic, OpenAI, etc.)
    """
    display_names = {
        "anthropic": "Anthropic",
        "openai": "OpenAI",
        "azure": "Azure OpenAI",
        "gemini": "Google Gemini",
        "github": "GitHub Models",
        "local": "Local (Docker)",
        "foundry": "Azure AI Foundry",
    }
    return display_names.get(provider, provider.title())


def format_provider_api_error(error: ProviderAPIError) -> str:
    """Format a provider API error (500, 503, 529) with troubleshooting steps.

    Args:
        error: ProviderAPIError instance

    Returns:
        Formatted error message with Rich markup
    """
    provider_display = _get_provider_display_name(error.provider)
    status_name = "Overloaded" if error.status_code == 529 else "Internal Server Error"

    lines = [
        f"[bold red]Provider API Error ({provider_display})[/bold red]",
        "",
        f"The {provider_display} API returned a {error.status_code} {status_name}.",
        "This is a temporary issue on the provider's side.",
        "",
        "[bold]Troubleshooting:[/bold]",
        "  • Try again in a few minutes",
    ]

    # Add provider alternatives
    alternatives = PROVIDER_ALTERNATIVES.get(error.provider, [])
    if alternatives:
        lines.append("  • Switch to a different provider:")
        lines.append(f"    [cyan]agent --provider {alternatives[0]}[/cyan]")

    # Add status page link
    status_url = PROVIDER_STATUS_PAGES.get(error.provider)
    if status_url:
        lines.append(f"  • Check status: [link]{status_url}[/link]")

    lines.append("")
    lines.append("[dim]Technical Details:[/dim]")
    lines.append(f"[dim]  Status: {error.status_code} {status_name}[/dim]")
    if error.model:
        lines.append(f"[dim]  Model: {error.model}[/dim]")
    if error.request_id:
        lines.append(f"[dim]  Request ID: {error.request_id}[/dim]")

    return "\n".join(lines)


def format_provider_auth_error(error: ProviderAuthError) -> str:
    """Format a provider authentication error (401, 403) with fix instructions.

    Args:
        error: ProviderAuthError instance

    Returns:
        Formatted error message with Rich markup
    """
    provider_display = _get_provider_display_name(error.provider)

    lines = [
        f"[bold red]Authentication Error ({provider_display})[/bold red]",
        "",
        f"The {provider_display} API rejected your API key or credentials.",
        "",
        "[bold]Fix:[/bold]",
    ]

    # Provider-specific instructions
    console_url = PROVIDER_CONSOLE_URLS.get(error.provider)
    if console_url:
        lines.append("  1. Get your API key from:")
        lines.append(f"     [link]{console_url}[/link]")

    lines.append("  2. Configure it:")
    lines.append(f"     [cyan]agent config provider {error.provider}[/cyan]")

    # Environment variable option
    env_var_names = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "azure": "AZURE_OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "github": "GITHUB_TOKEN",
    }
    env_var = env_var_names.get(error.provider)
    if env_var:
        lines.append("  3. Or set environment variable:")
        lines.append(f"     [cyan]export {env_var}=your-key-here[/cyan]")

    lines.append("")
    lines.append("[dim]Technical Details:[/dim]")
    lines.append(f"[dim]  Status: {error.status_code} Unauthorized[/dim]")
    if error.model:
        lines.append(f"[dim]  Model: {error.model}[/dim]")

    return "\n".join(lines)


def format_provider_rate_limit_error(error: ProviderRateLimitError) -> str:
    """Format a provider rate limit error (429) with retry guidance.

    Args:
        error: ProviderRateLimitError instance

    Returns:
        Formatted error message with Rich markup
    """
    provider_display = _get_provider_display_name(error.provider)

    lines = [
        f"[bold yellow]Rate Limit Exceeded ({provider_display})[/bold yellow]",
        "",
        f"You've exceeded {provider_display}'s rate limit.",
        "",
        "[bold]What to do:[/bold]",
    ]

    if error.retry_after:
        lines.append(f"  • Wait {error.retry_after} seconds before retrying")
    else:
        lines.append("  • Wait a few minutes before retrying")

    # Add provider alternatives
    alternatives = PROVIDER_ALTERNATIVES.get(error.provider, [])
    if alternatives:
        lines.append("  • Switch to a different provider:")
        lines.append(f"    [cyan]agent --provider {alternatives[0]}[/cyan]")

    # Upgrade suggestion (if applicable)
    if error.provider in ("anthropic", "openai"):
        lines.append(f"  • Consider upgrading your {provider_display} plan")

    lines.append("")
    lines.append("[dim]Technical Details:[/dim]")
    lines.append("[dim]  Status: 429 Too Many Requests[/dim]")
    if error.model:
        lines.append(f"[dim]  Model: {error.model}[/dim]")

    return "\n".join(lines)


def format_provider_model_not_found_error(error: ProviderModelNotFoundError) -> str:
    """Format a provider model not found error (404) with model suggestions.

    Args:
        error: ProviderModelNotFoundError instance

    Returns:
        Formatted error message with Rich markup
    """
    provider_display = _get_provider_display_name(error.provider)

    lines = [
        f"[bold red]Model Not Found ({provider_display})[/bold red]",
        "",
        f"The model '{error.model or 'unknown'}' is not available on {provider_display}.",
        "",
        "[bold]Fix:[/bold]",
        "  • Check your model name for typos",
        "  • Use the correct model for your provider:",
        f"    [cyan]agent config provider {error.provider}[/cyan]",
        "  • See documentation for valid model names",
    ]

    lines.append("")
    lines.append("[dim]Technical Details:[/dim]")
    lines.append("[dim]  Status: 404 Not Found[/dim]")
    if error.model:
        lines.append(f"[dim]  Invalid Model: {error.model}[/dim]")

    return "\n".join(lines)


def format_provider_timeout_error(error: ProviderTimeoutError) -> str:
    """Format a provider timeout/network error with troubleshooting steps.

    Args:
        error: ProviderTimeoutError instance

    Returns:
        Formatted error message with Rich markup
    """
    provider_display = _get_provider_display_name(error.provider)

    lines = [
        f"[bold red]Network Error ({provider_display})[/bold red]",
        "",
        f"Failed to connect to {provider_display} API.",
        "",
        "[bold]Troubleshooting:[/bold]",
        "  • Check your internet connection",
        "  • Try again in a moment",
        "  • Verify your network allows API access",
    ]

    # Add provider alternatives
    alternatives = PROVIDER_ALTERNATIVES.get(error.provider, [])
    if alternatives:
        lines.append("  • Try a different provider:")
        lines.append(f"    [cyan]agent --provider {alternatives[0]}[/cyan]")

    lines.append("")
    lines.append("[dim]Technical Details:[/dim]")
    lines.append("[dim]  Error: Connection timeout[/dim]")
    if error.model:
        lines.append(f"[dim]  Model: {error.model}[/dim]")

    return "\n".join(lines)


def format_error(error: AgentError) -> str:
    """Format any AgentError into a user-friendly message.

    This is the main dispatch function for error formatting.

    Args:
        error: AgentError instance

    Returns:
        Formatted error message with Rich markup
    """
    if isinstance(error, ProviderAPIError):
        return format_provider_api_error(error)
    elif isinstance(error, ProviderAuthError):
        return format_provider_auth_error(error)
    elif isinstance(error, ProviderRateLimitError):
        return format_provider_rate_limit_error(error)
    elif isinstance(error, ProviderModelNotFoundError):
        return format_provider_model_not_found_error(error)
    elif isinstance(error, ProviderTimeoutError):
        return format_provider_timeout_error(error)
    else:
        # Fallback for unknown AgentError types
        return f"[bold red]Error:[/bold red] {str(error)}"
