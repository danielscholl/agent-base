"""Integration tests for configuration system end-to-end workflows."""

import os
from unittest.mock import patch

import pytest

from agent.config import AgentConfig, get_default_config, load_config, save_config


@pytest.mark.integration
class TestConfigurationIntegration:
    """Test end-to-end configuration workflows."""

    def test_config_file_to_agent_config(self, tmp_path):
        """Test loading config file and creating AgentConfig."""
        # Create a test config file
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test-123"
        settings.providers.openai.enabled = True

        save_config(settings, config_path)

        # Load into AgentConfig
        agent_config = AgentConfig.from_file(config_path)

        assert agent_config.llm_provider == "openai"
        assert agent_config.openai_api_key == "sk-test-123"
        assert agent_config.config_source == "file"

    def test_file_overrides_env_integration(self, tmp_path):
        """Test that file settings override environment variables (FILE > ENV)."""
        # Create a test config file with OpenAI
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "file-key"
        settings.providers.openai.enabled = True

        save_config(settings, config_path)

        # Set environment variable (should be overridden by file)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-override"}, clear=False):
            agent_config = AgentConfig.from_combined(config_path)

        # File wins over env
        assert agent_config.openai_api_key == "file-key"
        assert agent_config.config_source == "combined"

    def test_multiple_providers_enabled(self, tmp_path):
        """Test enabling multiple providers."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Enable multiple providers
        settings.providers.enabled = ["local", "openai"]
        settings.providers.openai.api_key = "sk-test"
        settings.providers.openai.enabled = True

        save_config(settings, config_path)
        agent_config = AgentConfig.from_file(config_path)

        assert agent_config.enabled_providers == ["local", "openai"]
        assert agent_config.llm_provider == "local"  # First in list

    def test_provider_enable_disable_workflow(self, tmp_path):
        """Test enabling and disabling a provider."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Initially no providers enabled (explicit config required)
        assert settings.providers.enabled == []

        # Enable local provider first
        settings.providers.enabled.append("local")
        settings.providers.local.enabled = True

        # Then enable OpenAI
        settings.providers.enabled.append("openai")
        settings.providers.openai.api_key = "sk-test"
        settings.providers.openai.enabled = True
        save_config(settings, config_path)

        # Verify enabled
        loaded = load_config(config_path)
        assert "openai" in loaded.providers.enabled
        assert loaded.providers.openai.enabled is True

        # Disable OpenAI
        loaded.providers.enabled.remove("openai")
        loaded.providers.openai.enabled = False
        save_config(loaded, config_path)

        # Verify disabled
        final = load_config(config_path)
        assert "openai" not in final.providers.enabled
        assert final.providers.openai.enabled is False

    def test_from_combined_with_no_file(self, tmp_path):
        """Test from_combined() with no file and LLM_PROVIDER env var."""
        # Point to non-existent file
        config_path = tmp_path / "nonexistent.json"

        # Need LLM_PROVIDER env var when no file exists
        with patch.dict(os.environ, {"LLM_PROVIDER": "local"}, clear=False):
            agent_config = AgentConfig.from_combined(config_path)

        # Should use env var
        assert agent_config.llm_provider == "local"

    def test_backward_compatibility_env_only(self):
        """Test that from_env() still works (backward compatibility)."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "anthropic",
                "ANTHROPIC_API_KEY": "sk-ant-test",
            },
            clear=False,
        ):
            agent_config = AgentConfig.from_env()

        assert agent_config.llm_provider == "anthropic"
        assert agent_config.anthropic_api_key == "sk-ant-test"
        assert agent_config.config_source == "env"

    def test_telemetry_config_integration(self, tmp_path):
        """Test telemetry configuration."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()

        # Enable a provider and telemetry
        settings.providers.enabled = ["local"]
        settings.telemetry.enabled = True
        settings.telemetry.otlp_endpoint = "http://custom:4318"
        save_config(settings, config_path)

        agent_config = AgentConfig.from_file(config_path)

        assert agent_config.enable_otel is True
        assert agent_config.otlp_endpoint == "http://custom:4318"

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

        agent_config = AgentConfig.from_file(config_path)

        assert agent_config.memory_type == "mem0"
        assert agent_config.mem0_api_key == "mem0-key"
        assert agent_config.mem0_org_id == "org-123"


@pytest.mark.integration
class TestConfigPrecedence:
    """Test configuration precedence: CLI > file > env > defaults."""

    def test_file_overrides_defaults(self, tmp_path):
        """Test that file settings override defaults."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["anthropic"]
        settings.providers.anthropic.api_key = "file-key"
        settings.providers.anthropic.enabled = True

        save_config(settings, config_path)
        agent_config = AgentConfig.from_file(config_path)

        # File explicitly sets provider
        assert agent_config.llm_provider == "anthropic"

    def test_env_as_fallback(self, tmp_path):
        """Test that environment variables serve as fallback when file doesn't have values."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["openai"]
        # File has openai enabled but no API key set
        settings.providers.openai.api_key = None

        save_config(settings, config_path)

        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "env-fallback-key"},
            clear=False,
        ):
            agent_config = AgentConfig.from_combined(config_path)

        # Env used as fallback when file has null value
        assert agent_config.llm_provider == "openai"
        assert agent_config.openai_api_key == "env-fallback-key"

    def test_file_priority_over_env(self, tmp_path):
        """Test that file values take priority over environment variables."""
        config_path = tmp_path / "settings.json"
        settings = get_default_config()
        settings.providers.enabled = ["local"]  # Enable local provider
        settings.telemetry.enabled = False  # Explicitly disabled in file
        settings.memory.history_limit = 10  # Explicitly set in file

        save_config(settings, config_path)

        env_vars = {
            "ENABLE_OTEL": "true",  # Env says enable
            "MEMORY_HISTORY_LIMIT": "50",  # Env says 50
        }
        with patch.dict(os.environ, env_vars, clear=False):
            agent_config = AgentConfig.from_combined(config_path)

        # File values win over env
        assert agent_config.enable_otel is False  # File wins
        assert agent_config.memory_history_limit == 10  # File wins
