"""Unit tests for local provider configuration in agent.config module."""

import os
from unittest.mock import patch

import pytest

from agent.config import merge_with_env
from agent.config.schema import AgentSettings


@pytest.mark.unit
@pytest.mark.config
class TestLocalProviderConfig:
    """Tests for Local Provider configuration in AgentSettings."""

    def test_local_provider_with_env_overrides(self):
        """Test environment variable overrides for local provider."""
        env_vars = {
            "LOCAL_BASE_URL": "http://localhost:12434/engines/llama.cpp/v1",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = AgentSettings()
            settings.providers.enabled = ["local"]

            env_overrides = merge_with_env(settings)

            # Check that local base_url was read from environment
            assert "providers" in env_overrides
            assert "local" in env_overrides["providers"]
            assert (
                env_overrides["providers"]["local"]["base_url"]
                == "http://localhost:12434/engines/llama.cpp/v1"
            )

    def test_local_provider_defaults(self):
        """Test local provider uses default values."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]

        assert settings.llm_provider == "local"
        assert settings.local_base_url == "http://localhost:12434/engines/llama.cpp/v1"
        assert settings.local_model == "ai/phi4"

    def test_local_custom_base_url(self):
        """Test local provider with custom base URL."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = "http://localhost:9000/v1"

        assert settings.local_base_url == "http://localhost:9000/v1"

    def test_local_provider_validation_success(self):
        """Test validate succeeds for local provider with base_url."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = "http://localhost:12434/engines/llama.cpp/v1"

        # Should not raise
        errors = settings.validate_enabled_providers()
        assert errors == []

    def test_local_provider_validation_missing_url(self):
        """Test validate fails for local provider without base_url."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = None

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0
        assert "local" in errors[0].lower() or "base url" in errors[0].lower()

    def test_local_provider_validation_error_message(self):
        """Test validate error message includes helpful guidance."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = None

        errors = settings.validate_enabled_providers()
        assert len(errors) > 0
        # Error should mention local or base_url
        error_msg = errors[0].lower()
        assert "local" in error_msg or "base" in error_msg

    def test_local_provider_display_name(self):
        """Test get_model_display_name for local provider."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = "http://localhost:12434/engines/llama.cpp/v1"
        settings.providers.local.model = "ai/phi4"

        # New format includes provider prefix
        assert settings.get_model_display_name() == "Local/ai/phi4"

    def test_local_provider_display_name_custom_model(self):
        """Test get_model_display_name for local provider with custom model."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = "http://localhost:12434/engines/llama.cpp/v1"
        settings.providers.local.model = "ai/llama3.2"

        # New format includes provider prefix
        assert settings.get_model_display_name() == "Local/ai/llama3.2"

    def test_local_model_override_via_env(self):
        """Test model can be overridden via environment variables."""
        env_vars = {
            "LOCAL_MODEL": "ai/llama3.2",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            settings = AgentSettings()
            settings.providers.enabled = ["local"]

            env_overrides = merge_with_env(settings)

            # Check model override
            assert "providers" in env_overrides
            assert "local" in env_overrides["providers"]
            assert env_overrides["providers"]["local"]["model"] == "ai/llama3.2"

    def test_local_default_model(self):
        """Test local provider defaults to ai/phi4 model."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.providers.local.base_url = "http://localhost:12434/engines/llama.cpp/v1"

        assert settings.local_model == "ai/phi4"

    def test_local_provider_in_enabled_list(self):
        """Test that local can be in enabled providers list."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]

        assert "local" in settings.providers.enabled
        assert settings.llm_provider == "local"
