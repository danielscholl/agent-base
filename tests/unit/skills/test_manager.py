"""Unit tests for skill manager."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from agent.skills.errors import SkillError, SkillNotFoundError
from agent.skills.manager import SkillManager
from agent.skills.manifest import SkillRegistryEntry


@pytest.fixture
def temp_skills_dir(tmp_path):
    """Create temporary skills directory."""
    return tmp_path / "skills"


@pytest.fixture
def mock_repo():
    """Create mock Git repository."""
    repo = MagicMock()
    repo.git = MagicMock()
    repo.remotes.origin = MagicMock()
    return repo


class TestSkillManager:
    """Test SkillManager class."""

    def test_init_default_dir(self):
        """Should use default skills directory."""
        manager = SkillManager()
        expected = Path.home() / ".agent" / "skills"
        assert manager.skills_dir == expected

    def test_init_custom_dir(self, temp_skills_dir):
        """Should use custom skills directory."""
        manager = SkillManager(skills_dir=temp_skills_dir)
        assert manager.skills_dir == temp_skills_dir

    def test_init_creates_directory(self, temp_skills_dir):
        """Should create skills directory if it doesn't exist."""
        SkillManager(skills_dir=temp_skills_dir)
        assert temp_skills_dir.exists()

    @patch("agent.skills.manager.Repo")
    @patch("agent.skills.manager.parse_skill_manifest")
    @patch("agent.skills.manager.pin_commit_sha")
    def test_install_success(
        self, mock_pin_sha, mock_parse_manifest, mock_repo_class, temp_skills_dir
    ):
        """Should install skill from git URL."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_pin_sha.return_value = "abc123def456"

        mock_manifest = Mock()
        mock_manifest.name = "test-skill"
        mock_parse_manifest.return_value = mock_manifest

        # Create mock SKILL.md
        temp_clone = temp_skills_dir / ".temp-1234567890.0"
        temp_clone.mkdir(parents=True)
        (temp_clone / "SKILL.md").write_text("---\nname: test-skill\ndescription: test\n---\n")

        manager = SkillManager(skills_dir=temp_skills_dir)

        with patch("agent.skills.manager.datetime") as mock_dt:
            mock_dt.now.return_value.timestamp.return_value = 1234567890.0
            entries = manager.install("https://github.com/example/test-skill", trusted=True)

        # install() now returns list[SkillRegistryEntry]
        assert isinstance(entries, list)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.name == "test-skill"
        assert entry.git_url == "https://github.com/example/test-skill"
        assert entry.trusted is True

    @pytest.mark.skip(reason="Phase 2 feature - requires comprehensive git mocking")
    @patch("agent.skills.manager.Repo")
    def test_install_already_installed(self, mock_repo_class, temp_skills_dir):
        """Should reject installing duplicate skill."""
        manager = SkillManager(skills_dir=temp_skills_dir)

        # Pre-register a skill
        existing_entry = SkillRegistryEntry(
            name="test-skill",
            name_canonical="test-skill",
            installed_path=temp_skills_dir / "test-skill",
        )
        manager.registry.register(existing_entry)

        # Try to install again (should fail before git clone happens)
        with pytest.raises(SkillError, match="already installed"):
            manager.install("https://github.com/example/test-skill")

    @patch("agent.skills.manager.Repo")
    @patch("agent.skills.manager.parse_skill_manifest")
    @patch("agent.skills.manager.pin_commit_sha")
    def test_update_success(self, mock_pin_sha, mock_parse_manifest, mock_repo_class, temp_skills_dir):
        """Should update skill using uninstall + reinstall strategy."""
        # Setup existing installation
        skill_path = temp_skills_dir / "test-skill"
        skill_path.mkdir(parents=True)

        entry = SkillRegistryEntry(
            name="test-skill",
            name_canonical="test-skill",
            git_url="https://github.com/example/test-skill",
            commit_sha="old123",
            branch="main",
            installed_path=skill_path,
            trusted=True,
        )

        manager = SkillManager(skills_dir=temp_skills_dir)
        manager.registry.register(entry)

        # Setup mocks for reinstall
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_pin_sha.return_value = "new456"

        mock_manifest = Mock()
        mock_manifest.name = "test-skill"
        mock_parse_manifest.return_value = mock_manifest

        # Create mock SKILL.md for reinstall
        temp_clone = temp_skills_dir / ".temp-1234567890.0"
        temp_clone.mkdir(parents=True)
        (temp_clone / "SKILL.md").write_text("---\nname: test-skill\ndescription: test\n---\n")

        with patch("agent.skills.manager.datetime") as mock_dt:
            mock_dt.now.return_value.timestamp.return_value = 1234567890.0
            updated = manager.update("test-skill")

        assert updated.commit_sha == "new456"
        assert updated.git_url == "https://github.com/example/test-skill"
        assert updated.branch == "main"

    def test_update_bundled_skill_fails(self, temp_skills_dir):
        """Should reject updating bundled skills (no git_url)."""
        skill_path = temp_skills_dir / "bundled-skill"
        skill_path.mkdir(parents=True)

        entry = SkillRegistryEntry(
            name="bundled-skill",
            name_canonical="bundled-skill",
            git_url=None,  # Bundled skill
            installed_path=skill_path,
        )

        manager = SkillManager(skills_dir=temp_skills_dir)
        manager.registry.register(entry)

        with pytest.raises(SkillError, match="bundled skill"):
            manager.update("bundled-skill")

    def test_remove_success(self, temp_skills_dir):
        """Should remove skill and clean up."""
        skill_path = temp_skills_dir / "test-skill"
        skill_path.mkdir(parents=True)
        (skill_path / "file.txt").write_text("test")

        entry = SkillRegistryEntry(
            name="test-skill",
            name_canonical="test-skill",
            installed_path=skill_path,
        )

        manager = SkillManager(skills_dir=temp_skills_dir)
        manager.registry.register(entry)

        manager.remove("test-skill")

        assert not skill_path.exists()
        assert not manager.registry.exists("test-skill")

    def test_remove_nonexistent(self, temp_skills_dir):
        """Should raise error when removing nonexistent skill."""
        manager = SkillManager(skills_dir=temp_skills_dir)

        with pytest.raises(SkillNotFoundError):
            manager.remove("nonexistent")

    def test_list_installed(self, temp_skills_dir):
        """Should list all installed skills."""
        manager = SkillManager(skills_dir=temp_skills_dir)

        # Install multiple skills
        for i in range(3):
            skill_path = temp_skills_dir / f"skill-{i}"
            skill_path.mkdir(parents=True)

            entry = SkillRegistryEntry(
                name=f"skill-{i}",
                name_canonical=f"skill-{i}",
                installed_path=skill_path,
            )
            manager.registry.register(entry)

        skills = manager.list_installed()
        assert len(skills) == 3

    @patch("agent.skills.manager.parse_skill_manifest")
    def test_info(self, mock_parse_manifest, temp_skills_dir):
        """Should return detailed skill information."""
        skill_path = temp_skills_dir / "test-skill"
        skill_path.mkdir(parents=True)

        # Create SKILL.md
        (skill_path / "SKILL.md").write_text("---\nname: test-skill\ndescription: test\n---\n")

        # Create scripts
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "script1.py").write_text("# script 1")
        (scripts_dir / "script2.py").write_text("# script 2")

        entry = SkillRegistryEntry(
            name="test-skill",
            name_canonical="test-skill",
            installed_path=skill_path,
            git_url="https://github.com/example/test-skill",
            commit_sha="abc123",
        )

        manager = SkillManager(skills_dir=temp_skills_dir)
        manager.registry.register(entry)

        # Mock manifest
        mock_manifest = Mock()
        mock_manifest.description = "A test skill"
        mock_manifest.version = "1.0.0"
        mock_manifest.author = "Test Author"
        mock_manifest.repository = "https://github.com/example/test-skill"
        mock_manifest.toolsets = []
        mock_parse_manifest.return_value = mock_manifest

        info = manager.info("test-skill")

        assert info["name"] == "test-skill"
        assert info["scripts_count"] == 2
        assert info["commit_sha"] == "abc123"


class TestInstallWithBranchAndTag:
    """Test installation with branch and tag options."""

    @patch("agent.skills.manager.Repo")
    @patch("agent.skills.manager.parse_skill_manifest")
    @patch("agent.skills.manager.pin_commit_sha")
    def test_install_with_branch(
        self, mock_pin_sha, mock_parse_manifest, mock_repo_class, temp_skills_dir
    ):
        """Should clone specific branch."""
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_pin_sha.return_value = "abc123"

        mock_manifest = Mock()
        mock_manifest.name = "test-skill"
        mock_parse_manifest.return_value = mock_manifest

        # Create mock SKILL.md
        temp_clone = temp_skills_dir / ".temp-1234567890.0"
        temp_clone.mkdir(parents=True)
        (temp_clone / "SKILL.md").write_text("---\nname: test-skill\ndescription: test\n---\n")

        manager = SkillManager(skills_dir=temp_skills_dir)

        with patch("agent.skills.manager.datetime") as mock_dt:
            mock_dt.now.return_value.timestamp.return_value = 1234567890.0
            entries = manager.install(
                "https://github.com/example/test-skill", branch="develop", trusted=True
            )

        # install() now returns list[SkillRegistryEntry]
        assert isinstance(entries, list)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.branch == "develop"
        # Verify clone_from was called with branch argument
        call_kwargs = mock_repo_class.clone_from.call_args[1]
        assert call_kwargs["branch"] == "develop"


class TestMarketplaceStructure:
    """Test Claude Code marketplace structure support."""

    @patch("agent.skills.manager.Repo")
    @patch("agent.skills.manager.parse_skill_manifest")
    @patch("agent.skills.manager.pin_commit_sha")
    def test_install_marketplace_structure(
        self, mock_pin_sha, mock_parse_manifest, mock_repo_class, temp_skills_dir
    ):
        """Should detect and install from Claude Code marketplace structure."""
        # Setup mocks
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_pin_sha.return_value = "abc123def456"

        # Create mock marketplace structure in temp directory
        temp_clone = temp_skills_dir / ".temp-1234567890.0"
        plugins_dir = temp_clone / "plugins"

        # Create two plugins with skills
        plugin1_dir = plugins_dir / "agent-tools"
        plugin1_skills = plugin1_dir / "skills" / "web"
        plugin1_skills.mkdir(parents=True)
        (plugin1_skills / "SKILL.md").write_text(
            "---\nname: web\ndescription: Web tools\n---\n"
        )
        (plugin1_skills / "scripts").mkdir()
        (plugin1_dir / "plugin.json").write_text('{"name": "agent-tools"}')

        plugin2_dir = plugins_dir / "kalshi-markets"
        plugin2_skills = plugin2_dir / "skills" / "kalshi-markets"
        plugin2_skills.mkdir(parents=True)
        (plugin2_skills / "SKILL.md").write_text(
            "---\nname: kalshi-markets\ndescription: Kalshi API\n---\n"
        )
        (plugin2_skills / "scripts").mkdir()
        (plugin2_dir / "plugin.json").write_text('{"name": "kalshi-markets"}')

        # Mock manifests for both skills
        mock_manifest1 = Mock()
        mock_manifest1.name = "web"
        mock_manifest2 = Mock()
        mock_manifest2.name = "kalshi-markets"
        mock_parse_manifest.side_effect = [mock_manifest1, mock_manifest2]

        manager = SkillManager(skills_dir=temp_skills_dir)

        with patch("agent.skills.manager.datetime") as mock_dt:
            mock_dt.now.return_value.timestamp.return_value = 1234567890.0
            entries = manager.install(
                "https://github.com/danielscholl/agent-skills", branch="marketplace", trusted=True
            )

        # Should install both skills
        assert isinstance(entries, list)
        assert len(entries) == 2
        assert entries[0].name == "web"
        assert entries[1].name == "kalshi-markets"
        assert entries[0].git_url == "https://github.com/danielscholl/agent-skills"
        assert entries[1].git_url == "https://github.com/danielscholl/agent-skills"

    @patch("agent.skills.manager.Repo")
    @patch("agent.skills.manager.pin_commit_sha")
    def test_marketplace_no_skills_found(self, mock_pin_sha, mock_repo_class, temp_skills_dir):
        """Should raise error if plugins/ exists but no skills found."""
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_pin_sha.return_value = "abc123"

        # Create marketplace structure but no SKILL.md files
        temp_clone = temp_skills_dir / ".temp-1234567890.0"
        plugins_dir = temp_clone / "plugins"
        plugin_dir = plugins_dir / "empty-plugin"
        skills_dir = plugin_dir / "skills"
        skills_dir.mkdir(parents=True)

        manager = SkillManager(skills_dir=temp_skills_dir)

        with patch("agent.skills.manager.datetime") as mock_dt:
            mock_dt.now.return_value.timestamp.return_value = 1234567890.0
            with pytest.raises(SkillError, match="No skills found in marketplace"):
                manager.install("https://github.com/example/empty", trusted=True)
