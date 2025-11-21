"""Tests for skills configuration in AgentSettings.

This test module verifies that skills configuration is properly loaded
from JSON configuration files and accessible via AgentSettings.

Note: The AGENT_SKILLS environment variable feature was removed in the new
skills configuration redesign. Skills are now configured via:
- config.skills.plugins: list of plugin skill sources (git-based)
- config.skills.disabled_bundled: list of bundled skills to disable
"""

import os
from unittest.mock import patch

import pytest

from agent.config import load_config
from agent.config.schema import AgentSettings


@pytest.mark.unit
@pytest.mark.config
class TestSkillsConfiguration:
    """Test skills configuration loading from JSON files."""

    def test_load_config_without_skills_uses_defaults(self, tmp_path):
        """Test that load_config() uses default skills configuration when not specified."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            """{
  "version": "1.0",
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "model": "gpt-4o-mini"
    }
  },
  "agent": {
    "data_dir": "~/.agent"
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            settings = load_config(config_path=settings_file)

            # Should have default skills config
            assert settings.skills is not None
            assert settings.skills.plugins == []
            assert settings.skills.disabled_bundled == []
            assert settings.skills.user_dir.endswith("/.agent/skills")

    def test_load_config_transfers_skills_config(self, tmp_path):
        """Test that load_config() properly loads skills configuration from JSON."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            """{
  "version": "1.0",
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "model": "gpt-4o-mini"
    }
  },
  "agent": {
    "data_dir": "~/.agent"
  },
  "skills": {
    "plugins": [
      {
        "name": "test-skill",
        "git_url": "https://github.com/example/test-skill",
        "enabled": true
      }
    ],
    "disabled_bundled": ["old-skill"],
    "user_dir": "~/.agent/skills"
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            settings = load_config(config_path=settings_file)

            # Verify skills config is loaded
            assert settings.skills is not None
            assert len(settings.skills.plugins) == 1
            assert settings.skills.plugins[0].name == "test-skill"
            assert settings.skills.disabled_bundled == ["old-skill"]
            assert settings.skills.user_dir.endswith("/.agent/skills")

    def test_load_config_with_all_skills_options(self, tmp_path):
        """Test that load_config() loads all skills configuration options."""
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            """{
  "version": "1.0",
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "model": "gpt-4o-mini"
    }
  },
  "skills": {
    "plugins": [
      {
        "name": "my-skill",
        "git_url": "https://github.com/example/my-skill"
      }
    ],
    "disabled_bundled": ["deprecated-skill"],
    "script_timeout": 120,
    "max_script_output": 2097152
  }
}"""
        )

        settings = load_config(config_path=settings_file)

        # Verify all skills config is loaded
        assert settings.skills is not None
        assert len(settings.skills.plugins) == 1
        assert settings.skills.plugins[0].name == "my-skill"
        assert settings.skills.disabled_bundled == ["deprecated-skill"]
        assert settings.skills.script_timeout == 120
        assert settings.skills.max_script_output == 2097152

    def test_agent_settings_skills_property(self):
        """Test that AgentSettings has skills property with defaults."""
        settings = AgentSettings()

        # Should have default skills configuration
        assert settings.skills is not None
        assert settings.skills.plugins == []
        assert settings.skills.disabled_bundled == []
        assert isinstance(settings.skills.user_dir, str)


@pytest.mark.unit
@pytest.mark.config
class TestSkillsConfigIntegration:
    """Integration tests for skills configuration with Agent initialization."""

    def test_agent_initialization_with_default_skills(self):
        """Test that Agent initializes with default skills configuration.

        This is an integration test to verify the full flow:
        1. AgentSettings has default skills configuration
        2. Agent initializes successfully with skills
        """
        from agent import Agent

        settings = AgentSettings()
        settings.providers.enabled = ["openai"]
        settings.providers.openai.api_key = "test-key"
        settings.providers.openai.model = "gpt-4o-mini"

        # Mock chat client to avoid real LLM calls
        from tests.mocks import MockChatClient

        mock_client = MockChatClient(response="test")

        # Agent should not crash with default skills
        agent = Agent(settings=settings, chat_client=mock_client)

        # Agent should have initialized
        assert agent is not None
        assert agent.settings.skills is not None

    def test_agent_initialization_with_plugin_skills(self, tmp_path):
        """Test that Agent works with plugin skills configured."""
        from agent import Agent

        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            """{
  "version": "1.0",
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "model": "gpt-4o-mini",
      "api_key": "test-key"
    }
  },
  "skills": {
    "plugins": [],
    "disabled_bundled": []
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            settings = load_config(config_path=settings_file)

            from tests.mocks import MockChatClient

            mock_client = MockChatClient(response="test")

            agent = Agent(settings=settings, chat_client=mock_client)

            # Agent should work normally
            assert agent is not None
            assert agent.settings.skills is not None
            assert agent.settings.skills.plugins == []

            # Should have default toolsets
            toolset_names = [type(t).__name__ for t in agent.toolsets]
            assert "HelloTools" in toolset_names
            assert "FileSystemTools" in toolset_names
