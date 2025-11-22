"""Unit tests for mem0 utility functions."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agent.config.schema import AgentSettings
from agent.memory.mem0_utils import create_memory_instance, extract_llm_config, get_storage_path


def _create_openai_config(model="gpt-5-mini", api_key="sk-test"):
    """Helper to create OpenAI config."""
    config = AgentSettings()
    config.providers.enabled = ["openai"]
    config.providers.openai.model = model
    config.providers.openai.api_key = api_key
    return config


def _create_anthropic_config(model="claude-haiku-4-5-20251001", api_key="sk-ant-test"):
    """Helper to create Anthropic config."""
    config = AgentSettings()
    config.providers.enabled = ["anthropic"]
    config.providers.anthropic.model = model
    config.providers.anthropic.api_key = api_key
    return config


def _create_azure_config():
    """Helper to create Azure config."""
    config = AgentSettings()
    config.providers.enabled = ["azure"]
    config.providers.azure.deployment = "gpt-4o"
    config.providers.azure.api_key = "test-key"
    config.providers.azure.endpoint = "https://test.openai.azure.com/"
    config.providers.azure.api_version = "2024-10-21"
    return config


def _create_gemini_config():
    """Helper to create Gemini config."""
    config = AgentSettings()
    config.providers.enabled = ["gemini"]
    config.providers.gemini.model = "gemini-pro"
    config.providers.gemini.api_key = "test-gemini-key"
    return config


@pytest.mark.unit
@pytest.mark.memory
class TestMem0Utils:
    """Tests for mem0 utility functions."""

    def test_extract_llm_config_openai(self):
        """Test LLM config extraction for OpenAI provider."""
        config = _create_openai_config(model="gpt-4o", api_key="sk-test123")

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "openai"
        assert llm_config["config"]["model"] == "gpt-4o"
        assert llm_config["config"]["api_key"] == "sk-test123"

    def test_extract_llm_config_openai_default_model(self):
        """Test OpenAI config uses config's openai_model field."""
        config = _create_openai_config(model="gpt-5-mini", api_key="sk-test")

        llm_config = extract_llm_config(config)

        # Should use the default from config
        assert llm_config["config"]["model"] == config.openai_model

    def test_extract_llm_config_anthropic(self):
        """Test LLM config extraction for Anthropic provider."""
        config = _create_anthropic_config(model="claude-3-opus-20240229", api_key="sk-ant-test")

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "anthropic"
        assert llm_config["config"]["model"] == "claude-3-opus-20240229"
        assert llm_config["config"]["api_key"] == "sk-ant-test"

    def test_extract_llm_config_azure(self, monkeypatch):
        """Test LLM config extraction for Azure OpenAI provider.

        Azure OpenAI is not fully supported by mem0 - it requires OPENAI_API_KEY
        to be set, otherwise it raises an error recommending to use in_memory.
        """
        config = _create_azure_config()

        # Test with OPENAI_API_KEY set - should use OpenAI provider
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "openai"
        assert llm_config["config"]["model"] == "gpt-4o-mini"
        assert llm_config["config"]["api_key"] == "sk-test-openai"
        assert llm_config["config"]["openai_base_url"] == "https://api.openai.com/v1"

        # Test without OPENAI_API_KEY - should raise ValueError
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="mem0 does not fully support Azure OpenAI"):
            extract_llm_config(config)

    def test_extract_llm_config_gemini(self):
        """Test LLM config extraction for Gemini provider."""
        config = _create_gemini_config()

        llm_config = extract_llm_config(config)

        assert llm_config["provider"] == "gemini"
        assert llm_config["config"]["model"] == "gemini-pro"
        assert llm_config["config"]["api_key"] == "test-gemini-key"

    def test_extract_llm_config_unknown_provider_raises_error(self):
        """Test unknown provider raises ValueError with strict validation."""
        config = AgentSettings()
        config.providers.enabled = ["unknown"]
        config.providers.openai.api_key = "sk-test"

        with pytest.raises(ValueError, match="mem0 does not support 'unknown' provider"):
            extract_llm_config(config)

    def test_get_storage_path_custom(self):
        """Test get_storage_path uses custom path if provided."""
        config = _create_openai_config()
        config.memory.mem0.storage_path = Path("/custom/path")

        path = get_storage_path(config)

        assert path == Path("/custom/path")

    def test_get_storage_path_memory_dir(self):
        """Test get_storage_path uses memory_dir/chroma_db if no custom path."""
        config = _create_openai_config()
        config.agent.data_dir = "/tmp/data"
        # memory_dir is computed as agent_data_dir / "memory"

        path = get_storage_path(config)

        # Should use memory_dir (computed) + chroma_db
        assert path == Path("/tmp/data/memory/chroma_db")

    def test_get_storage_path_default(self):
        """Test get_storage_path falls back to agent_data_dir."""
        config = _create_openai_config()
        config.agent.data_dir = "/tmp/agent"

        path = get_storage_path(config)

        # Uses memory_dir (computed as agent_data_dir/memory) + chroma_db
        assert path == Path("/tmp/agent/memory/chroma_db")

    def test_create_memory_instance_local_mode(self):
        """Test create_memory_instance creates local Chroma instance."""
        config = _create_openai_config()
        config.agent.data_dir = "/tmp/data"

        with patch("mem0.Memory") as mock_memory_class:
            mock_instance = Mock()
            mock_memory_class.from_config.return_value = mock_instance

            memory = create_memory_instance(config)

            assert memory == mock_instance
            # Verify it was configured for local Chroma storage
            call_args = mock_memory_class.from_config.call_args[0][0]
            assert call_args["vector_store"]["provider"] == "chroma"
            # memory_dir is computed as agent_data_dir / "memory"
            expected_path = os.path.join("/tmp/data/memory", "chroma_db")
            assert call_args["vector_store"]["config"]["path"] == expected_path

    def test_create_memory_instance_cloud_mode(self):
        """Test create_memory_instance creates cloud instance when API keys provided."""
        config = _create_openai_config()
        config.memory.mem0.api_key = "mem0-key"
        config.memory.mem0.org_id = "org-123"

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
        config = _create_openai_config()

        with patch("builtins.__import__", side_effect=ImportError("No module named 'mem0'")):
            with pytest.raises(ImportError, match="mem0ai package not installed"):
                create_memory_instance(config)

    def test_create_memory_instance_reuses_agent_llm_config(self):
        """Test that mem0 uses the same LLM config as the agent."""
        config = _create_anthropic_config(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test")
        config.agent.data_dir = "/tmp/agent"

        with patch("mem0.Memory") as mock_memory_class:
            mock_instance = Mock()
            mock_memory_class.from_config.return_value = mock_instance

            create_memory_instance(config)

            # Verify LLM config matches agent config
            call_args = mock_memory_class.from_config.call_args[0][0]
            assert call_args["llm"]["provider"] == "anthropic"
            assert call_args["llm"]["config"]["model"] == "claude-3-5-sonnet-20241022"
            assert call_args["llm"]["config"]["api_key"] == "sk-ant-test"
