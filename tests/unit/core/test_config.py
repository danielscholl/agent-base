"""Unit tests for agent.config module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.config import merge_with_env
from agent.config.schema import AgentSettings


@pytest.mark.unit
@pytest.mark.config
class TestAgentConfig:
    """Tests for AgentSettings with environment variable merging."""

    def test_default_settings_empty_providers(self):
        """Test default AgentSettings has empty providers list."""
        settings = AgentSettings()

        # Default has no providers enabled
        assert settings.providers.enabled == []

    def test_env_overrides_openai_api_key(self):
        """Test environment variable overrides for OpenAI API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}, clear=False):
            settings = AgentSettings()
            settings.providers.enabled = ["openai"]

            env_overrides = merge_with_env(settings)

            # merge_with_env returns nested dict structure
            assert "providers" in env_overrides
            assert "openai" in env_overrides["providers"]
            assert env_overrides["providers"]["openai"]["api_key"] == "test-key-123"

    def test_env_overrides_anthropic_api_key(self):
        """Test environment variable overrides for Anthropic API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-456"}, clear=False):
            settings = AgentSettings()
            settings.providers.enabled = ["anthropic"]

            env_overrides = merge_with_env(settings)

            # merge_with_env returns nested dict structure
            assert "providers" in env_overrides
            assert "anthropic" in env_overrides["providers"]
            assert env_overrides["providers"]["anthropic"]["api_key"] == "sk-ant-test-456"

    def test_env_overrides_azure_foundry_config(self):
        """Test environment variable overrides for Azure AI Foundry."""
        env_vars = {
            "AZURE_PROJECT_ENDPOINT": "https://test.ai.azure.com/api/projects/test",
            "AZURE_MODEL_DEPLOYMENT": "gpt-4o",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = AgentSettings()
            settings.providers.enabled = ["foundry"]

            env_overrides = merge_with_env(settings)

            # merge_with_env returns nested dict structure
            assert "providers" in env_overrides
            assert "foundry" in env_overrides["providers"]
            assert (
                env_overrides["providers"]["foundry"]["project_endpoint"]
                == "https://test.ai.azure.com/api/projects/test"
            )
            assert env_overrides["providers"]["foundry"]["model_deployment"] == "gpt-4o"

    def test_default_data_directory(self):
        """Test default agent data directory."""
        settings = AgentSettings()

        expected_dir = Path.home() / ".agent"
        assert settings.agent_data_dir == expected_dir

    def test_validate_openai_success(self):
        """Test validate succeeds for OpenAI with API key."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test-key"
        # Should not raise
        errors = settings.validate_enabled_providers()
        assert errors == []

    def test_validate_openai_missing_api_key(self):
        """Test validate fails for OpenAI without API key."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0
        assert "OpenAI" in errors[0]

    def test_validate_anthropic_success(self):
        """Test validate succeeds for Anthropic with API key."""
        settings = AgentSettings()
        settings.providers.enabled = ["anthropic"]
        settings.providers.anthropic.api_key = "sk-ant-test"
        # Should not raise
        errors = settings.validate_enabled_providers()
        assert errors == []

    def test_validate_anthropic_missing_api_key(self):
        """Test validate fails for Anthropic without API key."""
        settings = AgentSettings()
        settings.providers.enabled = ["anthropic"]

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0
        assert "Anthropic" in errors[0]

    def test_validate_azure_foundry_success(self):
        """Test validate succeeds for Azure AI Foundry with required fields."""
        settings = AgentSettings()
        settings.providers.enabled = ["foundry"]
        settings.providers.foundry.project_endpoint = "https://test.ai.azure.com"
        settings.providers.foundry.model_deployment = "gpt-4o"
        # Should not raise
        errors = settings.validate_enabled_providers()
        assert errors == []

    def test_validate_azure_foundry_missing_endpoint(self):
        """Test validate fails for Azure AI Foundry without endpoint."""
        settings = AgentSettings()
        settings.providers.enabled = ["foundry"]
        settings.providers.foundry.model_deployment = "gpt-4o"

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0

    def test_validate_azure_foundry_missing_deployment(self):
        """Test validate fails for Azure AI Foundry without deployment."""
        settings = AgentSettings()
        settings.providers.enabled = ["foundry"]
        settings.providers.foundry.project_endpoint = "https://test.ai.azure.com"

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0

    def test_get_model_display_name_openai(self):
        """Test get_model_display_name for OpenAI."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test"
        settings.providers.openai.model = "gpt-5-mini"

        assert settings.get_model_display_name() == "OpenAI/gpt-5-mini"

    def test_get_model_display_name_anthropic(self):
        """Test get_model_display_name for Anthropic."""
        settings = AgentSettings()
        settings.providers.enabled = ["anthropic"]
        settings.providers.anthropic.api_key = "test"
        settings.providers.anthropic.model = "claude-haiku-4-5-20251001"

        assert settings.get_model_display_name() == "Anthropic/claude-haiku-4-5-20251001"

    def test_get_model_display_name_azure_foundry(self):
        """Test get_model_display_name for Azure AI Foundry."""
        settings = AgentSettings()
        settings.providers.enabled = ["foundry"]
        settings.providers.foundry.project_endpoint = "https://test.ai.azure.com"
        settings.providers.foundry.model_deployment = "gpt-4o"

        assert settings.get_model_display_name() == "Azure AI Foundry/gpt-4o"

    def test_get_model_display_name_no_providers(self):
        """Test get_model_display_name with no providers enabled."""
        settings = AgentSettings()
        # No providers enabled should raise error
        with pytest.raises(ValueError, match="No providers enabled"):
            settings.get_model_display_name()

    def test_anthropic_default_model(self):
        """Test Anthropic defaults to correct model."""
        settings = AgentSettings()

        assert settings.providers.anthropic.model == "claude-haiku-4-5-20251001"

    def test_openai_default_model(self):
        """Test OpenAI defaults to correct model."""
        settings = AgentSettings()

        assert settings.providers.openai.model == "gpt-5-mini"

    def test_validate_azure_openai_success(self):
        """Test validate succeeds for Azure OpenAI with endpoint and deployment."""
        settings = AgentSettings()
        settings.providers.enabled = ["azure"]
        settings.providers.azure.endpoint = "https://test.openai.azure.com/"
        settings.providers.azure.deployment = "gpt-5-codex"
        # Should not raise
        errors = settings.validate_enabled_providers()
        assert errors == []

    def test_validate_azure_openai_missing_endpoint(self):
        """Test validate fails for Azure OpenAI without endpoint."""
        settings = AgentSettings()
        settings.providers.enabled = ["azure"]
        settings.providers.azure.deployment = "gpt-5-codex"

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0
        assert "endpoint" in errors[0].lower()

    def test_validate_azure_openai_missing_deployment(self):
        """Test validate fails for Azure OpenAI without deployment."""
        settings = AgentSettings()
        settings.providers.enabled = ["azure"]
        settings.providers.azure.endpoint = "https://test.openai.azure.com/"

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0
        assert "deployment" in errors[0].lower()

    def test_get_model_display_name_azure_openai(self):
        """Test get_model_display_name for Azure OpenAI."""
        settings = AgentSettings()
        settings.providers.enabled = ["azure"]
        settings.providers.azure.deployment = "gpt-5-codex"

        assert settings.get_model_display_name() == "Azure OpenAI/gpt-5-codex"

    def test_system_prompt_file_from_env(self):
        """Test system_prompt_file reads from AGENT_SYSTEM_PROMPT environment variable."""
        with patch.dict(os.environ, {"AGENT_SYSTEM_PROMPT": "/path/to/custom/prompt.md"}):
            settings = AgentSettings()
            assert settings.system_prompt_file == "/path/to/custom/prompt.md"

    def test_system_prompt_file_defaults_to_none(self):
        """Test system_prompt_file defaults to None when env var not set."""
        # Clear AGENT_SYSTEM_PROMPT if it exists
        env_vars = {k: v for k, v in os.environ.items() if k != "AGENT_SYSTEM_PROMPT"}
        with patch.dict(os.environ, env_vars, clear=True):
            settings = AgentSettings()
            assert settings.system_prompt_file is None
