"""Unit tests for minimal config serialization (progressive disclosure)."""

import json
import tempfile
from pathlib import Path

import pytest

from agent.config.manager import load_config, save_config
from agent.config.schema import AgentSettings


@pytest.mark.unit
@pytest.mark.config
class TestMinimalConfigSerialization:
    """Tests for minimal/progressive config serialization."""

    def test_minimal_excludes_disabled_providers(self):
        """Test that minimal format excludes disabled providers."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test-123"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        # Should only have enabled providers
        assert "openai" in data["providers"]
        assert "anthropic" not in data["providers"]
        assert "azure" not in data["providers"]
        assert "foundry" not in data["providers"]
        assert "gemini" not in data["providers"]
        assert "local" not in data["providers"]

    def test_minimal_excludes_null_values(self):
        """Test that minimal format excludes null values."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test-123"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        # Should not have null values
        openai_config = data["providers"]["openai"]
        assert "api_key" in openai_config  # Non-null value
        assert openai_config["api_key"] == "sk-test-123"

        # Model should be present (has default)
        assert "model" in openai_config

    def test_minimal_preserves_enabled_list(self):
        """Test that minimal format preserves the enabled providers list."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai", "anthropic"]
        settings.providers.openai.api_key = "sk-test-1"
        settings.providers.anthropic.api_key = "sk-test-2"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        assert set(data["providers"]["enabled"]) == {"openai", "anthropic"}
        assert "openai" in data["providers"]
        assert "anthropic" in data["providers"]
        assert "local" not in data["providers"]

    def test_minimal_removes_redundant_enabled_flag(self):
        """Test that redundant 'enabled' flag is removed from provider configs."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        # Provider config should not have 'enabled' field (it's in the list already)
        openai_config = data["providers"]["openai"]
        assert "enabled" not in openai_config

    def test_minimal_removes_empty_mem0_config(self):
        """Test that empty mem0 config is removed."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        # mem0 config has all null values by default

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        # mem0 should be removed if all values are None
        if "memory" in data:
            assert "mem0" not in data["memory"]

    def test_minimal_keeps_non_empty_mem0_config(self):
        """Test that non-empty mem0 config is preserved."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.memory.type = "mem0"
        settings.memory.mem0.api_key = "mem0-key-123"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        # mem0 should be present with the api_key
        assert "memory" in data
        assert "mem0" in data["memory"]
        assert data["memory"]["mem0"]["api_key"] == "mem0-key-123"

    def test_save_and_load_minimal_format(self):
        """Test that saving minimal format and loading works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            # Create and save minimal config
            settings = AgentSettings()
            settings.providers.enabled = ["openai"]
            settings.providers.openai.api_key = "sk-test-456"
            settings.providers.openai.model = "gpt-4o"
            save_config(settings, config_path)

            # Load it back
            loaded = load_config(config_path)

            # Verify data integrity
            assert loaded.providers.enabled == ["openai"]
            assert loaded.providers.openai.api_key == "sk-test-456"
            assert loaded.providers.openai.model == "gpt-4o"

    def test_load_legacy_full_format_still_works(self):
        """Test backward compatibility: loading old verbose format still works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"

            # Create old-style verbose config
            legacy_config = {
                "version": "1.0",
                "providers": {
                    "enabled": ["openai"],
                    "local": {
                        "enabled": False,
                        "base_url": "http://localhost:12434",
                        "model": "ai/phi4",
                    },
                    "openai": {"enabled": True, "api_key": "sk-legacy", "model": "gpt-5-mini"},
                    "anthropic": {"enabled": False, "api_key": None, "model": "claude-haiku"},
                    "azure": {
                        "enabled": False,
                        "endpoint": None,
                        "deployment": None,
                        "api_version": "2025",
                        "api_key": None,
                    },
                    "foundry": {
                        "enabled": False,
                        "project_endpoint": None,
                        "model_deployment": None,
                    },
                    "gemini": {
                        "enabled": False,
                        "api_key": None,
                        "model": "gemini-2.0",
                        "use_vertexai": False,
                        "project_id": None,
                        "location": None,
                    },
                },
                "agent": {"data_dir": "~/.agent", "log_level": "info"},
                "telemetry": {
                    "enabled": False,
                    "enable_sensitive_data": False,
                    "otlp_endpoint": "http://localhost:4317",
                    "applicationinsights_connection_string": None,
                },
                "memory": {
                    "enabled": True,
                    "type": "in_memory",
                    "history_limit": 20,
                    "mem0": {
                        "storage_path": None,
                        "api_key": None,
                        "org_id": None,
                        "user_id": None,
                        "project_id": None,
                    },
                },
            }

            # Write legacy format
            with open(config_path, "w") as f:
                json.dump(legacy_config, f, indent=2)

            # Load it - should work fine
            loaded = load_config(config_path)

            # Verify it loaded correctly
            assert loaded.providers.enabled == ["openai"]
            assert loaded.providers.openai.api_key == "sk-legacy"
            assert loaded.providers.openai.model == "gpt-5-mini"

    def test_minimal_format_is_actually_smaller(self):
        """Test that minimal format produces significantly smaller output."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test"

        minimal_json = settings.model_dump_json_minimal()
        verbose_json = settings.model_dump_json_pretty()

        # Minimal should be much smaller (at least 50% reduction)
        assert len(minimal_json) < len(verbose_json) * 0.5

    def test_multiple_enabled_providers_all_included(self):
        """Test that all enabled providers are included."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai", "anthropic", "local"]
        settings.providers.openai.api_key = "sk-1"
        settings.providers.anthropic.api_key = "sk-2"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        assert set(data["providers"]["enabled"]) == {"openai", "anthropic", "local"}
        assert "openai" in data["providers"]
        assert "anthropic" in data["providers"]
        assert "local" in data["providers"]
        assert "azure" not in data["providers"]
        assert "foundry" not in data["providers"]
        assert "gemini" not in data["providers"]

    def test_minimal_format_json_valid(self):
        """Test that minimal format produces valid JSON."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "sk-test"

        json_str = settings.model_dump_json_minimal()

        # Should parse without errors
        data = json.loads(json_str)
        assert isinstance(data, dict)
        assert "version" in data
        assert "providers" in data

    def test_minimal_preserves_non_default_agent_settings(self):
        """Test that non-default agent settings are preserved."""
        settings = AgentSettings()
        settings.providers.enabled = ["local"]
        settings.agent.data_dir = "/custom/path"
        settings.agent.log_level = "debug"

        json_str = settings.model_dump_json_minimal()
        data = json.loads(json_str)

        assert data["agent"]["data_dir"] == "/custom/path"
        assert data["agent"]["log_level"] == "debug"
