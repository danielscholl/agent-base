"""Tests for skills configuration in AgentConfig.

This test module verifies that skills configuration is properly transferred
from AgentSettings to AgentConfig in both from_env() and from_combined() methods.

Note: The AGENT_SKILLS environment variable feature was removed in the new
skills configuration redesign. Skills are now configured via:
- config.skills.plugins: list of plugin skill sources (git-based)
- config.skills.disabled_bundled: list of bundled skills to disable
"""

import os
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


@pytest.mark.unit
@pytest.mark.config
class TestSkillsConfiguration:
    """Test skills configuration loading and transfer to AgentConfig."""

    def test_from_env_sets_skills_to_none(self):
        """Test that from_env() sets skills to None (no env var config for skills)."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            # Skills should be None when loaded from env only
            assert config.skills is None

    def test_from_combined_transfers_skills_config(self, tmp_path):
        """Test that from_combined() transfers skills configuration from settings."""
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
            config = AgentConfig.from_combined(config_path=settings_file)

            # Verify skills config is transferred
            assert config.skills is not None
            assert len(config.skills.plugins) == 1
            assert config.skills.plugins[0].name == "test-skill"
            assert config.skills.disabled_bundled == ["old-skill"]
            assert config.skills.user_dir.endswith("/.agent/skills")

    def test_from_combined_uses_default_skills_config(self, tmp_path):
        """Test that from_combined() uses default SkillsConfig when not in settings."""
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
            config = AgentConfig.from_combined(config_path=settings_file)

            # Should have default skills config
            assert config.skills is not None
            assert config.skills.plugins == []
            assert config.skills.disabled_bundled == []
            assert config.skills.user_dir.endswith("/.agent/skills")

    def test_from_file_transfers_skills_config(self, tmp_path):
        """Test that from_file() transfers skills configuration."""
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

        config = AgentConfig.from_file(config_path=settings_file)

        # Verify all skills config is transferred
        assert config.skills is not None
        assert len(config.skills.plugins) == 1
        assert config.skills.plugins[0].name == "my-skill"
        assert config.skills.disabled_bundled == ["deprecated-skill"]
        assert config.skills.script_timeout == 120
        assert config.skills.max_script_output == 2097152


@pytest.mark.unit
@pytest.mark.config
class TestSkillsConfigIntegration:
    """Integration tests for skills configuration with Agent initialization."""

    def test_agent_initialization_with_skills_config(self):
        """Test that Agent initializes with skills configuration.

        This is an integration test to verify the full flow:
        1. Config transfers skills from settings
        2. Agent sees config.skills and loads SkillLoader
        """
        from agent import Agent

        with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            # Mock chat client to avoid real LLM calls
            from tests.mocks import MockChatClient

            mock_client = MockChatClient(response="test")

            # Agent should not crash with skills=None
            agent = Agent(config=config, chat_client=mock_client)

            # Agent should have initialized
            assert agent is not None
            assert agent.config.skills is None

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
      "model": "gpt-4o-mini"
    }
  },
  "skills": {
    "plugins": [],
    "disabled_bundled": []
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_combined(config_path=settings_file)

            from tests.mocks import MockChatClient

            mock_client = MockChatClient(response="test")

            agent = Agent(config=config, chat_client=mock_client)

            # Agent should work normally
            assert agent is not None
            assert agent.config.skills is not None
            assert agent.config.skills.plugins == []

            # Should have default toolsets
            toolset_names = [type(t).__name__ for t in agent.toolsets]
            assert "HelloTools" in toolset_names
            assert "FileSystemTools" in toolset_names
