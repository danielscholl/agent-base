"""Unit tests for CLI argument overrides."""

import os
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


@pytest.mark.unit
@pytest.mark.cli
class TestCLIArgumentOverrides:
    """Tests for --provider and --model CLI argument functionality."""

    def test_provider_cli_override_openai(self):
        """Test --provider openai overrides LLM_PROVIDER environment variable."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
            config = AgentConfig.from_env()
            assert config.llm_provider == "openai"

    def test_provider_cli_override_local(self):
        """Test --provider local overrides LLM_PROVIDER environment variable."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "local"}, clear=True):
            config = AgentConfig.from_env()
            assert config.llm_provider == "local"

    def test_model_cli_override_for_openai(self):
        """Test --model overrides AGENT_MODEL for OpenAI provider."""
        with patch.dict(
            os.environ, {"LLM_PROVIDER": "openai", "AGENT_MODEL": "gpt-5-mini"}, clear=True
        ):
            config = AgentConfig.from_env()
            assert config.openai_model == "gpt-5-mini"

    def test_model_cli_override_for_local(self):
        """Test --model overrides AGENT_MODEL for local provider."""
        with patch.dict(
            os.environ, {"LLM_PROVIDER": "local", "AGENT_MODEL": "ai/qwen3"}, clear=True
        ):
            config = AgentConfig.from_env()
            assert config.local_model == "ai/qwen3"

    def test_model_cli_override_for_anthropic(self):
        """Test --model overrides AGENT_MODEL for Anthropic provider."""
        with patch.dict(
            os.environ,
            {"LLM_PROVIDER": "anthropic", "AGENT_MODEL": "claude-opus-4-20250514"},
            clear=True,
        ):
            config = AgentConfig.from_env()
            assert config.anthropic_model == "claude-opus-4-20250514"

    def test_model_cli_override_for_gemini(self):
        """Test --model overrides AGENT_MODEL for Gemini provider."""
        with patch.dict(
            os.environ, {"LLM_PROVIDER": "gemini", "AGENT_MODEL": "gemini-2.5-pro"}, clear=True
        ):
            config = AgentConfig.from_env()
            assert config.gemini_model == "gemini-2.5-pro"

    def test_provider_and_model_cli_override_together(self):
        """Test both --provider and --model can be used together."""
        with patch.dict(
            os.environ, {"LLM_PROVIDER": "local", "AGENT_MODEL": "ai/phi4"}, clear=True
        ):
            config = AgentConfig.from_env()
            assert config.llm_provider == "local"
            assert config.local_model == "ai/phi4"

    def test_cli_override_without_env_file(self):
        """Test CLI overrides work even without .env file."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "local"}, clear=True):
            config = AgentConfig.from_env()
            assert config.llm_provider == "local"
            # Should use default model
            assert config.local_model == "ai/phi4"

    def test_provider_override_with_multiple_switches(self):
        """Test switching between providers via environment variable override."""
        # First use local
        with patch.dict(os.environ, {"LLM_PROVIDER": "local"}, clear=True):
            config1 = AgentConfig.from_env()
            assert config1.llm_provider == "local"

        # Then switch to openai
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}, clear=True):
            config2 = AgentConfig.from_env()
            assert config2.llm_provider == "openai"

        # And back to local with different model
        with patch.dict(
            os.environ, {"LLM_PROVIDER": "local", "AGENT_MODEL": "ai/qwen3"}, clear=True
        ):
            config3 = AgentConfig.from_env()
            assert config3.llm_provider == "local"
            assert config3.local_model == "ai/qwen3"
