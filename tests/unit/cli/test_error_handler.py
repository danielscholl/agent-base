"""Unit tests for agent.cli.error_handler module.

This module tests error classification and formatting for provider API errors.
It ensures that cryptic SDK exceptions are properly converted into user-friendly
error messages with actionable troubleshooting steps.
"""

from unittest.mock import Mock

import pytest

from agent.cli.error_handler import (
    classify_anthropic_error,
    classify_gemini_error,
    classify_openai_error,
    classify_provider_error,
    format_error,
    format_provider_api_error,
    format_provider_auth_error,
    format_provider_model_not_found_error,
    format_provider_rate_limit_error,
    format_provider_timeout_error,
)
from agent.config.schema import AgentSettings
from agent.exceptions import (
    ProviderAPIError,
    ProviderAuthError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_anthropic_config():
    """Mock AgentConfig for Anthropic provider."""
    config = Mock(spec=AgentSettings)
    config.llm_provider = "anthropic"
    config.anthropic_model = "claude-3-5-sonnet-20241022"
    return config


@pytest.fixture
def mock_openai_config():
    """Mock AgentConfig for OpenAI provider."""
    config = Mock(spec=AgentSettings)
    config.llm_provider = "openai"
    config.openai_model = "gpt-4o"
    return config


@pytest.fixture
def mock_azure_config():
    """Mock AgentConfig for Azure OpenAI provider."""
    config = Mock(spec=AgentSettings)
    config.llm_provider = "azure"
    config.azure_openai_deployment = "gpt-4o-deployment"
    return config


@pytest.fixture
def mock_github_config():
    """Mock AgentConfig for GitHub Models provider."""
    config = Mock(spec=AgentSettings)
    config.llm_provider = "github"
    config.github_model = "gpt-4o"
    return config


@pytest.fixture
def mock_gemini_config():
    """Mock AgentConfig for Gemini provider."""
    config = Mock(spec=AgentSettings)
    config.llm_provider = "gemini"
    config.gemini_model = "gemini-1.5-pro"
    return config


# ============================================================================
# Error Classification Tests - Anthropic
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestClassifyAnthropicError:
    """Tests for classify_anthropic_error function."""

    def test_classify_anthropic_500_error(self, mock_anthropic_config):
        """Test classification of Anthropic 500 Internal Server Error."""
        pytest.importorskip("anthropic")
        import anthropic

        # Mock APIStatusError with status 500
        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 500
        error.body = {"error": {"message": "Internal server error", "type": "api_error"}}
        error.request_id = "req_123456789"
        error.__str__ = Mock(return_value="Internal server error")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAPIError)
        assert result.provider == "anthropic"
        assert result.status_code == 500
        assert result.model == "claude-3-5-sonnet-20241022"
        assert result.request_id == "req_123456789"
        assert result.original_error is error

    def test_classify_anthropic_503_error(self, mock_anthropic_config):
        """Test classification of Anthropic 503 Service Unavailable."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 503
        error.body = {"error": {"message": "Service unavailable"}}
        error.request_id = None
        error.__str__ = Mock(return_value="Service unavailable")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAPIError)
        assert result.status_code == 503

    def test_classify_anthropic_529_error(self, mock_anthropic_config):
        """Test classification of Anthropic 529 Overloaded."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 529
        error.body = {"error": {"message": "Overloaded"}}
        error.request_id = "req_overload"
        error.__str__ = Mock(return_value="Overloaded")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAPIError)
        assert result.status_code == 529

    def test_classify_anthropic_401_error(self, mock_anthropic_config):
        """Test classification of Anthropic 401 Unauthorized."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 401
        error.body = {"error": {"message": "Invalid API key"}}
        error.__str__ = Mock(return_value="Invalid API key")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "anthropic"
        assert result.status_code == 401

    def test_classify_anthropic_403_error(self, mock_anthropic_config):
        """Test classification of Anthropic 403 Forbidden."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 403
        error.body = {"error": {"message": "Forbidden"}}
        error.__str__ = Mock(return_value="Forbidden")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAuthError)
        assert result.status_code == 403

    def test_classify_anthropic_429_error(self, mock_anthropic_config):
        """Test classification of Anthropic 429 Rate Limit."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 429
        error.body = {"error": {"message": "Rate limit exceeded"}}
        error.response = Mock()
        error.response.headers = {"retry-after": "60"}
        error.__str__ = Mock(return_value="Rate limit exceeded")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderRateLimitError)
        assert result.status_code == 429
        assert result.retry_after == 60

    def test_classify_anthropic_429_error_no_retry_after(self, mock_anthropic_config):
        """Test classification of Anthropic 429 without retry-after header."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 429
        error.body = {"error": {"message": "Rate limit exceeded"}}
        error.response = Mock()
        error.response.headers = {}
        error.__str__ = Mock(return_value="Rate limit exceeded")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderRateLimitError)
        assert result.retry_after is None

    def test_classify_anthropic_404_error(self, mock_anthropic_config):
        """Test classification of Anthropic 404 Not Found."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 404
        error.body = {"error": {"message": "Model not found"}}
        error.__str__ = Mock(return_value="Model not found")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderModelNotFoundError)
        assert result.status_code == 404

    def test_classify_anthropic_connection_error(self, mock_anthropic_config):
        """Test classification of Anthropic APIConnectionError."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIConnectionError)
        error.__str__ = Mock(return_value="Connection failed")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderTimeoutError)
        assert result.provider == "anthropic"
        assert result.model == "claude-3-5-sonnet-20241022"

    def test_classify_anthropic_error_without_config(self):
        """Test classification of Anthropic error without config."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 500
        error.body = {"error": {"message": "Internal server error"}}
        error.request_id = None
        error.__str__ = Mock(return_value="Internal server error")

        result = classify_anthropic_error(error, None)

        assert isinstance(result, ProviderAPIError)
        assert result.model is None

    def test_classify_anthropic_error_with_simple_body(self, mock_anthropic_config):
        """Test classification with simple string body (not dict)."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 500
        error.body = "Internal server error"
        error.request_id = None
        error.__str__ = Mock(return_value="Internal server error")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAPIError)

    def test_classify_anthropic_unknown_error_type(self, mock_anthropic_config):
        """Test classification of unknown Anthropic error type."""
        pytest.importorskip("anthropic")

        error = Exception("Generic error")

        result = classify_anthropic_error(error, mock_anthropic_config)

        assert result is None


# ============================================================================
# Error Classification Tests - OpenAI
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestClassifyOpenAIError:
    """Tests for classify_openai_error function."""

    def test_classify_openai_auth_error(self, mock_openai_config):
        """Test classification of OpenAI AuthenticationError."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.AuthenticationError)
        error.__str__ = Mock(return_value="Invalid API key")

        result = classify_openai_error(error, mock_openai_config)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "openai"
        assert result.status_code == 401
        assert result.model == "gpt-4o"

    def test_classify_openai_rate_limit_error(self, mock_openai_config):
        """Test classification of OpenAI RateLimitError."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.RateLimitError)
        error.__str__ = Mock(return_value="Rate limit exceeded")

        result = classify_openai_error(error, mock_openai_config)

        assert isinstance(result, ProviderRateLimitError)
        assert result.provider == "openai"
        assert result.status_code == 429

    def test_classify_openai_connection_error(self, mock_openai_config):
        """Test classification of OpenAI APIConnectionError."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.APIConnectionError)
        error.__str__ = Mock(return_value="Connection failed")

        result = classify_openai_error(error, mock_openai_config)

        assert isinstance(result, ProviderTimeoutError)
        assert result.provider == "openai"

    def test_classify_openai_500_error(self, mock_openai_config):
        """Test classification of OpenAI 500 error."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.APIStatusError)
        error.status_code = 500
        error.__str__ = Mock(return_value="Internal server error")

        result = classify_openai_error(error, mock_openai_config)

        assert isinstance(result, ProviderAPIError)
        assert result.status_code == 500

    def test_classify_openai_503_error(self, mock_openai_config):
        """Test classification of OpenAI 503 error."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.APIStatusError)
        error.status_code = 503
        error.__str__ = Mock(return_value="Service unavailable")

        result = classify_openai_error(error, mock_openai_config)

        assert isinstance(result, ProviderAPIError)
        assert result.status_code == 503

    def test_classify_openai_404_error(self, mock_openai_config):
        """Test classification of OpenAI 404 error."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.APIStatusError)
        error.status_code = 404
        error.__str__ = Mock(return_value="Model not found")

        result = classify_openai_error(error, mock_openai_config)

        assert isinstance(result, ProviderModelNotFoundError)
        assert result.status_code == 404

    def test_classify_azure_error(self, mock_azure_config):
        """Test classification of Azure OpenAI error."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.AuthenticationError)
        error.__str__ = Mock(return_value="Invalid credentials")

        result = classify_openai_error(error, mock_azure_config)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "azure"
        assert result.model == "gpt-4o-deployment"

    def test_classify_github_error(self, mock_github_config):
        """Test classification of GitHub Models error."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.RateLimitError)
        error.__str__ = Mock(return_value="Rate limit exceeded")

        result = classify_openai_error(error, mock_github_config)

        assert isinstance(result, ProviderRateLimitError)
        assert result.provider == "github"
        assert result.model == "gpt-4o"

    def test_classify_openai_error_without_config(self):
        """Test classification of OpenAI error without config."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.AuthenticationError)
        error.__str__ = Mock(return_value="Invalid API key")

        result = classify_openai_error(error, None)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "openai"
        assert result.model is None

    def test_classify_openai_unknown_error_type(self, mock_openai_config):
        """Test classification of unknown OpenAI error type."""
        pytest.importorskip("openai")

        error = Exception("Generic error")

        result = classify_openai_error(error, mock_openai_config)

        assert result is None


# ============================================================================
# Error Classification Tests - Gemini
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestClassifyGeminiError:
    """Tests for classify_gemini_error function."""

    def test_classify_gemini_unauthenticated_error(self, mock_gemini_config):
        """Test classification of Gemini Unauthenticated error."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.Unauthenticated)
        error.__str__ = Mock(return_value="Invalid API key")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "gemini"
        assert result.status_code == 401

    def test_classify_gemini_resource_exhausted_error(self, mock_gemini_config):
        """Test classification of Gemini ResourceExhausted error."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.ResourceExhausted)
        error.__str__ = Mock(return_value="Quota exceeded")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderRateLimitError)
        assert result.status_code == 429

    def test_classify_gemini_not_found_error(self, mock_gemini_config):
        """Test classification of Gemini NotFound error."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.NotFound)
        error.__str__ = Mock(return_value="Model not found")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderModelNotFoundError)
        assert result.status_code == 404

    def test_classify_gemini_internal_server_error(self, mock_gemini_config):
        """Test classification of Gemini InternalServerError."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.InternalServerError)
        error.__str__ = Mock(return_value="Internal server error")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderAPIError)
        assert result.status_code == 500

    def test_classify_gemini_service_unavailable_error(self, mock_gemini_config):
        """Test classification of Gemini ServiceUnavailable error."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.ServiceUnavailable)
        error.__str__ = Mock(return_value="Service unavailable")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderAPIError)
        assert result.status_code == 503

    def test_classify_gemini_deadline_exceeded_error(self, mock_gemini_config):
        """Test classification of Gemini DeadlineExceeded error."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.DeadlineExceeded)
        error.__str__ = Mock(return_value="Deadline exceeded")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderTimeoutError)
        assert result.provider == "gemini"

    def test_classify_gemini_aborted_error(self, mock_gemini_config):
        """Test classification of Gemini Aborted error."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.Aborted)
        error.__str__ = Mock(return_value="Aborted")

        result = classify_gemini_error(error, mock_gemini_config)

        assert isinstance(result, ProviderTimeoutError)

    def test_classify_gemini_unknown_error_type(self, mock_gemini_config):
        """Test classification of unknown Gemini error type."""
        pytest.importorskip("google.api_core.exceptions")

        error = Exception("Generic error")

        result = classify_gemini_error(error, mock_gemini_config)

        assert result is None


# ============================================================================
# Error Classification Tests - Dispatcher
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestClassifyProviderError:
    """Tests for classify_provider_error dispatcher function."""

    def test_classify_provider_error_anthropic(self, mock_anthropic_config):
        """Test dispatcher classifies Anthropic errors."""
        pytest.importorskip("anthropic")
        import anthropic

        error = Mock(spec=anthropic.APIStatusError)
        error.status_code = 500
        error.body = {"error": {"message": "Internal server error"}}
        error.request_id = None
        error.__str__ = Mock(return_value="Internal server error")

        result = classify_provider_error(error, mock_anthropic_config)

        assert isinstance(result, ProviderAPIError)
        assert result.provider == "anthropic"

    def test_classify_provider_error_openai(self, mock_openai_config):
        """Test dispatcher classifies OpenAI errors."""
        pytest.importorskip("openai")
        import openai

        error = Mock(spec=openai.AuthenticationError)
        error.__str__ = Mock(return_value="Invalid API key")

        result = classify_provider_error(error, mock_openai_config)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "openai"

    def test_classify_provider_error_gemini(self, mock_gemini_config):
        """Test dispatcher classifies Gemini errors."""
        pytest.importorskip("google.api_core.exceptions")
        from google.api_core import exceptions as google_exceptions

        error = Mock(spec=google_exceptions.Unauthenticated)
        error.__str__ = Mock(return_value="Invalid API key")

        result = classify_provider_error(error, mock_gemini_config)

        assert isinstance(result, ProviderAuthError)
        assert result.provider == "gemini"

    def test_classify_provider_error_unknown(self, mock_anthropic_config):
        """Test dispatcher returns None for unknown errors."""
        error = Exception("Generic error")

        result = classify_provider_error(error, mock_anthropic_config)

        assert result is None


# ============================================================================
# Error Formatting Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestFormatProviderAPIError:
    """Tests for format_provider_api_error function."""

    def test_format_provider_api_error_anthropic(self):
        """Test formatting of Anthropic API error."""
        error = ProviderAPIError(
            provider="anthropic",
            status_code=500,
            message="Internal server error",
            request_id="req_123",
            model="claude-3-5-sonnet-20241022",
        )

        result = format_provider_api_error(error)

        # Verify key components are present
        assert "Provider API Error" in result
        assert "Anthropic" in result
        assert "500" in result
        assert "Internal Server Error" in result
        assert "Troubleshooting:" in result
        assert "Try again in a few minutes" in result
        assert "agent --provider" in result
        assert "status.anthropic.com" in result
        assert "req_123" in result
        assert "claude-3-5-sonnet-20241022" in result

    def test_format_provider_api_error_529_overloaded(self):
        """Test formatting of Anthropic 529 Overloaded error."""
        error = ProviderAPIError(
            provider="anthropic",
            status_code=529,
            message="Overloaded",
        )

        result = format_provider_api_error(error)

        assert "529" in result
        assert "Overloaded" in result

    def test_format_provider_api_error_missing_metadata(self):
        """Test formatting with missing request_id and model."""
        error = ProviderAPIError(
            provider="openai",
            status_code=503,
            message="Service unavailable",
        )

        result = format_provider_api_error(error)

        assert "OpenAI" in result
        assert "503" in result
        assert "Service unavailable" not in result  # Message is for exception, not display

    def test_format_provider_api_error_no_alternatives(self):
        """Test formatting when provider has no alternatives."""
        error = ProviderAPIError(
            provider="unknown_provider",
            status_code=500,
            message="Error",
        )

        result = format_provider_api_error(error)

        # Should still format, but without alternatives
        assert "Provider API Error" in result

    def test_format_provider_api_error_no_status_page(self):
        """Test formatting when provider has no status page."""
        error = ProviderAPIError(
            provider="local",
            status_code=500,
            message="Error",
        )

        result = format_provider_api_error(error)

        assert "Provider API Error" in result
        # Should not include status page link
        assert "status." not in result.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestFormatProviderAuthError:
    """Tests for format_provider_auth_error function."""

    def test_format_provider_auth_error_anthropic(self):
        """Test formatting of Anthropic authentication error."""
        error = ProviderAuthError(
            provider="anthropic",
            status_code=401,
            message="Invalid API key",
            model="claude-3-5-sonnet-20241022",
        )

        result = format_provider_auth_error(error)

        assert "Authentication Error" in result
        assert "Anthropic" in result
        assert "console.anthropic.com" in result
        assert "agent config provider anthropic" in result
        assert "ANTHROPIC_API_KEY" in result
        assert "401" in result

    def test_format_provider_auth_error_openai(self):
        """Test formatting of OpenAI authentication error."""
        error = ProviderAuthError(
            provider="openai",
            status_code=401,
            message="Invalid API key",
        )

        result = format_provider_auth_error(error)

        assert "OpenAI" in result
        assert "platform.openai.com" in result
        assert "OPENAI_API_KEY" in result

    def test_format_provider_auth_error_azure(self):
        """Test formatting of Azure authentication error."""
        error = ProviderAuthError(
            provider="azure",
            status_code=401,
            message="Invalid credentials",
        )

        result = format_provider_auth_error(error)

        assert "Azure OpenAI" in result
        assert "portal.azure.com" in result
        assert "AZURE_OPENAI_API_KEY" in result

    def test_format_provider_auth_error_no_console_url(self):
        """Test formatting when provider has no console URL."""
        error = ProviderAuthError(
            provider="unknown_provider",
            status_code=401,
            message="Invalid credentials",
        )

        result = format_provider_auth_error(error)

        assert "Authentication Error" in result
        assert "agent config provider unknown_provider" in result


@pytest.mark.unit
@pytest.mark.cli
class TestFormatProviderRateLimitError:
    """Tests for format_provider_rate_limit_error function."""

    def test_format_provider_rate_limit_error_with_retry_after(self):
        """Test formatting of rate limit error with retry_after."""
        error = ProviderRateLimitError(
            provider="anthropic",
            status_code=429,
            message="Rate limit exceeded",
            retry_after=60,
            model="claude-3-5-sonnet-20241022",
        )

        result = format_provider_rate_limit_error(error)

        assert "Rate Limit Exceeded" in result
        assert "Anthropic" in result
        assert "60 seconds" in result
        assert "agent --provider" in result
        assert "upgrading your" in result  # Upgrade suggestion

    def test_format_provider_rate_limit_error_without_retry_after(self):
        """Test formatting of rate limit error without retry_after."""
        error = ProviderRateLimitError(
            provider="openai",
            status_code=429,
            message="Rate limit exceeded",
        )

        result = format_provider_rate_limit_error(error)

        assert "Rate Limit Exceeded" in result
        assert "Wait a few minutes" in result
        assert "60 seconds" not in result

    def test_format_provider_rate_limit_error_no_upgrade_suggestion(self):
        """Test formatting for providers without upgrade suggestion."""
        error = ProviderRateLimitError(
            provider="github",
            status_code=429,
            message="Rate limit exceeded",
        )

        result = format_provider_rate_limit_error(error)

        assert "Rate Limit Exceeded" in result
        assert "upgrading" not in result.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestFormatProviderModelNotFoundError:
    """Tests for format_provider_model_not_found_error function."""

    def test_format_provider_model_not_found_error(self):
        """Test formatting of model not found error."""
        error = ProviderModelNotFoundError(
            provider="anthropic",
            status_code=404,
            message="Model not found",
            model="claude-invalid-model",
        )

        result = format_provider_model_not_found_error(error)

        assert "Model Not Found" in result
        assert "Anthropic" in result
        assert "claude-invalid-model" in result
        assert "Check your model name" in result
        assert "agent config provider anthropic" in result
        assert "404" in result

    def test_format_provider_model_not_found_error_no_model(self):
        """Test formatting when model name is None."""
        error = ProviderModelNotFoundError(
            provider="openai",
            status_code=404,
            message="Model not found",
        )

        result = format_provider_model_not_found_error(error)

        assert "Model Not Found" in result
        assert "unknown" in result


@pytest.mark.unit
@pytest.mark.cli
class TestFormatProviderTimeoutError:
    """Tests for format_provider_timeout_error function."""

    def test_format_provider_timeout_error(self):
        """Test formatting of timeout error."""
        error = ProviderTimeoutError(
            provider="anthropic",
            message="Connection timeout",
            model="claude-3-5-sonnet-20241022",
        )

        result = format_provider_timeout_error(error)

        assert "Network Error" in result
        assert "Anthropic" in result
        assert "Check your internet connection" in result
        assert "Try again in a moment" in result
        assert "agent --provider" in result
        assert "claude-3-5-sonnet-20241022" in result

    def test_format_provider_timeout_error_no_alternatives(self):
        """Test formatting when provider has no alternatives."""
        error = ProviderTimeoutError(
            provider="unknown_provider",
            message="Connection timeout",
        )

        result = format_provider_timeout_error(error)

        assert "Network Error" in result
        assert "Check your internet connection" in result


@pytest.mark.unit
@pytest.mark.cli
class TestFormatError:
    """Tests for format_error dispatcher function."""

    def test_format_error_provider_api_error(self):
        """Test dispatcher formats ProviderAPIError."""
        error = ProviderAPIError(
            provider="anthropic",
            status_code=500,
            message="Internal server error",
        )

        result = format_error(error)

        assert "Provider API Error" in result

    def test_format_error_provider_auth_error(self):
        """Test dispatcher formats ProviderAuthError."""
        error = ProviderAuthError(
            provider="openai",
            status_code=401,
            message="Invalid API key",
        )

        result = format_error(error)

        assert "Authentication Error" in result

    def test_format_error_provider_rate_limit_error(self):
        """Test dispatcher formats ProviderRateLimitError."""
        error = ProviderRateLimitError(
            provider="anthropic",
            status_code=429,
            message="Rate limit exceeded",
        )

        result = format_error(error)

        assert "Rate Limit Exceeded" in result

    def test_format_error_provider_model_not_found_error(self):
        """Test dispatcher formats ProviderModelNotFoundError."""
        error = ProviderModelNotFoundError(
            provider="openai",
            status_code=404,
            message="Model not found",
            model="invalid-model",
        )

        result = format_error(error)

        assert "Model Not Found" in result

    def test_format_error_provider_timeout_error(self):
        """Test dispatcher formats ProviderTimeoutError."""
        error = ProviderTimeoutError(
            provider="gemini",
            message="Connection timeout",
        )

        result = format_error(error)

        assert "Network Error" in result

    def test_format_error_unknown_agent_error(self):
        """Test dispatcher handles unknown AgentError types."""
        from agent.exceptions import AgentError

        error = AgentError("Unknown error")

        result = format_error(error)

        assert "Error:" in result
        assert "Unknown error" in result
