"""Unit tests for mem0 utility functions."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.config import AgentConfig
from agent.memory.mem0_utils import create_memory_instance, extract_llm_config, get_storage_path


@pytest.mark.unit
@pytest.mark.memory
class TestMem0Utils:
    """Tests for mem0 utility functions."""

    def test_extract_llm_config_openai(self):
        """Test LLM config extraction for OpenAI provider."""
        config = AgentConfig(
            llm_provider="openai",
            openai_model="gpt-4o",
            openai_api_key="sk-test123",
        )

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "openai"
        assert llm_config["config"]["model"] == "gpt-4o"
        assert llm_config["config"]["api_key"] == "sk-test123"

    def test_extract_llm_config_openai_default_model(self):
        """Test OpenAI config uses config's openai_model field."""
        config = AgentConfig(llm_provider="openai", openai_api_key="sk-test")

        llm_config = extract_llm_config(config)

        # Should use the default from AgentConfig.openai_model
        assert llm_config["config"]["model"] == config.openai_model

    def test_extract_llm_config_anthropic(self):
        """Test LLM config extraction for Anthropic provider."""
        config = AgentConfig(
            llm_provider="anthropic",
            anthropic_model="claude-3-opus-20240229",
            anthropic_api_key="sk-ant-test",
        )

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "anthropic"
        assert llm_config["config"]["model"] == "claude-3-opus-20240229"
        assert llm_config["config"]["api_key"] == "sk-ant-test"

    def test_extract_llm_config_azure(self):
        """Test LLM config extraction for Azure OpenAI provider."""
        config = AgentConfig(
            llm_provider="azure",
            azure_model_deployment="gpt-4o",
            azure_openai_api_key="test-key",
            azure_openai_endpoint="https://test.openai.azure.com/",
            azure_openai_api_version="2024-10-21",
        )

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "azure_openai"
        assert llm_config["config"]["model"] == "gpt-4o"
        assert llm_config["config"]["api_key"] == "test-key"
        assert llm_config["config"]["azure_endpoint"] == "https://test.openai.azure.com/"
        assert llm_config["config"]["api_version"] == "2024-10-21"

    def test_extract_llm_config_gemini(self):
        """Test LLM config extraction for Gemini provider."""
        config = AgentConfig(
            llm_provider="gemini",
            gemini_model="gemini-pro",
            gemini_api_key="test-gemini-key",
        )

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "gemini"
        assert llm_config["config"]["model"] == "gemini-pro"
        assert llm_config["config"]["api_key"] == "test-gemini-key"

    def test_extract_llm_config_unknown_provider_raises_error(self):
        """Test unknown provider raises ValueError with strict validation."""
        config = AgentConfig(llm_provider="unknown", openai_api_key="sk-test")

        with pytest.raises(ValueError, match="mem0 does not support 'unknown' provider"):
            extract_llm_config(config)

    def test_get_storage_path_custom(self):
        """Test get_storage_path uses custom path if provided."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            mem0_storage_path=Path("/custom/path"),
        )

        path = get_storage_path(config)

        assert path == Path("/custom/path")

    def test_get_storage_path_memory_dir(self):
        """Test get_storage_path uses memory_dir/chroma_db if no custom path."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_dir=Path("/tmp/memory"),
        )

        path = get_storage_path(config)

        assert path == Path("/tmp/memory/chroma_db")

    def test_get_storage_path_default(self):
        """Test get_storage_path falls back to agent_data_dir."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            agent_data_dir=Path("/tmp/agent"),
        )

        path = get_storage_path(config)

        assert path == Path("/tmp/agent/mem0_data/chroma_db")

    def test_create_memory_instance_local_mode(self):
        """Test create_memory_instance creates local Chroma instance."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="sk-test",
            memory_dir=Path("/tmp/memory"),
        )

        with patch("mem0.Memory") as mock_memory_class:
            mock_instance = Mock()
            mock_memory_class.from_config.return_value = mock_instance

            memory = create_memory_instance(config)

            assert memory == mock_instance
            # Verify it was configured for local Chroma storage
            call_args = mock_memory_class.from_config.call_args[0][0]
            assert call_args["vector_store"]["provider"] == "chroma"
            assert "/tmp/memory/chroma_db" in call_args["vector_store"]["config"]["path"]

    def test_create_memory_instance_cloud_mode(self):
        """Test create_memory_instance creates cloud instance when API keys provided."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="sk-test",
            mem0_api_key="mem0-key",
            mem0_org_id="org-123",
        )

        with patch("mem0.Memory") as mock_memory_class:
            mock_instance = Mock()
            mock_memory_class.from_config.return_value = mock_instance

            memory = create_memory_instance(config)

            assert memory == mock_instance
            # Verify it was configured for cloud mode
            call_args = mock_memory_class.from_config.call_args[0][0]
            assert call_args["vector_store"]["provider"] == "mem0"
            assert call_args["vector_store"]["config"]["api_key"] == "mem0-key"
            assert call_args["vector_store"]["config"]["org_id"] == "org-123"

    def test_create_memory_instance_missing_import_raises(self):
        """Test create_memory_instance raises clear error when mem0 not installed."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test")

        with patch("builtins.__import__", side_effect=ImportError("No module named 'mem0'")):
            with pytest.raises(ImportError, match="mem0ai package not installed"):
                create_memory_instance(config)

    def test_create_memory_instance_reuses_agent_llm_config(self):
        """Test that mem0 uses the same LLM config as the agent."""
        config = AgentConfig(
            llm_provider="anthropic",
            anthropic_model="claude-3-5-sonnet-20241022",
            anthropic_api_key="sk-ant-test",
            agent_data_dir=Path("/tmp/agent"),
        )

        with patch("mem0.Memory") as mock_memory_class:
            mock_instance = Mock()
            mock_memory_class.from_config.return_value = mock_instance

            create_memory_instance(config)

            # Verify LLM config matches agent config
            call_args = mock_memory_class.from_config.call_args[0][0]
            assert call_args["llm"]["provider"] == "anthropic"
            assert call_args["llm"]["config"]["model"] == "claude-3-5-sonnet-20241022"
            assert call_args["llm"]["config"]["api_key"] == "sk-ant-test"
