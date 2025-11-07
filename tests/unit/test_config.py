"""Unit tests for agent.config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


class TestAgentConfig:
    """Tests for AgentConfig class."""

    def test_from_env_defaults_to_openai(self):
        """Test from_env defaults to OpenAI provider when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            assert config.llm_provider == "openai"
            assert config.openai_model == "gpt-5-mini"
            assert config.openai_api_key is None

    def test_from_env_loads_openai_config(self):
        """Test from_env loads OpenAI configuration from environment."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key-123",
                "OPENAI_MODEL": "gpt-4-turbo",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "openai"
            assert config.openai_api_key == "test-key-123"
            assert config.openai_model == "gpt-4-turbo"

    def test_from_env_loads_anthropic_config(self):
        """Test from_env loads Anthropic configuration from environment."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "sk-ant-test-456",
                "ANTHROPIC_MODEL": "claude-opus-4-20250514",
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
                "LLM_PROVIDER": "azure_ai_foundry",
                "AZURE_PROJECT_ENDPOINT": "https://test.ai.azure.com/api/projects/test",
                "AZURE_MODEL_DEPLOYMENT": "gpt-4o",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "azure_ai_foundry"
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
            llm_provider="azure_ai_foundry",
            azure_project_endpoint="https://test.ai.azure.com",
            azure_model_deployment="gpt-4o",
        )
        # Should not raise
        config.validate()

    def test_validate_azure_foundry_missing_endpoint(self):
        """Test validate fails for Azure AI Foundry without endpoint."""
        config = AgentConfig(
            llm_provider="azure_ai_foundry",
            azure_model_deployment="gpt-4o",
        )

        with pytest.raises(ValueError, match="Azure AI Foundry requires project endpoint"):
            config.validate()

    def test_validate_azure_foundry_missing_deployment(self):
        """Test validate fails for Azure AI Foundry without deployment."""
        config = AgentConfig(
            llm_provider="azure_ai_foundry",
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
            anthropic_model="claude-sonnet-4-5-20250929",
        )

        assert config.get_model_display_name() == "Anthropic/claude-sonnet-4-5-20250929"

    def test_get_model_display_name_azure_foundry(self):
        """Test get_model_display_name for Azure AI Foundry."""
        config = AgentConfig(
            llm_provider="azure_ai_foundry",
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

        assert config.anthropic_model == "claude-sonnet-4-5-20250929"

    def test_openai_default_model(self):
        """Test OpenAI defaults to correct model."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        assert config.openai_model == "gpt-5-mini"
