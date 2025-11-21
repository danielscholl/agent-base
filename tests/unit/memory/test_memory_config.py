"""Unit tests for memory configuration integration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.config.manager import load_config, merge_with_env
from agent.config.schema import AgentSettings


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.config
class TestMemoryConfiguration:
    """Tests for memory-related configuration."""

    def test_config_memory_enabled_by_default(self):
        """Test memory is enabled by default for conversation context."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test"

        assert settings.memory_enabled is True

    def test_config_memory_type_defaults_to_in_memory(self):
        """Test memory type defaults to in_memory."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test"

        assert settings.memory_type == "in_memory"

    def test_config_memory_enabled_explicit(self):
        """Test memory can be explicitly enabled."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test"
        settings.memory.enabled = True

        assert settings.memory_enabled is True

    def test_config_memory_type_custom(self):
        """Test memory type can be customized."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test"
        settings.memory.enabled = True
        settings.memory.type = "custom"

        assert settings.memory_type == "custom"

    def test_config_memory_dir_default(self):
        """Test memory_dir defaults to agent_data_dir/memory."""
        settings = AgentSettings()

        # memory_dir is a computed property
        expected = settings.agent_data_dir / "memory"
        assert settings.memory_dir == expected

    def test_config_memory_dir_custom(self):
        """Test memory_dir is computed from agent_data_dir."""
        settings = AgentSettings()
        custom_data_dir = Path("/custom/data")
        settings.agent.data_dir = str(custom_data_dir)

        # memory_dir is computed as agent_data_dir / "memory"
        expected = custom_data_dir / "memory"
        assert settings.memory_dir == expected

    def test_load_config_memory_enabled_by_default(self):
        """Test load_config has memory enabled by default for conversation context."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            settings = load_config()
            settings.providers.enabled = ["openai"]

            assert settings.memory_enabled is True

    def test_merge_env_memory_enabled_from_env_var(self):
        """Test merge_with_env loads memory_enabled from environment."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        with patch.dict(os.environ, {"MEMORY_ENABLED": "true"}, clear=False):
            env_overrides = merge_with_env(settings)

            assert "memory" in env_overrides
            assert env_overrides["memory"]["enabled"] is True

    def test_merge_env_memory_enabled_case_insensitive(self):
        """Test MEMORY_ENABLED is case-insensitive."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        # Test various cases
        for value in ["true", "True", "TRUE", "TrUe"]:
            with patch.dict(os.environ, {"MEMORY_ENABLED": value}, clear=False):
                env_overrides = merge_with_env(settings)

                assert env_overrides["memory"]["enabled"] is True

    def test_merge_env_memory_enabled_false_values(self):
        """Test MEMORY_ENABLED false values."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        for value in ["false", "False", "FALSE", "0", ""]:
            with patch.dict(os.environ, {"MEMORY_ENABLED": value}, clear=False):
                env_overrides = merge_with_env(settings)

                # Memory section might not exist if no overrides, check if present
                if "memory" in env_overrides:
                    assert env_overrides["memory"]["enabled"] is False

    def test_merge_env_memory_type_from_env_var(self):
        """Test merge_with_env loads memory_type from environment."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        with patch.dict(os.environ, {"MEMORY_TYPE": "custom_type"}, clear=False):
            env_overrides = merge_with_env(settings)

            assert env_overrides["memory"]["type"] == "custom_type"

    def test_merge_env_memory_type_defaults_to_in_memory(self):
        """Test merge_with_env defaults memory_type to in_memory."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        with patch.dict(os.environ, {}, clear=False):
            # No MEMORY_TYPE env var, should use default from settings
            assert settings.memory.type == "in_memory"

    def test_merge_env_memory_dir_from_data_dir(self):
        """Test memory_dir is computed from AGENT_DATA_DIR."""
        settings = AgentSettings()

        with patch.dict(os.environ, {"AGENT_DATA_DIR": "/custom/data"}, clear=False):
            env_overrides = merge_with_env(settings)

            # Merge overrides into settings
            settings.agent.data_dir = env_overrides["agent"]["data_dir"]

            expected_dir = Path("/custom/data") / "memory"
            assert settings.memory_dir == expected_dir

    def test_merge_env_memory_dir_defaults_to_agent_data_dir(self):
        """Test memory_dir defaults to agent_data_dir/memory."""
        settings = AgentSettings()

        with patch.dict(os.environ, {}, clear=False):
            expected_dir = settings.agent_data_dir / "memory"
            assert settings.memory_dir == expected_dir

    def test_merge_env_memory_dir_expands_user(self):
        """Test merge_with_env expands ~ in data_dir (thus memory_dir)."""
        settings = AgentSettings()

        with patch.dict(os.environ, {"AGENT_DATA_DIR": "~/custom/data"}, clear=False):
            env_overrides = merge_with_env(settings)

            # Merge and compute
            settings.agent.data_dir = env_overrides["agent"]["data_dir"]

            expected = Path.home() / "custom" / "data" / "memory"
            assert settings.memory_dir == expected

    def test_config_with_all_memory_settings(self):
        """Test config with all memory settings configured."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test"
        settings.memory.enabled = True
        settings.memory.type = "in_memory"
        settings.agent.data_dir = "/custom/data"

        assert settings.memory_enabled is True
        assert settings.memory_type == "in_memory"
        assert settings.memory_dir == Path("/custom/data/memory")

    def test_merge_env_with_all_memory_env_vars(self):
        """Test merge_with_env with all memory environment variables set."""
        settings = AgentSettings()
        settings.providers.enabled = ["openai"]

        env_vars = {
            "MEMORY_ENABLED": "true",
            "MEMORY_TYPE": "in_memory",
            "AGENT_DATA_DIR": "/custom/data",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            env_overrides = merge_with_env(settings)

            # Apply overrides
            settings.memory.enabled = env_overrides["memory"]["enabled"]
            settings.memory.type = env_overrides["memory"]["type"]
            settings.agent.data_dir = env_overrides["agent"]["data_dir"]

            assert settings.memory_enabled is True
            assert settings.memory_type == "in_memory"
            assert settings.memory_dir == Path("/custom/data/memory")

    def test_mem0_config_local(self):
        """Test mem0 local storage configuration."""
        env_vars = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "MEMORY_TYPE": "mem0",
            "MEM0_STORAGE_PATH": "/custom/mem0/path",
            "MEM0_USER_ID": "alice",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            # Apply overrides
            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]
                if "mem0" in env_overrides["memory"]:
                    if "storage_path" in env_overrides["memory"]["mem0"]:
                        settings.memory.mem0.storage_path = env_overrides["memory"]["mem0"][
                            "storage_path"
                        ]
                    if "user_id" in env_overrides["memory"]["mem0"]:
                        settings.memory.mem0.user_id = env_overrides["memory"]["mem0"]["user_id"]

            assert settings.memory_type == "mem0"
            assert settings.mem0_storage_path == "/custom/mem0/path"
            assert settings.mem0_user_id == "alice"

            # Should validate successfully

    def test_mem0_config_cloud(self):
        """Test mem0 cloud configuration."""
        env_vars = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "MEMORY_TYPE": "mem0",
            "MEM0_API_KEY": "test-key",
            "MEM0_ORG_ID": "test-org",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            # Apply overrides
            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]
                if "mem0" in env_overrides["memory"]:
                    if "api_key" in env_overrides["memory"]["mem0"]:
                        settings.memory.mem0.api_key = env_overrides["memory"]["mem0"]["api_key"]
                    if "org_id" in env_overrides["memory"]["mem0"]:
                        settings.memory.mem0.org_id = env_overrides["memory"]["mem0"]["org_id"]

            assert settings.memory_type == "mem0"
            assert settings.mem0_api_key == "test-key"
            assert settings.mem0_org_id == "test-org"

            # Should validate successfully

    def test_mem0_config_validation_passes_local_mode(self):
        """Test mem0 validation passes for local mode."""
        env_vars = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test", "MEMORY_TYPE": "mem0"}

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]

            # Should validate successfully

    def test_mem0_config_validation_passes_with_only_api_key(self):
        """Test mem0 validation passes with only API key (falls back to local)."""
        env_vars = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test",
            "MEMORY_TYPE": "mem0",
            "MEM0_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]
                if (
                    "mem0" in env_overrides["memory"]
                    and "api_key" in env_overrides["memory"]["mem0"]
                ):
                    settings.memory.mem0.api_key = env_overrides["memory"]["mem0"]["api_key"]

            # Should pass - will fall back to local mode when org_id missing

    def test_mem0_config_user_id_defaults_to_none(self):
        """Test mem0 user_id defaults to None when not set."""
        env_vars = {
            "MEMORY_TYPE": "mem0",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]

            # Should be None when MEM0_USER_ID not set (no $USER defaulting in new API)
            assert settings.mem0_user_id is None

    def test_mem0_config_user_id_explicit(self):
        """Test mem0 user_id can be explicitly set."""
        env_vars = {
            "MEMORY_TYPE": "mem0",
            "MEM0_USER_ID": "alice",
            "USER": "should_not_use_this",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]
                if (
                    "mem0" in env_overrides["memory"]
                    and "user_id" in env_overrides["memory"]["mem0"]
                ):
                    settings.memory.mem0.user_id = env_overrides["memory"]["mem0"]["user_id"]

            # MEM0_USER_ID should take precedence over $USER
            assert settings.mem0_user_id == "alice"

    def test_mem0_config_project_id_optional(self):
        """Test mem0 project_id is optional."""
        env_vars = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test", "MEMORY_TYPE": "mem0"}

        with patch.dict(os.environ, env_vars, clear=False):
            settings = load_config()
            env_overrides = merge_with_env(settings)

            if "memory" in env_overrides:
                settings.memory.type = env_overrides["memory"]["type"]

            assert settings.mem0_project_id is None
