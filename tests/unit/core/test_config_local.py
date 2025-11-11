"""Unit tests for local provider configuration in agent.config module."""

import os
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


@pytest.mark.unit
@pytest.mark.config
class TestLocalProviderConfig:
    """Tests for Local Provider configuration in AgentConfig."""

    def test_from_env_with_local_provider(self):
        """Test from_env loads local provider configuration."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "local",
                "LOCAL_BASE_URL": "http://localhost:12434/engines/llama.cpp/v1",
                "AGENT_MODEL": "ai/phi4",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "local"
            assert config.local_base_url == "http://localhost:12434/engines/llama.cpp/v1"
            assert config.local_model == "ai/phi4"

    def test_from_env_local_provider_defaults(self):
        """Test from_env uses default values for local provider."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "local",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.llm_provider == "local"
            assert config.local_base_url == "http://localhost:12434/engines/llama.cpp/v1"
            assert config.local_model == "ai/phi4"

    def test_from_env_local_custom_base_url(self):
        """Test from_env with custom LOCAL_BASE_URL."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "local",
                "LOCAL_BASE_URL": "http://localhost:9000/v1",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.local_base_url == "http://localhost:9000/v1"

    def test_local_provider_validation_success(self):
        """Test validate succeeds for local provider with base_url."""
        config = AgentConfig(
            llm_provider="local",
            local_base_url="http://localhost:12434/engines/llama.cpp/v1",
        )
        # Should not raise
        config.validate()

    def test_local_provider_validation_missing_url(self):
        """Test validate fails for local provider without base_url."""
        config = AgentConfig(
            llm_provider="local",
            local_base_url=None,
        )

        with pytest.raises(ValueError, match="Local provider requires base URL"):
            config.validate()

    def test_local_provider_validation_error_message(self):
        """Test validate error message includes helpful guidance."""
        config = AgentConfig(
            llm_provider="local",
            local_base_url=None,
        )

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        error_msg = str(exc_info.value)
        assert "LOCAL_BASE_URL" in error_msg
        assert "docker model pull phi4" in error_msg

    def test_local_provider_display_name(self):
        """Test get_model_display_name for local provider."""
        config = AgentConfig(
            llm_provider="local",
            local_base_url="http://localhost:12434/engines/llama.cpp/v1",
            local_model="ai/phi4",
        )

        assert config.get_model_display_name() == "Local/ai/phi4"

    def test_local_provider_display_name_custom_model(self):
        """Test get_model_display_name for local provider with custom model."""
        config = AgentConfig(
            llm_provider="local",
            local_base_url="http://localhost:12434/engines/llama.cpp/v1",
            local_model="ai/llama3.2",
        )

        assert config.get_model_display_name() == "Local/ai/llama3.2"

    def test_local_model_override_via_agent_model(self):
        """Test AGENT_MODEL overrides default local model."""
        with patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "local",
                "AGENT_MODEL": "ai/llama3.2",
            },
            clear=True,
        ):
            config = AgentConfig.from_env()

            assert config.local_model == "ai/llama3.2"

    def test_local_default_model(self):
        """Test local provider defaults to ai/phi4 model."""
        config = AgentConfig(
            llm_provider="local",
            local_base_url="http://localhost:12434/engines/llama.cpp/v1",
        )

        assert config.local_model == "ai/phi4"

    def test_local_provider_in_supported_providers(self):
        """Test that validation error message includes local in supported providers."""
        config = AgentConfig(llm_provider="invalid_provider")

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        error_msg = str(exc_info.value)
        assert "local" in error_msg
        assert "Supported providers:" in error_msg
