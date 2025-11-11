"""Tests for system prompt loading with three-tier fallback."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agent.agent import Agent


class TestSystemPromptLoading:
    """Test system prompt loading with different sources."""

    def test_load_default_prompt_from_package(self, mock_config):
        """Test that default prompt loads from package prompts/system.md."""
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should contain content from system.md
        assert "<agent>" in prompt
        assert "Helpful AI assistant" in prompt
        # Should NOT contain placeholders (they should be replaced)
        assert "{{MODEL}}" not in prompt
        assert "{{PROVIDER}}" not in prompt

    def test_load_custom_prompt_from_file(self, custom_prompt_config, custom_prompt_file):
        """Test loading custom prompt from file specified in config."""
        agent = Agent(custom_prompt_config)
        prompt = agent._load_system_prompt()

        # Should contain custom content
        assert "Custom Test Prompt" in prompt
        assert "test assistant" in prompt
        # Should replace placeholders
        assert "OpenAI/gpt-5-mini" in prompt  # {{MODEL}} replaced
        assert "openai" in prompt  # {{PROVIDER}} replaced

    def test_placeholder_replacement(self, mock_config, tmp_path):
        """Test that all placeholders are replaced with config values."""
        # Create a prompt with all placeholders
        prompt_content = """
        Model: {{MODEL}}
        Provider: {{PROVIDER}}
        Data: {{DATA_DIR}}
        Session: {{SESSION_DIR}}
        Memory: {{MEMORY_ENABLED}}
        """
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        mock_config.system_prompt_file = str(prompt_file)
        mock_config.agent_data_dir = Path("/test/data")
        mock_config.agent_session_dir = Path("/test/sessions")
        mock_config.memory_enabled = True

        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Verify all placeholders are replaced
        assert "{{MODEL}}" not in prompt
        assert "{{PROVIDER}}" not in prompt
        assert "{{DATA_DIR}}" not in prompt
        assert "{{SESSION_DIR}}" not in prompt
        assert "{{MEMORY_ENABLED}}" not in prompt

        # Verify replacements are correct
        assert "OpenAI/gpt-5-mini" in prompt
        assert "openai" in prompt
        assert "/test/data" in prompt
        assert "/test/sessions" in prompt
        assert "True" in prompt

    def test_missing_placeholders_ignored(self, mock_config, tmp_path):
        """Test that unknown placeholders are left unchanged."""
        prompt_content = "Model: {{MODEL}}, Unknown: {{UNKNOWN_PLACEHOLDER}}"
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        mock_config.system_prompt_file = str(prompt_file)
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Known placeholder should be replaced
        assert "{{MODEL}}" not in prompt
        assert "OpenAI/gpt-5-mini" in prompt

        # Unknown placeholder should remain
        assert "{{UNKNOWN_PLACEHOLDER}}" in prompt

    def test_user_default_system_prompt(self, mock_config, tmp_path):
        """Test loading from ~/.agent/system.md (user default tier)."""
        # Create user default prompt
        user_default = tmp_path / "system.md"
        user_default.write_text("User default system prompt for testing", encoding="utf-8")

        mock_config.agent_data_dir = tmp_path
        mock_config.system_prompt_file = None  # No explicit override

        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should load from user default
        assert "User default system prompt for testing" in prompt

    def test_fallback_on_missing_custom_file(self, mock_config, caplog):
        """Test fallback to default when custom file doesn't exist."""
        mock_config.system_prompt_file = "/nonexistent/prompt.md"

        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should fall back to default prompt
        assert "<agent>" in prompt

        # Should log warning about failed custom file load
        assert "Failed to load system prompt from AGENT_SYSTEM_PROMPT" in caplog.text

    def test_fallback_on_corrupt_prompt_file(self, mock_config, tmp_path, caplog):
        """Test fallback when prompt file is unreadable."""
        prompt_file = tmp_path / "corrupt.md"
        prompt_file.write_bytes(b"\x80\x81\x82")  # Invalid UTF-8

        mock_config.system_prompt_file = str(prompt_file)
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should fall back to default or hardcoded
        assert len(prompt) > 0
        assert "Failed to load system prompt from AGENT_SYSTEM_PROMPT" in caplog.text

    def test_hardcoded_fallback_on_package_failure(self, mock_config, caplog):
        """Test hardcoded fallback when package resource loading fails."""
        agent = Agent(mock_config)

        # Mock importlib.resources to fail
        with patch("agent.agent.resources.files") as mock_files:
            mock_files.side_effect = Exception("Package resource not found")
            prompt = agent._load_system_prompt()

        # Should use hardcoded fallback
        assert "helpful AI assistant" in prompt
        assert "Using hardcoded fallback" in caplog.text

    def test_placeholder_values_from_config(self, mock_config, custom_prompt_file):
        """Test that placeholder values come from config."""
        mock_config.system_prompt_file = str(custom_prompt_file)
        mock_config.llm_provider = "anthropic"
        mock_config.anthropic_model = "claude-opus-4"
        mock_config.anthropic_api_key = "test-key"  # Required for agent initialization

        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should reflect config values
        assert "Anthropic/claude-opus-4" in prompt
        assert "anthropic" in prompt

    def test_empty_prompt_file_uses_fallback(self, mock_config, tmp_path, caplog):
        """Test that empty prompt file triggers fallback."""
        prompt_file = tmp_path / "empty.md"
        prompt_file.write_text("", encoding="utf-8")

        mock_config.system_prompt_file = str(prompt_file)
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should fall back since prompt_content is empty
        assert len(prompt) > 0
        assert "<agent>" in prompt

    def test_prompt_with_partial_placeholders(self, mock_config, tmp_path):
        """Test prompt with some placeholders and some plain text."""
        prompt_content = """You are an assistant using {{MODEL}}.

        No placeholders here.

        Memory status: {{MEMORY_ENABLED}}"""

        prompt_file = tmp_path / "partial.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        mock_config.system_prompt_file = str(prompt_file)
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should replace only the placeholders
        assert "OpenAI/gpt-5-mini" in prompt
        assert "True" in prompt  # memory_enabled defaults to True now
        assert "No placeholders here" in prompt
        assert "{{MODEL}}" not in prompt
        assert "{{MEMORY_ENABLED}}" not in prompt

    def test_yaml_front_matter_stripped(self, mock_config, tmp_path):
        """Test YAML front matter is stripped from prompt."""
        prompt_content = """---
description: Test prompt with front matter
version: 1.0
---

<agent>
You are a test agent.
Model: {{MODEL}}
</agent>"""

        prompt_file = tmp_path / "yaml_prompt.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        mock_config.system_prompt_file = str(prompt_file)
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # YAML front matter should be stripped
        assert "---" not in prompt
        assert "description:" not in prompt
        assert "version:" not in prompt

        # Content should remain
        assert "<agent>" in prompt
        assert "test agent" in prompt

    def test_unresolved_placeholders_logged(self, mock_config, tmp_path, caplog):
        """Test warning is logged for unresolved placeholders."""
        prompt_content = "Model: {{MODEL}}, Unknown: {{UNKNOWN}}, Another: {{MISSING}}"

        prompt_file = tmp_path / "unresolved.md"
        prompt_file.write_text(prompt_content, encoding="utf-8")

        mock_config.system_prompt_file = str(prompt_file)
        agent = Agent(mock_config)
        agent._load_system_prompt()

        # Should log warning about unresolved placeholders
        assert "Unresolved placeholders" in caplog.text
        assert "{{UNKNOWN}}" in caplog.text or "UNKNOWN" in caplog.text
        assert "{{MISSING}}" in caplog.text or "MISSING" in caplog.text

    def test_env_var_expansion_in_path(self, mock_config, tmp_path, monkeypatch):
        """Test environment variable expansion in custom prompt path."""
        # Create a test prompt file
        prompt_file = tmp_path / "custom.md"
        prompt_file.write_text("Test content with {{MODEL}}")

        # Set environment variable
        monkeypatch.setenv("TEST_PROMPT_DIR", str(tmp_path))

        # Use env var in path
        mock_config.system_prompt_file = "$TEST_PROMPT_DIR/custom.md"
        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should successfully load the file (env var expanded)
        assert "Test content" in prompt
        assert "OpenAI/gpt-5-mini" in prompt  # Placeholder replaced

    def test_user_default_load_exception_handling(self, mock_config, tmp_path, caplog, monkeypatch):
        """Test exception handling when loading user default system prompt fails."""
        # Set up agent_data_dir but make file.read_text() raise an error
        mock_config.agent_data_dir = tmp_path
        mock_config.system_prompt_file = None  # Will try user default

        # Create the file so exists() returns True
        user_default = tmp_path / "system.md"
        user_default.write_text("test content")

        # Mock read_text to raise an exception
        original_read_text = type(user_default).read_text

        def mock_read_text(self, *args, **kwargs):
            if "system.md" in str(self):
                raise PermissionError("Cannot read file")
            return original_read_text(self, *args, **kwargs)

        monkeypatch.setattr(type(user_default), "read_text", mock_read_text)

        agent = Agent(mock_config)
        prompt = agent._load_system_prompt()

        # Should eventually fall back (user default fails, then package default, then hardcoded)
        assert prompt is not None
        assert len(prompt) > 0
        assert "Failed to load user default system prompt" in caplog.text


class TestConfigValidation:
    """Test configuration validation for system prompt file."""

    def test_validate_existing_prompt_file(self, mock_config, custom_prompt_file):
        """Test validation passes for existing prompt file."""
        mock_config.system_prompt_file = str(custom_prompt_file)
        # Should not raise
        mock_config.validate()

    def test_validate_missing_prompt_file_raises_error(self, mock_config):
        """Test validation fails for missing prompt file."""
        mock_config.system_prompt_file = "/nonexistent/prompt.md"

        with pytest.raises(ValueError, match="System prompt file not found"):
            mock_config.validate()

    def test_validate_none_prompt_file_passes(self, mock_config):
        """Test validation passes when system_prompt_file is None."""
        mock_config.system_prompt_file = None
        # Should not raise
        mock_config.validate()

    def test_validate_with_env_var_expansion(self, mock_config, tmp_path, monkeypatch):
        """Test validation expands environment variables before checking existence."""
        # Create a test prompt file
        prompt_file = tmp_path / "test_prompt.md"
        prompt_file.write_text("Test content")

        # Set environment variable
        monkeypatch.setenv("TEST_PROMPT_PATH", str(tmp_path))

        # Use env var in path
        mock_config.system_prompt_file = "$TEST_PROMPT_PATH/test_prompt.md"

        # Should not raise - validation should expand the env var
        mock_config.validate()
