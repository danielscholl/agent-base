"""Unit tests for configuration manager."""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.config.manager import (
    ConfigurationError,
    deep_merge,
    get_config_path,
    load_config,
    merge_with_env,
    save_config,
    validate_config,
)
from agent.config.schema import AgentSettings


class TestGetConfigPath:
    """Test get_config_path function."""

    def test_returns_expected_path(self):
        """Test that get_config_path returns ~/.agent/settings.json."""
        path = get_config_path()
        assert path == Path.home() / ".agent" / "settings.json"


class TestLoadConfig:
    """Test load_config function."""

    def test_load_nonexistent_file_returns_defaults(self, tmp_path):
        """Test loading non-existent file returns default settings."""
        config_path = tmp_path / "nonexistent.json"
        settings = load_config(config_path)

        assert isinstance(settings, AgentSettings)
        assert settings.version == "1.0"
        assert settings.providers.enabled == ["local"]  # Local provider enabled by default

    def test_load_valid_json_succeeds(self, tmp_path):
        """Test loading valid JSON file succeeds."""
        config_path = tmp_path / "settings.json"
        config_data = {
            "version": "1.0",
            "providers": {
                "enabled": ["openai"],
                "openai": {"enabled": True, "api_key": "test-key", "model": "gpt-4o"},
            },
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        settings = load_config(config_path)
        assert settings.providers.enabled == ["openai"]
        assert settings.providers.openai.api_key == "test-key"
        assert settings.providers.openai.model == "gpt-4o"

    def test_load_invalid_json_raises_error(self, tmp_path):
        """Test loading invalid JSON raises ConfigurationError."""
        config_path = tmp_path / "invalid.json"
        with open(config_path, "w") as f:
            f.write("{invalid json")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_path)
        assert "Invalid JSON" in str(exc_info.value)

    def test_load_invalid_schema_raises_error(self, tmp_path):
        """Test loading JSON with invalid schema raises ConfigurationError."""
        config_path = tmp_path / "invalid_schema.json"
        config_data = {
            "version": "1.0",
            "providers": {
                "enabled": ["invalid_provider"],  # Invalid provider name
            },
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(config_path)
        assert "validation failed" in str(exc_info.value).lower()


class TestSaveConfig:
    """Test save_config function."""

    def test_save_creates_directory(self, tmp_path):
        """Test that save_config creates directory if it doesn't exist."""
        config_path = tmp_path / "new_dir" / "settings.json"
        settings = AgentSettings()

        save_config(settings, config_path)

        assert config_path.exists()
        assert config_path.parent.exists()

    def test_save_creates_valid_json(self, tmp_path):
        """Test that save_config creates valid JSON file."""
        config_path = tmp_path / "settings.json"
        settings = AgentSettings(
            providers={"enabled": ["openai"]},
        )

        save_config(settings, config_path)

        # Verify file exists and is valid JSON
        assert config_path.exists()
        with open(config_path) as f:
            data = json.load(f)
        assert data["providers"]["enabled"] == ["openai"]

    def test_save_formats_json_pretty(self, tmp_path):
        """Test that save_config formats JSON with indentation."""
        config_path = tmp_path / "settings.json"
        settings = AgentSettings()

        save_config(settings, config_path)

        with open(config_path) as f:
            content = f.read()

        # Check for indentation
        assert "\n" in content
        assert "  " in content

    def test_save_and_load_roundtrip(self, tmp_path):
        """Test that save and load are reversible."""
        config_path = tmp_path / "settings.json"
        original = AgentSettings(
            providers={"enabled": ["openai", "anthropic"]},
            telemetry={"enabled": True},
        )

        save_config(original, config_path)
        loaded = load_config(config_path)

        assert loaded.providers.enabled == ["openai", "anthropic"]
        assert loaded.telemetry.enabled is True


class TestMergeWithEnv:
    """Test merge_with_env function."""

    def test_no_env_vars_returns_empty_dict(self):
        """Test that no environment variables returns empty overrides."""
        settings = AgentSettings()
        with patch.dict(os.environ, {}, clear=True):
            overrides = merge_with_env(settings)
        assert overrides == {}

    def test_openai_api_key_override(self):
        """Test OpenAI API key environment override."""
        settings = AgentSettings()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-123"}, clear=True):
            overrides = merge_with_env(settings)

        assert overrides["providers"]["openai"]["api_key"] == "env-key-123"

    def test_anthropic_api_key_override(self):
        """Test Anthropic API key environment override."""
        settings = AgentSettings()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            overrides = merge_with_env(settings)

        assert overrides["providers"]["anthropic"]["api_key"] == "sk-ant-test"

    def test_azure_endpoint_and_deployment_override(self):
        """Test Azure endpoint and deployment overrides."""
        settings = AgentSettings()
        env_vars = {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4-deployment",
            "AZURE_OPENAI_API_KEY": "azure-key",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            overrides = merge_with_env(settings)

        assert overrides["providers"]["azure"]["endpoint"] == "https://test.openai.azure.com"
        assert overrides["providers"]["azure"]["deployment"] == "gpt-4-deployment"
        assert overrides["providers"]["azure"]["api_key"] == "azure-key"

    def test_telemetry_overrides(self):
        """Test telemetry environment overrides."""
        settings = AgentSettings()
        env_vars = {
            "ENABLE_OTEL": "true",
            "ENABLE_SENSITIVE_DATA": "true",
            "OTLP_ENDPOINT": "http://custom:4318",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            overrides = merge_with_env(settings)

        assert overrides["telemetry"]["enabled"] is True
        assert overrides["telemetry"]["enable_sensitive_data"] is True
        assert overrides["telemetry"]["otlp_endpoint"] == "http://custom:4318"

    def test_memory_overrides(self):
        """Test memory environment overrides."""
        settings = AgentSettings()
        env_vars = {
            "MEMORY_ENABLED": "false",
            "MEMORY_TYPE": "mem0",
            "MEMORY_HISTORY_LIMIT": "50",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            overrides = merge_with_env(settings)

        assert overrides["memory"]["enabled"] is False
        assert overrides["memory"]["type"] == "mem0"
        assert overrides["memory"]["history_limit"] == 50

    def test_mem0_overrides(self):
        """Test mem0 specific environment overrides."""
        settings = AgentSettings()
        env_vars = {
            "MEM0_API_KEY": "mem0-key",
            "MEM0_ORG_ID": "org-123",
            "MEM0_USER_ID": "user-456",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            overrides = merge_with_env(settings)

        assert overrides["memory"]["mem0"]["api_key"] == "mem0-key"
        assert overrides["memory"]["mem0"]["org_id"] == "org-123"
        assert overrides["memory"]["mem0"]["user_id"] == "user-456"


class TestValidateConfig:
    """Test validate_config function."""

    def test_valid_config_returns_no_errors(self):
        """Test that valid configuration returns empty error list."""
        settings = AgentSettings(
            providers={"enabled": ["local"]},
        )
        errors = validate_config(settings)
        assert len(errors) == 0

    def test_missing_openai_key_returns_error(self):
        """Test that enabled OpenAI without key returns error."""
        settings = AgentSettings(
            providers={"enabled": ["openai"]},
        )
        errors = validate_config(settings)
        assert len(errors) == 1
        assert "OpenAI" in errors[0]
        assert "api_key" in errors[0]

    def test_missing_azure_config_returns_errors(self):
        """Test that enabled Azure without config returns multiple errors."""
        settings = AgentSettings(
            providers={"enabled": ["azure"]},
        )
        errors = validate_config(settings)
        assert len(errors) == 2
        assert any("endpoint" in error for error in errors)
        assert any("deployment" in error for error in errors)

    def test_multiple_providers_with_issues(self):
        """Test validation with multiple providers having issues."""
        settings = AgentSettings(
            providers={"enabled": ["openai", "anthropic"]},
        )
        errors = validate_config(settings)
        assert len(errors) == 2
        assert any("OpenAI" in error for error in errors)
        assert any("Anthropic" in error for error in errors)


class TestDeepMerge:
    """Test deep_merge utility function."""

    def test_merge_flat_dicts(self):
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 20, "z": 30}}
        result = deep_merge(base, override)

        assert result == {"a": {"x": 1, "y": 20, "z": 30}, "b": 3}

    def test_override_takes_precedence(self):
        """Test that override values take precedence."""
        base = {"key": "base_value"}
        override = {"key": "override_value"}
        result = deep_merge(base, override)

        assert result["key"] == "override_value"

    def test_merge_preserves_base_keys(self):
        """Test that merge preserves keys only in base."""
        base = {"a": 1, "b": 2, "c": 3}
        override = {"b": 20}
        result = deep_merge(base, override)

        assert "a" in result
        assert "c" in result
        assert result["a"] == 1
        assert result["c"] == 3
