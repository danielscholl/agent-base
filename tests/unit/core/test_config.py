"""Unit tests for agent.config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


@pytest.mark.unit
@pytest.mark.config
class TestAgentConfig:
    """Tests for AgentConfig class."""

    def test_from_env_defaults_to_local(self):
        """Test from_env defaults to Local provider when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            assert config.llm_provider == "local"
            assert config.local_model == "ai/phi4"
            assert config.local_base_url == "http://localhost:12434/engines/llama.cpp/v1"

    def test_from_env_loads_openai_config(self):
        """Test from_env loads OpenAI configuration with AGENT_MODEL override."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key-123",
                "AGENT_MODEL": "gpt-4-turbo",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "openai"
            assert config.openai_api_key == "test-key-123"
            assert config.openai_model == "gpt-4-turbo"

    def test_from_env_loads_anthropic_config(self):
        """Test from_env loads Anthropic configuration with AGENT_MODEL override."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "sk-ant-test-456",
                "AGENT_MODEL": "claude-opus-4-20250514",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "anthropic"
            assert config.anthropic_api_key == "sk-ant-test-456"
            assert config.anthropic_model == "claude-opus-4-20250514"

    def test_from_env_loads_azure_foundry_config(self):
        """Test from_env loads Azure AI Foundry configuration from environment."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "foundry",
                "AZURE_PROJECT_ENDPOINT": "https://test.ai.azure.com/api/projects/test",
                "AZURE_MODEL_DEPLOYMENT": "gpt-4o",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "foundry"
            assert config.azure_project_endpoint == "https://test.ai.azure.com/api/projects/test"
            assert config.azure_model_deployment == "gpt-4o"

    def test_from_env_sets_default_data_directory(self):
        """Test from_env sets default agent data directory."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            expected_dir = Path.home() / ".agent"
            assert config.agent_data_dir == expected_dir
            assert config.agent_session_dir == expected_dir / "sessions"

    def test_from_env_respects_custom_data_directory(self):
        """Test from_env uses custom AGENT_DATA_DIR when specified."""
        with patch.dict(os.environ, {"AGENT_DATA_DIR": "/custom/path"}, clear=True):
            config = AgentConfig.from_env()

            assert config.agent_data_dir == Path("/custom/path")
            assert config.agent_session_dir == Path("/custom/path/sessions")

    def test_validate_openai_success(self):
        """Test validate succeeds for OpenAI with API key."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        # Should not raise
        config.validate()

    def test_validate_openai_missing_api_key(self):
        """Test validate fails for OpenAI without API key."""
        config = AgentConfig(llm_provider="openai")

        with pytest.raises(ValueError, match="OpenAI provider requires API key"):
            config.validate()

    def test_validate_anthropic_success(self):
        """Test validate succeeds for Anthropic with API key."""
        config = AgentConfig(llm_provider="anthropic", anthropic_api_key="sk-ant-test")
        # Should not raise
        config.validate()

    def test_validate_anthropic_missing_api_key(self):
        """Test validate fails for Anthropic without API key."""
        config = AgentConfig(llm_provider="anthropic")

        with pytest.raises(ValueError, match="Anthropic provider requires API key"):
            config.validate()

    def test_validate_azure_foundry_success(self):
        """Test validate succeeds for Azure AI Foundry with required fields."""
        config = AgentConfig(
            llm_provider="foundry",
            azure_project_endpoint="https://test.ai.azure.com",
            azure_model_deployment="gpt-4o",
        )
        # Should not raise
        config.validate()

    def test_validate_azure_foundry_missing_endpoint(self):
        """Test validate fails for Azure AI Foundry without endpoint."""
        config = AgentConfig(
            llm_provider="foundry",
            azure_model_deployment="gpt-4o",
        )

        with pytest.raises(ValueError, match="Azure AI Foundry requires project endpoint"):
            config.validate()

    def test_validate_azure_foundry_missing_deployment(self):
        """Test validate fails for Azure AI Foundry without deployment."""
        config = AgentConfig(
            llm_provider="foundry",
            azure_project_endpoint="https://test.ai.azure.com",
        )

        with pytest.raises(ValueError, match="Azure AI Foundry requires model deployment name"):
            config.validate()

    def test_validate_unknown_provider(self):
        """Test validate fails for unknown provider."""
        config = AgentConfig(llm_provider="invalid_provider")

        with pytest.raises(ValueError, match="Unknown LLM provider: invalid_provider"):
            config.validate()

    def test_get_model_display_name_openai(self):
        """Test get_model_display_name for OpenAI."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            openai_model="gpt-5-mini",
        )

        assert config.get_model_display_name() == "OpenAI/gpt-5-mini"

    def test_get_model_display_name_anthropic(self):
        """Test get_model_display_name for Anthropic."""
        config = AgentConfig(
            llm_provider="anthropic",
            anthropic_api_key="test",
            anthropic_model="claude-haiku-4-5-20251001",
        )

        assert config.get_model_display_name() == "Anthropic/claude-haiku-4-5-20251001"

    def test_get_model_display_name_azure_foundry(self):
        """Test get_model_display_name for Azure AI Foundry."""
        config = AgentConfig(
            llm_provider="foundry",
            azure_project_endpoint="https://test.ai.azure.com",
            azure_model_deployment="gpt-4o",
        )

        assert config.get_model_display_name() == "Azure AI Foundry/gpt-4o"

    def test_get_model_display_name_unknown_provider(self):
        """Test get_model_display_name for unknown provider."""
        config = AgentConfig(llm_provider="unknown")

        assert config.get_model_display_name() == "Unknown"

    def test_anthropic_default_model(self):
        """Test Anthropic defaults to correct model."""
        config = AgentConfig(llm_provider="anthropic", anthropic_api_key="test")

        assert config.anthropic_model == "claude-haiku-4-5-20251001"

    def test_openai_default_model(self):
        """Test OpenAI defaults to correct model."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        assert config.openai_model == "gpt-5-mini"

    def test_validate_azure_openai_success(self):
        """Test validate succeeds for Azure OpenAI with endpoint and deployment."""
        config = AgentConfig(
            llm_provider="azure",
            azure_openai_endpoint="https://test.openai.azure.com/",
            azure_openai_deployment="gpt-5-codex",
        )
        # Should not raise
        config.validate()

    def test_validate_azure_openai_missing_endpoint(self):
        """Test validate fails for Azure OpenAI without endpoint."""
        config = AgentConfig(llm_provider="azure", azure_openai_deployment="gpt-5-codex")

        with pytest.raises(ValueError, match="endpoint"):
            config.validate()

    def test_validate_azure_openai_missing_deployment(self):
        """Test validate fails for Azure OpenAI without deployment."""
        config = AgentConfig(
            llm_provider="azure", azure_openai_endpoint="https://test.openai.azure.com/"
        )

        with pytest.raises(ValueError, match="deployment"):
            config.validate()

    def test_get_model_display_name_azure_openai(self):
        """Test get_model_display_name for Azure OpenAI."""
        config = AgentConfig(llm_provider="azure", azure_openai_deployment="gpt-5-codex")

        assert config.get_model_display_name() == "Azure OpenAI/gpt-5-codex"

    def test_system_prompt_file_from_env(self):
        """Test system_prompt_file is loaded from AGENT_SYSTEM_PROMPT environment variable."""
        with patch.dict(os.environ, {"AGENT_SYSTEM_PROMPT": "/path/to/custom/prompt.md"}):
            config = AgentConfig.from_env()

            assert config.system_prompt_file == "/path/to/custom/prompt.md"

    def test_system_prompt_file_defaults_to_none(self):
        """Test system_prompt_file defaults to None when not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            assert config.system_prompt_file is None

    def test_system_prompt_file_path_expansion(self, tmp_path):
        """Test system prompt file path supports tilde and environment variable expansion."""
        # Create a test prompt file
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("Test prompt content")

        # Test with tilde expansion
        config_tilde = AgentConfig(
            llm_provider="openai",
            openai_api_key="test-key",
            system_prompt_file="~/test_prompt.md",
        )

        # Verify tilde expansion happens in loader (path starts with ~)
        assert config_tilde.system_prompt_file.startswith("~")

        # Test with environment variable (validation in loader, not config)
        with patch.dict(os.environ, {"TEST_PROMPT_DIR": str(tmp_path)}):
            config_env = AgentConfig(
                llm_provider="openai",
                openai_api_key="test-key",
                system_prompt_file="$TEST_PROMPT_DIR/test_prompt.md",
            )

            # Verify env var is preserved in config (expansion happens in loader)
            assert "$TEST_PROMPT_DIR" in config_env.system_prompt_file
