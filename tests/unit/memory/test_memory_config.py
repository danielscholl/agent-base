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
