"""Tests for skills configuration in AgentConfig.

This test module verifies that skills configuration is properly transferred
from AgentSettings to AgentConfig in both from_env() and from_combined() methods.

Related bugs:
- Missing skills configuration transfer in legacy.py
- Settings file overriding AGENT_SKILLS env variable
"""

import os
from unittest.mock import patch

import pytest

from agent.config import AgentConfig


@pytest.mark.unit
@pytest.mark.config
class TestSkillsConfiguration:
    """Test skills configuration loading and precedence."""

    def test_from_env_reads_agent_skills_all(self):
        """Test that from_env() reads AGENT_SKILLS=all environment variable."""
        with patch.dict(os.environ, {"AGENT_SKILLS": "all", "LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            assert config.enabled_skills == ["all"]
            assert isinstance(config.enabled_skills, list)

    def test_from_env_reads_agent_skills_comma_separated(self):
        """Test that from_env() reads comma-separated skill names."""
        with patch.dict(
            os.environ, {"AGENT_SKILLS": "skill1,skill2,skill3", "LLM_PROVIDER": "openai"}
        ):
            config = AgentConfig.from_env()

            assert config.enabled_skills == ["skill1", "skill2", "skill3"]

    def test_from_env_reads_agent_skills_none(self):
        """Test that from_env() handles AGENT_SKILLS=none."""
        with patch.dict(os.environ, {"AGENT_SKILLS": "none", "LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            assert config.enabled_skills == []

    def test_from_env_reads_agent_skills_empty_string(self):
        """Test that from_env() handles AGENT_SKILLS='' (empty string)."""
        with patch.dict(os.environ, {"AGENT_SKILLS": "", "LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            assert config.enabled_skills == []

    def test_from_env_transfers_skills_config_to_legacy_class(self):
        """Test that from_env() transfers all skills config to AgentConfig."""
        with patch.dict(
            os.environ,
            {
                "AGENT_SKILLS": "all",
                "LLM_PROVIDER": "openai",
            },
        ):
            config = AgentConfig.from_env()

            # Verify all skills configuration is transferred
            assert hasattr(config, "enabled_skills")
            assert config.enabled_skills == ["all"]

            # Other skills config should exist (may be None/defaults)
            assert hasattr(config, "core_skills_dir")
            assert hasattr(config, "agent_skills_dir")

    def test_from_combined_env_takes_precedence_over_file(self, tmp_path):
        """Test that AGENT_SKILLS env variable overrides settings.json.

        This is the critical bug fix: even if settings.json has enabled_skills: [],
        the AGENT_SKILLS env var should take precedence (like LLM_PROVIDER does).
        """
        # Create a settings.json with enabled_skills: []
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
    "data_dir": "~/.agent",
    "enabled_skills": []
  }
}"""
        )

        # Set AGENT_SKILLS=all in environment
        with patch.dict(os.environ, {"AGENT_SKILLS": "all"}):
            config = AgentConfig.from_combined(config_path=settings_file)

            # ENV should win over file
            assert config.enabled_skills == ["all"], (
                "AGENT_SKILLS env var should override settings.json "
                "(bug: settings.json enabled_skills: [] was overriding env)"
            )

    def test_from_combined_uses_file_when_no_env_var(self, tmp_path):
        """Test that from_combined() uses file settings when no env var set."""
        # Create a settings.json with specific skills
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
    "data_dir": "~/.agent",
    "enabled_skills": ["skill1", "skill2"]
  }
}"""
        )

        # No AGENT_SKILLS env var
        with patch.dict(os.environ, {}, clear=True):
            # Need LLM_PROVIDER or file must have enabled providers
            config = AgentConfig.from_combined(config_path=settings_file)

            # File should be used
            assert config.enabled_skills == ["skill1", "skill2"]

    def test_from_combined_transfers_all_skills_config(self, tmp_path):
        """Test that from_combined() transfers all skills configuration fields."""
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
    "data_dir": "~/.agent",
    "enabled_skills": ["skill1"],
    "core_skills_dir": "/path/to/core",
    "agent_skills_dir": "~/.agent/skills",
    "script_timeout": 120,
    "max_script_output": 2097152
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_combined(config_path=settings_file)

            # Verify all skills config is transferred
            assert config.enabled_skills == ["skill1"]
            # core_skills_dir is now a Path object (type fix)
            assert str(config.core_skills_dir) == "/path/to/core"
            # agent_skills_dir gets expanded (~/ -> /Users/...)
            assert str(config.agent_skills_dir).endswith("/.agent/skills")
            assert config.script_timeout == 120
            assert config.max_script_output == 2097152

    def test_agent_skills_all_untrusted(self):
        """Test that from_env() handles AGENT_SKILLS=all-untrusted."""
        with patch.dict(os.environ, {"AGENT_SKILLS": "all-untrusted", "LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            assert config.enabled_skills == ["all-untrusted"]

    def test_agent_skills_whitespace_handling(self):
        """Test that from_env() strips whitespace from skill names."""
        with patch.dict(
            os.environ, {"AGENT_SKILLS": " skill1 , skill2 , skill3 ", "LLM_PROVIDER": "openai"}
        ):
            config = AgentConfig.from_env()

            assert config.enabled_skills == ["skill1", "skill2", "skill3"]

    def test_core_skills_dir_type_conversion_from_file(self, tmp_path):
        """Test that core_skills_dir is converted from str to Path in from_file()."""
        from pathlib import Path

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
    "data_dir": "~/.agent",
    "core_skills_dir": "/absolute/path/to/core"
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_file(config_path=settings_file)

            # core_skills_dir should be converted to Path
            assert isinstance(config.core_skills_dir, Path)
            assert str(config.core_skills_dir) == "/absolute/path/to/core"

    def test_core_skills_dir_type_conversion_from_combined(self, tmp_path):
        """Test that core_skills_dir is converted from str to Path in from_combined()."""
        from pathlib import Path

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
    "data_dir": "~/.agent",
    "core_skills_dir": "/absolute/path/to/core"
  }
}"""
        )

        with patch.dict(os.environ, {}, clear=True):
            config = AgentConfig.from_combined(config_path=settings_file)

            # core_skills_dir should be converted to Path
            assert isinstance(config.core_skills_dir, Path)
            assert str(config.core_skills_dir) == "/absolute/path/to/core"

    def test_core_skills_dir_none_handling(self, tmp_path):
        """Test that core_skills_dir=None is handled correctly."""
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

            # core_skills_dir should remain None when not set
            assert config.core_skills_dir is None


@pytest.mark.unit
@pytest.mark.config
class TestSkillsConfigIntegration:
    """Integration tests for skills configuration with Agent initialization."""

    def test_agent_initialization_with_skills_enabled(self):
        """Test that Agent initializes skills when enabled_skills is set.

        This is an integration test to verify the full flow:
        1. Config reads AGENT_SKILLS env var
        2. Config transfers to legacy AgentConfig
        3. Agent sees enabled_skills and loads SkillLoader
        """
        from agent import Agent

        with patch.dict(os.environ, {"AGENT_SKILLS": "all", "LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            # Mock chat client to avoid real LLM calls
            from tests.mocks import MockChatClient

            mock_client = MockChatClient(response="test")

            # Agent should not crash with enabled_skills set
            agent = Agent(config=config, chat_client=mock_client)

            # Agent should have initialized
            assert agent is not None
            assert agent.config.enabled_skills == ["all"]

            # If skills directory exists, SkillLoader should have run
            # (We don't assert on toolsets here since skills may not exist in test env)

    def test_agent_initialization_without_skills(self):
        """Test that Agent works normally when skills are disabled."""
        from agent import Agent

        with patch.dict(os.environ, {"AGENT_SKILLS": "none", "LLM_PROVIDER": "openai"}):
            config = AgentConfig.from_env()

            from tests.mocks import MockChatClient

            mock_client = MockChatClient(response="test")

            agent = Agent(config=config, chat_client=mock_client)

            # Agent should work normally
            assert agent is not None
            assert agent.config.enabled_skills == []

            # Should have default toolsets only
            toolset_names = [type(t).__name__ for t in agent.toolsets]
            assert "HelloTools" in toolset_names
            assert "FileSystemTools" in toolset_names
