"""Unit tests for skill loader."""

from unittest.mock import Mock

import pytest

from agent.skills.errors import SkillManifestError
from agent.skills.loader import SkillLoader
from agent.skills.manifest import SkillManifest


@pytest.fixture
def mock_config():
    """Create mock AgentConfig with proper skills structure."""
    config = Mock()
    # Mock skills config with proper structure
    config.skills = Mock()
    config.skills.disabled_bundled = []  # Must be list, not Mock (loader iterates over it)
    config.skills.bundled_dir = None
    config.skills.plugins = []  # Must be list, not Mock
    config.skills.user_dir = None
    return config


class TestSkillLoader:
    """Test SkillLoader class."""

    def test_init(self, mock_config):
        """Should initialize with config."""
        loader = SkillLoader(mock_config)
        assert loader.config == mock_config
        assert loader._loaded_scripts == {}

    def test_scan_skill_directory_nonexistent(self, mock_config, tmp_path):
        """Should return empty list for nonexistent directory."""
        loader = SkillLoader(mock_config)
        nonexistent = tmp_path / "nonexistent"
        result = loader.scan_skill_directory(nonexistent)
        assert result == []

    def test_scan_skill_directory_with_skills(self, mock_config, tmp_path):
        """Should find skills with SKILL.md."""
        loader = SkillLoader(mock_config)

        # Create skill directories
        skill1 = tmp_path / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: skill1\ndescription: test\n---\n")

        skill2 = tmp_path / "skill2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("---\nname: skill2\ndescription: test\n---\n")

        # Create directory without SKILL.md (should be ignored)
        no_manifest = tmp_path / "no_manifest"
        no_manifest.mkdir()

        result = loader.scan_skill_directory(tmp_path)
        assert len(result) == 2
        assert skill1 in result
        assert skill2 in result

    def test_discover_scripts_auto_discover(self, mock_config, tmp_path):
        """Should auto-discover scripts from scripts/ directory."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create script files
        (scripts_dir / "status.py").write_text("# status script")
        (scripts_dir / "markets.py").write_text("# markets script")

        manifest = SkillManifest(name="test-skill", description="test", scripts=None)

        scripts = loader.discover_scripts(skill_path, manifest)

        assert len(scripts) == 2
        script_names = [s["name"] for s in scripts]
        assert "status" in script_names
        assert "markets" in script_names

    def test_discover_scripts_explicit_list(self, mock_config, tmp_path):
        """Should use explicit script list from manifest."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create scripts
        (scripts_dir / "status.py").write_text("# status")
        (scripts_dir / "markets.py").write_text("# markets")
        (scripts_dir / "extra.py").write_text("# extra")

        # Manifest only specifies status and markets
        manifest = SkillManifest(
            name="test-skill", description="test", scripts=["status", "markets"]
        )

        scripts = loader.discover_scripts(skill_path, manifest)

        assert len(scripts) == 2
        script_names = [s["name"] for s in scripts]
        assert "status" in script_names
        assert "markets" in script_names
        assert "extra" not in script_names

    def test_discover_scripts_with_ignore_patterns(self, mock_config, tmp_path):
        """Should exclude scripts matching ignore patterns."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create scripts
        (scripts_dir / "status.py").write_text("# status")
        (scripts_dir / "status_test.py").write_text("# test")
        (scripts_dir / "_private.py").write_text("# private")

        manifest = SkillManifest(
            name="test-skill",
            description="test",
            scripts=None,
            scripts_ignore=["*_test.py", "_*.py"],
        )

        scripts = loader.discover_scripts(skill_path, manifest)

        assert len(scripts) == 1
        assert scripts[0]["name"] == "status"

    def test_discover_scripts_no_scripts_dir(self, mock_config, tmp_path):
        """Should return empty list if scripts/ doesn't exist."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()

        manifest = SkillManifest(name="test-skill", description="test")

        scripts = loader.discover_scripts(skill_path, manifest)
        assert scripts == []

    def test_load_skill_minimal(self, mock_config, tmp_path):
        """Should load skill with minimal manifest."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

# Test Skill
"""
        )

        manifest, toolsets, scripts = loader.load_skill(skill_path)

        assert manifest.name == "test-skill"
        assert toolsets == []
        assert scripts == []

    def test_load_skill_with_scripts(self, mock_config, tmp_path):
        """Should load skill with scripts."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()

        (skill_path / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

# Test Skill
"""
        )

        (scripts_dir / "status.py").write_text("# status script")

        manifest, toolsets, scripts = loader.load_skill(skill_path)

        assert manifest.name == "test-skill"
        assert len(scripts) == 1
        assert scripts[0]["name"] == "status"

    def test_load_skill_invalid_manifest(self, mock_config, tmp_path):
        """Should raise SkillManifestError for invalid manifest."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text("Invalid YAML")

        with pytest.raises(SkillManifestError):
            loader.load_skill(skill_path)

    def test_load_enabled_skills_none(self, mock_config):
        """Should return empty lists if no skills enabled."""
        # Ensure mock has proper skills config
        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = None
        mock_config.skills.plugins = []

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        assert toolsets == []
        assert script_wrapper is None
        assert not skill_docs.has_skills()

    def test_load_enabled_skills_none_marker(self, mock_config):
        """Should return empty lists when no bundled or plugin skills configured."""
        # Note: The 'none' marker concept is removed - skills are disabled by having empty config
        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = None
        mock_config.skills.plugins = []

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        assert toolsets == []
        assert script_wrapper is None
        assert not skill_docs.has_skills()


class TestScriptNameNormalization:
    """Test script name normalization in loader."""

    def test_accepts_both_formats(self, mock_config, tmp_path):
        """Should accept both 'status' and 'status.py' in manifest."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        (scripts_dir / "status.py").write_text("# status")

        # Manifest lists without .py extension
        manifest = SkillManifest(name="test-skill", description="test", scripts=["status"])

        scripts = loader.discover_scripts(skill_path, manifest)

        assert len(scripts) == 1
        assert scripts[0]["name"] == "status"
        assert scripts[0]["path"] == scripts_dir / "status.py"


class TestSecurityChecks:
    """Test security-related checks in loader."""

    def test_reject_script_with_path_separator(self, mock_config, tmp_path):
        """Should reject scripts with path separators."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        manifest = SkillManifest(name="test-skill", description="test", scripts=["../malicious.py"])

        scripts = loader.discover_scripts(skill_path, manifest)
        assert scripts == []

    def test_reject_script_with_backslash(self, mock_config, tmp_path):
        """Should reject scripts with backslashes."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        manifest = SkillManifest(
            name="test-skill", description="test", scripts=["..\\malicious.py"]
        )

        scripts = loader.discover_scripts(skill_path, manifest)
        assert scripts == []

    def test_reject_script_escaping_directory(self, mock_config, tmp_path):
        """Should reject scripts that escape scripts/ directory."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        manifest = SkillManifest(name="test-skill", description="test", scripts=[".."])

        scripts = loader.discover_scripts(skill_path, manifest)
        assert scripts == []

    def test_warn_on_missing_explicit_script(self, mock_config, tmp_path):
        """Should warn when explicitly listed script is missing."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        manifest = SkillManifest(name="test-skill", description="test", scripts=["nonexistent.py"])

        scripts = loader.discover_scripts(skill_path, manifest)
        assert scripts == []

    def test_skip_symlinks_in_auto_discover(self, mock_config, tmp_path):
        """Should skip symbolic links during auto-discovery."""
        import os

        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create a real script
        (scripts_dir / "real.py").write_text("# real")

        # Create a symlink (if platform supports it)
        try:
            os.symlink(scripts_dir / "real.py", scripts_dir / "link.py")
        except (OSError, NotImplementedError):
            pytest.skip("Platform doesn't support symlinks")

        manifest = SkillManifest(name="test-skill", description="test", scripts=None)

        scripts = loader.discover_scripts(skill_path, manifest)

        # Should only find real.py, not the symlink
        assert len(scripts) == 1
        assert scripts[0]["name"] == "real"

    def test_skip_non_directories_in_scan(self, mock_config, tmp_path):
        """Should skip non-directory items during scan."""
        loader = SkillLoader(mock_config)

        # Create a file (not directory) with SKILL.md name
        (tmp_path / "not-a-dir.txt").write_text("some file")

        # Create a valid skill
        skill1 = tmp_path / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: skill1\ndescription: test\n---\n")

        result = loader.scan_skill_directory(tmp_path)

        # Should only find skill1
        assert len(result) == 1
        assert skill1 in result


class TestToolsetImporting:
    """Test toolset importing functionality."""

    def test_import_toolset_invalid_format(self, mock_config, tmp_path):
        """Should return None for invalid toolset definition."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()

        result = loader._import_toolset(skill_path, "test-skill", "InvalidFormat")

        assert result is None

    def test_import_toolset_file_not_found(self, mock_config, tmp_path):
        """Should return None when toolset file doesn't exist."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()

        result = loader._import_toolset(skill_path, "test-skill", "toolsets.nonexistent:MyToolset")

        assert result is None

    def test_import_toolset_class_not_found(self, mock_config, tmp_path):
        """Should return None when class doesn't exist in module."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        toolsets_dir = skill_path / "toolsets"
        toolsets_dir.mkdir(parents=True)

        # Create module without the expected class
        (toolsets_dir / "mytools.py").write_text(
            """
from agent.tools.toolset import AgentToolset

class WrongClass(AgentToolset):
    def get_tools(self):
        return []
"""
        )

        result = loader._import_toolset(skill_path, "test-skill", "toolsets.mytools:MyToolset")

        assert result is None

    def test_import_toolset_not_subclass(self, mock_config, tmp_path):
        """Should return None when class doesn't inherit from AgentToolset."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        toolsets_dir = skill_path / "toolsets"
        toolsets_dir.mkdir(parents=True)

        # Create class that doesn't inherit from AgentToolset
        (toolsets_dir / "mytools.py").write_text(
            """
class MyToolset:
    pass
"""
        )

        result = loader._import_toolset(skill_path, "test-skill", "toolsets.mytools:MyToolset")

        assert result is None

    def test_import_toolset_success(self, mock_config, tmp_path):
        """Should successfully import valid toolset."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        toolsets_dir = skill_path / "toolsets"
        toolsets_dir.mkdir(parents=True)

        (toolsets_dir / "mytools.py").write_text(
            """
from agent.tools.toolset import AgentToolset

class MyToolset(AgentToolset):
    def get_tools(self):
        return []
"""
        )

        result = loader._import_toolset(skill_path, "test-skill", "toolsets.mytools:MyToolset")

        assert result is not None
        from agent.tools.toolset import AgentToolset

        assert isinstance(result, AgentToolset)

    def test_load_skill_with_toolsets(self, mock_config, tmp_path):
        """Should load skill with toolsets."""
        loader = SkillLoader(mock_config)

        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()
        toolsets_dir = skill_path / "toolsets"
        toolsets_dir.mkdir()

        (skill_path / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
toolsets:
  - toolsets.mytools:MyToolset
---

# Test Skill
"""
        )

        (toolsets_dir / "mytools.py").write_text(
            """
from agent.tools.toolset import AgentToolset

class MyToolset(AgentToolset):
    def get_tools(self):
        return []
"""
        )

        manifest, toolsets, scripts = loader.load_skill(skill_path)

        assert manifest.name == "test-skill"
        assert len(toolsets) == 1
        from agent.tools.toolset import AgentToolset

        assert isinstance(toolsets[0], AgentToolset)


class TestLoadEnabledSkills:
    """Test load_enabled_skills functionality."""

    def test_load_with_core_skills_dir(self, mock_config, tmp_path):
        """Should load skills from bundled_dir."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        skill1 = bundled_dir / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: skill1\ndescription: test skill 1\n---\n")

        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should load the skill
        assert script_wrapper is None  # No scripts

    def test_load_with_user_skills_dir(self, mock_config, tmp_path):
        """Should load skills from user skills directory (plugins)."""
        user_dir = tmp_path / "user"
        user_dir.mkdir()

        skill1 = user_dir / "my-skill"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: my-skill\ndescription: test skill\n---\n")

        # Create a plugin entry
        plugin = Mock()
        plugin.name = "my-skill"
        plugin.enabled = True
        plugin.installed_path = str(skill1)

        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = None
        mock_config.skills.plugins = [plugin]
        mock_config.skills.user_dir = str(user_dir)

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        assert script_wrapper is None

    def test_load_all_skills(self, mock_config, tmp_path):
        """Should load all bundled skills (auto-discovery)."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        skill1 = bundled_dir / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: skill1\ndescription: test skill 1\n---\n")

        skill2 = bundled_dir / "skill2"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("---\nname: skill2\ndescription: test skill 2\n---\n")

        mock_config.skills.disabled_bundled = []  # None disabled, load all
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should load both skills
        assert script_wrapper is None

    def test_load_skills_with_scripts_creates_wrapper(self, mock_config, tmp_path):
        """Should create script wrapper when skills have scripts."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        skill1 = bundled_dir / "skill1"
        skill1.mkdir()
        scripts_dir = skill1 / "scripts"
        scripts_dir.mkdir()

        (skill1 / "SKILL.md").write_text(
            "---\nname: skill1\ndescription: test skill with scripts\n---\n"
        )
        (scripts_dir / "status.py").write_text("# status script")

        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should create script wrapper
        assert script_wrapper is not None
        from agent.skills.script_tools import ScriptToolset

        assert isinstance(script_wrapper, ScriptToolset)

    def test_skip_invalid_manifest_continue_loading(self, mock_config, tmp_path):
        """Should continue loading other skills when one has invalid manifest."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        # Invalid skill
        bad_skill = bundled_dir / "bad-skill"
        bad_skill.mkdir()
        (bad_skill / "SKILL.md").write_text("invalid yaml {]")

        # Valid skill
        good_skill = bundled_dir / "good-skill"
        good_skill.mkdir()
        (good_skill / "SKILL.md").write_text(
            "---\nname: good-skill\ndescription: valid skill\n---\n"
        )

        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should load good-skill despite bad-skill failing
        assert script_wrapper is None

    def test_skill_name_matching_case_insensitive(self, mock_config, tmp_path):
        """Should match skill names case-insensitively when checking disabled list."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        skill1 = bundled_dir / "MySkill"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: MySkill\ndescription: test skill\n---\n")

        # Disable with lowercase
        mock_config.skills.disabled_bundled = ["myskill"]
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should skip the disabled skill completely
        assert script_wrapper is None
        assert toolsets == []
        assert not skill_docs.has_skills()

    def test_skill_name_matching_hyphen_underscore_equivalence(self, mock_config, tmp_path):
        """Should treat hyphens and underscores as equivalent when checking disabled list."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        skill1 = bundled_dir / "my-skill"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: my-skill\ndescription: test skill\n---\n")

        # Disable with underscore
        mock_config.skills.disabled_bundled = ["my_skill"]
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should skip the disabled skill completely
        assert script_wrapper is None
        assert toolsets == []
        assert not skill_docs.has_skills()

    def test_skill_without_instructions_added_to_docs_index(self, mock_config, tmp_path):
        """Should add skills to documentation index even without instructions."""
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        # Skill with no instructions (empty after frontmatter)
        skill1 = bundled_dir / "api-skill"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text(
            "---\nname: api-skill\ndescription: API client skill\n---\n"
        )

        mock_config.skills.disabled_bundled = []
        mock_config.skills.bundled_dir = str(bundled_dir)
        mock_config.skills.plugins = []
        mock_config.skills.user_dir = None

        loader = SkillLoader(mock_config)
        toolsets, script_wrapper, skill_docs = loader.load_enabled_skills()

        # Should have the skill in documentation index even without instructions
        assert skill_docs.has_skills()
        assert skill_docs.count() == 1
        metadata = skill_docs.get_all_metadata()
        assert len(metadata) == 1
        assert metadata[0]["name"] == "api-skill"
