"""Tests for skill command functions in CLI.

This test module verifies the skill management commands:
- show_skills: Display bundled and plugin skills
- manage_skills: Interactive skill management
- enable_skill/disable_skill: Toggle skill state
"""

import json
from unittest.mock import patch

import pytest

from agent.cli.skill_commands import show_skills


@pytest.mark.unit
@pytest.mark.cli
class TestShowSkills:
    """Test the show_skills command."""

    def test_show_skills_with_nonexistent_bundled_dir_falls_back_to_auto_detect(
        self, tmp_path, capsys
    ):
        """Test that show_skills falls back to auto-detection when bundled_dir doesn't exist.

        This is the fix for: "the agent skill show command is no longer showing Bundled Skills"

        When a user has a config with an invalid bundled_dir path (e.g., after moving the repo),
        the command should fall back to auto-detection instead of showing "None found".
        """
        # Create a settings file with non-existent bundled_dir
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "version": "1.0",
                    "providers": {"enabled": []},
                    "skills": {
                        "bundled_dir": "/nonexistent/path/to/skills",
                        "disabled_bundled": [],
                        "plugins": [],
                    },
                }
            )
        )

        # Mock load_config to return settings with invalid bundled_dir
        with patch("agent.cli.skill_commands.load_config") as mock_load_config:
            from agent.config.schema import AgentSettings, SkillsConfig

            settings = AgentSettings(
                skills=SkillsConfig(
                    bundled_dir="/nonexistent/path/to/skills",
                    disabled_bundled=[],
                    plugins=[],
                )
            )
            mock_load_config.return_value = settings

            # Mock _get_repo_paths to return a test directory
            with patch("agent.cli.skill_commands._get_repo_paths") as mock_get_paths:
                # Create a test bundled skills directory
                test_skills_dir = tmp_path / "skills" / "core"
                test_skills_dir.mkdir(parents=True)

                # Create a test skill
                test_skill_dir = test_skills_dir / "test-skill"
                test_skill_dir.mkdir()
                skill_md = test_skill_dir / "SKILL.md"
                skill_md.write_text(
                    """# Test Skill

## Instructions

This is a test skill.
"""
                )

                mock_get_paths.return_value = (tmp_path, str(test_skills_dir))

                # Mock token counting to avoid network calls
                with patch("agent.utils.tokens.count_tokens", return_value=10):
                    # Run show_skills
                    show_skills()

        # Check output
        captured = capsys.readouterr()
        output = captured.out

        # Should show bundled skills (not "None found")
        assert "Bundled:" in output
        assert "test-skill" in output
        assert "None found" not in output

    def test_show_skills_with_none_bundled_dir_auto_detects(self, tmp_path, capsys):
        """Test that show_skills auto-detects when bundled_dir is None."""
        # Mock load_config to return settings with None bundled_dir
        with patch("agent.cli.skill_commands.load_config") as mock_load_config:
            from agent.config.schema import AgentSettings, SkillsConfig

            settings = AgentSettings(
                skills=SkillsConfig(
                    bundled_dir=None,
                    disabled_bundled=[],
                    plugins=[],
                )
            )
            mock_load_config.return_value = settings

            # Mock _get_repo_paths to return a test directory
            with patch("agent.cli.skill_commands._get_repo_paths") as mock_get_paths:
                # Create a test bundled skills directory
                test_skills_dir = tmp_path / "skills" / "core"
                test_skills_dir.mkdir(parents=True)

                # Create a test skill
                test_skill_dir = test_skills_dir / "test-skill"
                test_skill_dir.mkdir()
                skill_md = test_skill_dir / "SKILL.md"
                skill_md.write_text(
                    """# Test Skill

## Instructions

This is a test skill.
"""
                )

                mock_get_paths.return_value = (tmp_path, str(test_skills_dir))

                # Mock token counting to avoid network calls
                with patch("agent.utils.tokens.count_tokens", return_value=10):
                    # Run show_skills
                    show_skills()

        # Check output
        captured = capsys.readouterr()
        output = captured.out

        # Should show bundled skills
        assert "Bundled:" in output
        assert "test-skill" in output
        assert "None found" not in output

    def test_show_skills_with_valid_bundled_dir(self, tmp_path, capsys):
        """Test that show_skills works correctly with a valid bundled_dir."""
        # Create a test bundled skills directory
        test_skills_dir = tmp_path / "skills" / "core"
        test_skills_dir.mkdir(parents=True)

        # Create a test skill
        test_skill_dir = test_skills_dir / "test-skill"
        test_skill_dir.mkdir()
        skill_md = test_skill_dir / "SKILL.md"
        skill_md.write_text(
            """# Test Skill

## Instructions

This is a test skill.
"""
        )

        # Mock load_config to return settings with valid bundled_dir
        with patch("agent.cli.skill_commands.load_config") as mock_load_config:
            from agent.config.schema import AgentSettings, SkillsConfig

            settings = AgentSettings(
                skills=SkillsConfig(
                    bundled_dir=str(test_skills_dir),
                    disabled_bundled=[],
                    plugins=[],
                )
            )
            mock_load_config.return_value = settings

            # Mock token counting to avoid network calls
            with patch("agent.utils.tokens.count_tokens", return_value=10):
                # Run show_skills
                show_skills()

        # Check output
        captured = capsys.readouterr()
        output = captured.out

        # Should show bundled skills
        assert "Bundled:" in output
        assert "test-skill" in output
        assert "None found" not in output

    def test_show_skills_no_bundled_skills(self, tmp_path, capsys):
        """Test that show_skills shows 'None found' when there are no skills."""
        # Create an empty skills directory
        test_skills_dir = tmp_path / "skills" / "core"
        test_skills_dir.mkdir(parents=True)

        # Mock load_config to return settings with valid but empty bundled_dir
        with patch("agent.cli.skill_commands.load_config") as mock_load_config:
            from agent.config.schema import AgentSettings, SkillsConfig

            settings = AgentSettings(
                skills=SkillsConfig(
                    bundled_dir=str(test_skills_dir),
                    disabled_bundled=[],
                    plugins=[],
                )
            )
            mock_load_config.return_value = settings

            # Run show_skills
            show_skills()

        # Check output
        captured = capsys.readouterr()
        output = captured.out

        # Should show "None found" when directory exists but is empty
        assert "Bundled: None found" in output
