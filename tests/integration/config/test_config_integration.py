"""Integration tests for configuration system end-to-end workflows."""

import os
from unittest.mock import patch

import pytest

from agent.config import get_default_config, load_config, merge_with_env, save_config
from agent.config.schema import AgentSettings


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test end-to-end configuration workflows."""

    def test_config_file_to_agent_settings(self, tmp_path):
        """Test loading config file and creating AgentSettings."""
        # Create a test config file
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test-123"

        save_config(settings, config_path)

        # Load settings from file
        loaded_settings = load_config(config_path)

        assert loaded_settings.llm_provider == "openai"
        assert loaded_settings.openai_api_key == "sk-test-123"

    def test_file_with_env_overrides_integration(self, tmp_path):
        """Test that environment variables can override file settings when merged."""
        # Create a test config file with OpenAI
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "file-key"

        save_config(settings, config_path)

        # Set environment variable to override
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-override"}, clear=False):
            loaded_settings = load_config(config_path)
            env_overrides = merge_with_env(loaded_settings)

        # Env overrides file when explicitly merged
        # merge_with_env returns dict of overrides
        assert env_overrides["providers"]["openai"]["api_key"] == "env-key-override"

    def test_multiple_providers_enabled(self, tmp_path):
        """Test enabling multiple providers."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Enable multiple providers
        settings.providers.enabled = ["local", "openai"]
        settings.providers.openai.api_key = "sk-test"

        save_config(settings, config_path)
        loaded_settings = load_config(config_path)

        assert loaded_settings.providers.enabled == ["local", "openai"]
        assert loaded_settings.llm_provider == "local"  # First in list

    def test_provider_enable_disable_workflow(self, tmp_path):
        """Test enabling and disabling a provider."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Initially no providers enabled (explicit config required)
        assert settings.providers.enabled == []

        # Enable local provider first
        settings.providers.enabled.append("local")

        # Then enable OpenAI
        settings.providers.enabled.append("openai")
        settings.providers.openai.api_key = "sk-test"
        save_config(settings, config_path)

        # Verify enabled
        loaded = load_config(config_path)
        assert "openai" in loaded.providers.enabled

        # Disable OpenAI
        loaded.providers.enabled.remove("openai")
        save_config(loaded, config_path)

        # Verify disabled
        final = load_config(config_path)
        assert "openai" not in final.providers.enabled

    def test_load_config_with_no_file_uses_defaults(self, tmp_path):
        """Test load_config() with non-existent file returns defaults."""
        # Point to non-existent file
        config_path = tmp_path / "nonexistent.json"

        # Should return default configuration
        settings = load_config(config_path)

        # Should have default providers (empty list)
        assert settings.providers.enabled == []

    def test_env_variables_integration(self):
        """Test that environment variables work with the system."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "sk-ant-test",
            },
            clear=False,
        ):
            settings = AgentSettings()
            settings.providers.enabled = ["anthropic"]
            env_overrides = merge_with_env(settings)

        # merge_with_env returns dict of overrides
        assert env_overrides["providers"]["anthropic"]["api_key"] == "sk-ant-test"

    def test_telemetry_config_integration(self, tmp_path):
        """Test telemetry configuration."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Enable a provider and telemetry
        settings.providers.enabled = ["local"]
        settings.telemetry.enabled = True
        settings.telemetry.otlp_endpoint = "http://custom:4318"
        save_config(settings, config_path)

        loaded_settings = load_config(config_path)

        assert loaded_settings.telemetry.enabled is True
        assert loaded_settings.telemetry.otlp_endpoint == "http://custom:4318"

    def test_memory_config_integration(self, tmp_path):
        """Test memory configuration."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Enable a provider and configure mem0
        settings.providers.enabled = ["local"]
        settings.memory.type = "mem0"
        settings.memory.mem0.api_key = "mem0-key"
        settings.memory.mem0.org_id = "org-123"
        save_config(settings, config_path)

        loaded_settings = load_config(config_path)

        assert loaded_settings.memory.type == "mem0"
        assert loaded_settings.memory.mem0.api_key == "mem0-key"
        assert loaded_settings.memory.mem0.org_id == "org-123"


@pytest.mark.integration
class TestConfigPrecedence:
    """Test configuration precedence: file + env overrides."""

    def test_file_overrides_defaults(self, tmp_path):
        """Test that file settings override defaults."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["anthropic"]
        settings.providers.anthropic.api_key = "file-key"

        save_config(settings, config_path)
        loaded_settings = load_config(config_path)

        # File explicitly sets provider
        assert loaded_settings.llm_provider == "anthropic"

    def test_env_as_override(self, tmp_path):
        """Test that environment variables can override file values when merged."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "file-key"

        save_config(settings, config_path)

        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "env-override-key"},
            clear=False,
        ):
            loaded_settings = load_config(config_path)
            env_overrides = merge_with_env(loaded_settings)

        # Env used to override file value when merged
        assert loaded_settings.openai_api_key == "file-key"  # File value without merge
        # merge_with_env returns dict of overrides
        assert env_overrides["providers"]["openai"]["api_key"] == "env-override-key"  # Env overrides after merge

    def test_file_values_persist(self, tmp_path):
        """Test that file values are preserved in configuration."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["local"]
        settings.telemetry.enabled = False
        settings.memory.history_limit = 10

        save_config(settings, config_path)

        loaded_settings = load_config(config_path)

        # File values are loaded
        assert loaded_settings.telemetry.enabled is False
        assert loaded_settings.memory.history_limit == 10
