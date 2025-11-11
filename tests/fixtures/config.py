"""Configuration fixtures for testing."""

import pytest

from agent.config import AgentConfig


@pytest.fixture
def mock_openai_config():
    """Create mock OpenAI configuration."""
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
    )


@pytest.fixture
def mock_anthropic_config():
    """Create mock Anthropic configuration."""
    return AgentConfig(
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        anthropic_model="claude-haiku-4-5-20251001",
    )


@pytest.fixture
def mock_azure_foundry_config():
    """Create mock Azure AI Foundry configuration."""
    return AgentConfig(
        llm_provider="foundry",
        azure_project_endpoint="https://test-project.services.ai.azure.com/api/projects/test",
        azure_model_deployment="gpt-4o",
    )


@pytest.fixture
def mock_config(mock_openai_config):
    """Default mock configuration (OpenAI)."""
    return mock_openai_config


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
def custom_prompt_config(custom_prompt_file):
    """Create config with custom system prompt file.

    Args:
        custom_prompt_file: Path to custom prompt file

    Returns:
        AgentConfig with system_prompt_file set
    """
    config = AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-5-mini",
        system_prompt_file=str(custom_prompt_file),
    )
    return config
