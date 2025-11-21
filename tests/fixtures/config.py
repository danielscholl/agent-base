"""Configuration fixtures for testing."""

import pytest

from agent.config.schema import AgentSettings


@pytest.fixture
def mock_openai_settings():
    """Create mock OpenAI configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["openai"]
    settings.providers.openai.api_key = "test-key"
    settings.providers.openai.model = "gpt-5-mini"
    return settings


@pytest.fixture
def mock_anthropic_settings():
    """Create mock Anthropic configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["anthropic"]
    settings.providers.anthropic.api_key = "test-key"
    settings.providers.anthropic.model = "claude-haiku-4-5-20251001"
    return settings


@pytest.fixture
def mock_azure_settings():
    """Create mock Azure OpenAI configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["azure"]
    settings.providers.azure.endpoint = "https://test-openai.openai.azure.com/"
    settings.providers.azure.deployment = "gpt-5-mini"
    settings.providers.azure.api_key = "test-key"
    return settings


@pytest.fixture
def mock_foundry_settings():
    """Create mock Azure AI Foundry configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["foundry"]
    settings.providers.foundry.project_endpoint = (
        "https://test-project.services.ai.azure.com/api/projects/test"
    )
    settings.providers.foundry.model_deployment = "gpt-4o"
    return settings


@pytest.fixture
def mock_gemini_settings():
    """Create mock Google Gemini configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["gemini"]
    settings.providers.gemini.api_key = "test-key"
    settings.providers.gemini.model = "gemini-2.0-flash-exp"
    return settings


@pytest.fixture
def mock_github_settings():
    """Create mock GitHub Models configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["github"]
    settings.providers.github.token = "test-token"
    settings.providers.github.model = "gpt-4o-mini"
    return settings


@pytest.fixture
def mock_local_settings():
    """Create mock local provider configuration."""
    settings = AgentSettings()
    settings.providers.enabled = ["local"]
    settings.providers.local.base_url = "http://localhost:8000"
    settings.providers.local.model = "ai/phi4"
    return settings


@pytest.fixture
def mock_settings(mock_openai_settings):
    """Default mock configuration (OpenAI)."""
    return mock_openai_settings


@pytest.fixture
def custom_prompt_file(tmp_path):
    """Create a temporary custom prompt file for testing.

    Yields:
        Path to temporary prompt file with custom content and placeholders
    """
    prompt_content = """# Custom Test Prompt

You are a test assistant.

Configuration:
- Model: {{MODEL}}
- Provider: {{PROVIDER}}
- Data Dir: {{DATA_DIR}}
- Session Dir: {{SESSION_DIR}}
- Memory: {{MEMORY_ENABLED}}

Be helpful and test-friendly."""

    prompt_file = tmp_path / "custom_prompt.md"
    prompt_file.write_text(prompt_content, encoding="utf-8")
    yield prompt_file


@pytest.fixture
def custom_prompt_settings(custom_prompt_file, mock_openai_settings):
    """Create settings with custom system prompt file.

    Args:
        custom_prompt_file: Path to custom prompt file
        mock_openai_settings: Base OpenAI settings

    Returns:
        AgentSettings with system_prompt_file configured
    """
    # Create a copy to avoid mutating the shared fixture
    settings = mock_openai_settings.model_copy(deep=True)
    settings.agent.system_prompt_file = str(custom_prompt_file)
    return settings
