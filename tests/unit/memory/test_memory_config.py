"""Unit tests for memory configuration integration."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.config
class TestMemoryConfiguration:
    """Tests for memory-related configuration."""

    def test_config_memory_enabled_by_default(self):
        """Test memory is enabled by default for conversation context."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        assert config.memory_enabled is True

    def test_config_memory_type_defaults_to_in_memory(self):
        """Test memory type defaults to in_memory."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        assert config.memory_type == "in_memory"

    def test_config_memory_enabled_explicit(self):
        """Test memory can be explicitly enabled."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
        )

        assert config.memory_enabled is True

    def test_config_memory_type_custom(self):
        """Test memory type can be customized."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
            memory_type="custom",
        )

        assert config.memory_type == "custom"

    def test_config_memory_dir_default(self):
        """Test memory_dir defaults to None."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        assert config.memory_dir is None

    def test_config_memory_dir_custom(self):
        """Test memory_dir can be set."""
        custom_dir = Path("/custom/memory")
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_dir=custom_dir,
        )

        assert config.memory_dir == custom_dir

    def test_from_env_memory_enabled_by_default(self):
        """Test from_env has memory enabled by default for conversation context."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            assert config.memory_enabled is True

    def test_from_env_memory_enabled_from_env_var(self):
        """Test from_env loads memory_enabled from environment."""
        with patch.dict(os.environ, {"MEMORY_ENABLED": "true"}, clear=True):
            config = AgentConfig.from_env()

            assert config.memory_enabled is True

    def test_from_env_memory_enabled_case_insensitive(self):
        """Test MEMORY_ENABLED is case-insensitive."""
        # Test various cases
        for value in ["true", "True", "TRUE", "TrUe"]:
            with patch.dict(os.environ, {"MEMORY_ENABLED": value}, clear=True):
                config = AgentConfig.from_env()
                assert config.memory_enabled is True

    def test_from_env_memory_enabled_false_values(self):
        """Test MEMORY_ENABLED false values."""
        for value in ["false", "False", "FALSE", "0", ""]:
            with patch.dict(os.environ, {"MEMORY_ENABLED": value}, clear=True):
                config = AgentConfig.from_env()
                assert config.memory_enabled is False

    def test_from_env_memory_type_from_env_var(self):
        """Test from_env loads memory_type from environment."""
        with patch.dict(os.environ, {"MEMORY_TYPE": "custom_type"}, clear=True):
            config = AgentConfig.from_env()

            assert config.memory_type == "custom_type"

    def test_from_env_memory_type_defaults_to_in_memory(self):
        """Test from_env defaults memory_type to in_memory."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            assert config.memory_type == "in_memory"

    def test_from_env_memory_dir_from_env_var(self):
        """Test from_env loads memory_dir from environment."""
        with patch.dict(os.environ, {"MEMORY_DIR": "/custom/memory"}, clear=True):
            config = AgentConfig.from_env()

            assert config.memory_dir == Path("/custom/memory")

    def test_from_env_memory_dir_defaults_to_agent_data_dir(self):
        """Test from_env defaults memory_dir to agent_data_dir/memory."""
        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_env()

            expected_dir = config.agent_data_dir / "memory"
            assert config.memory_dir == expected_dir

    def test_from_env_memory_dir_expands_user(self):
        """Test from_env expands ~ in memory_dir."""
        with patch.dict(os.environ, {"MEMORY_DIR": "~/custom/memory"}, clear=True):
            config = AgentConfig.from_env()

            assert config.memory_dir == Path.home() / "custom" / "memory"

    def test_config_with_all_memory_settings(self):
        """Test config with all memory settings configured."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
            memory_type="in_memory",
            memory_dir=Path("/custom/memory"),
        )

        assert config.memory_enabled is True
        assert config.memory_type == "in_memory"
        assert config.memory_dir == Path("/custom/memory")

    def test_from_env_with_all_memory_env_vars(self):
        """Test from_env with all memory environment variables set."""
        with patch.dict(
            os.environ,
            {
                "MEMORY_ENABLED": "true",
                "MEMORY_TYPE": "in_memory",
                "MEMORY_DIR": "/custom/memory",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.memory_enabled is True
            assert config.memory_type == "in_memory"
            assert config.memory_dir == Path("/custom/memory")

    def test_mem0_config_local(self):
        """Test mem0 local storage configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test",
                "MEMORY_TYPE": "mem0",
                "MEM0_STORAGE_PATH": "/custom/mem0/path",
                "MEM0_USER_ID": "alice",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.memory_type == "mem0"
            assert config.mem0_storage_path == Path("/custom/mem0/path")
            assert config.mem0_user_id == "alice"

            # Should validate successfully
            config.validate()  # Should not raise

    def test_mem0_config_cloud(self):
        """Test mem0 cloud configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test",
                "MEMORY_TYPE": "mem0",
                "MEM0_API_KEY": "test-key",
                "MEM0_ORG_ID": "test-org",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.memory_type == "mem0"
            assert config.mem0_api_key == "test-key"
            assert config.mem0_org_id == "test-org"

            # Should validate successfully
            config.validate()  # Should not raise

    def test_mem0_config_validation_passes_local_mode(self):
        """Test mem0 validation passes for local mode."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test", "MEMORY_TYPE": "mem0"},
            clear=True,
        ):
            config = AgentConfig.from_env()

            # Should validate successfully
            config.validate()  # Should not raise

    def test_mem0_config_validation_passes_with_only_api_key(self):
        """Test mem0 validation passes with only API key (falls back to local)."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test",
                "MEMORY_TYPE": "mem0",
                "MEM0_API_KEY": "test-key",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            # Should pass - will fall back to local mode when org_id missing
            config.validate()  # Should not raise

    def test_mem0_config_user_id_defaults_to_username(self):
        """Test mem0 user_id defaults to $USER environment variable."""
        with patch.dict(
            os.environ,
            {
                "MEMORY_TYPE": "mem0",
                "USER": "testuser",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            # Should default to $USER when MEM0_USER_ID not set
            assert config.mem0_user_id == "testuser"

    def test_mem0_config_user_id_explicit(self):
        """Test mem0 user_id can be explicitly set."""
        with patch.dict(
            os.environ,
            {
                "MEMORY_TYPE": "mem0",
                "MEM0_USER_ID": "alice",
                "USER": "should_not_use_this",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            # MEM0_USER_ID should take precedence over $USER
            assert config.mem0_user_id == "alice"

    def test_mem0_config_project_id_optional(self):
        """Test mem0 project_id is optional."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test", "MEMORY_TYPE": "mem0"},
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.mem0_project_id is None
            config.validate()  # Should not raise even without project_id
