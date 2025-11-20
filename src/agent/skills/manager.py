"""Skill manager for lifecycle operations.

This module handles skill installation, updates, and removal with git operations.
"""

import gc
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from git import Repo

from agent.skills.errors import SkillError
from agent.skills.manifest import SkillRegistryEntry, parse_skill_manifest
from agent.skills.registry import SkillRegistry
from agent.skills.security import normalize_skill_name, pin_commit_sha, validate_manifest

logger = logging.getLogger(__name__)


class SkillManager:
    """Manage skill lifecycle: install, update, remove.

    Handles git operations for skill installation from repositories.

    Example:
        >>> manager = SkillManager()
        >>> manager.install("https://github.com/example/skill", trusted=True)
    """

    def __init__(self, skills_dir: Path | None = None):
        """Initialize skill manager.

        Args:
            skills_dir: Directory for installed skills (default: ~/.agent/skills)
        """
        if skills_dir is None:
            skills_dir = Path.home() / ".agent" / "skills"

        self.skills_dir = skills_dir

        # Use registry in skills_dir to keep tests isolated
        registry_path = self.skills_dir / "registry.json"
        self.registry = SkillRegistry(registry_path=registry_path)

        # Ensure skills directory exists
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def install(
        self,
        git_url: str,
        skill_name: str | None = None,
        branch: str | None = None,
        tag: str | None = None,
        trusted: bool = False,
    ) -> list[SkillRegistryEntry]:
        """Install skill(s) from a git repository.

        Supports multiple repository structures:
        - Single-skill: SKILL.md in repository root
        - Single-skill subdirectory: SKILL.md in skill/ subdirectory
        - Monorepo: Multiple subdirectories each containing SKILL.md
        - Marketplace: plugins/{plugin-name}/skills/{skill-name}/SKILL.md (Claude Code compatible)

        Args:
            git_url: Git repository URL
            skill_name: Custom skill name for single-skill repos (auto-detected if None)
            branch: Git branch to clone (default: main/master)
            tag: Git tag to checkout (takes precedence over branch)
            trusted: Mark skill as trusted (skip confirmation prompt)

        Returns:
            List of SkillRegistryEntry for installed skills (single-skill: 1 entry, monorepo/marketplace: multiple)

        Raises:
            SkillError: If installation fails
            SkillManifestError: If SKILL.md is invalid
        """
        # Clean up any leftover temporary directories from previous runs
        # Do this at the start of install() to avoid interfering with tests
        self._cleanup_temp_dirs()

        # Early check for duplicate if skill_name is provided
        if skill_name:
            canonical_check = normalize_skill_name(skill_name)
            if self.registry.exists(canonical_check):
                raise SkillError(f"Skill '{canonical_check}' is already installed")

        temp_dir = None
        repo = None
        try:
            # Clone to temporary directory first
            temp_dir = self.skills_dir / f".temp-{datetime.now().timestamp()}"
            logger.info(f"Cloning skill from {git_url}...")

            # Clone repository
            clone_kwargs: dict[str, Any] = {"depth": 1}  # Shallow clone for speed
            if branch:
                clone_kwargs["branch"] = branch

            repo = Repo.clone_from(git_url, temp_dir, **clone_kwargs)

            # Checkout tag if specified
            if tag:
                repo.git.checkout(tag)

            # Get commit SHA
            commit_sha = pin_commit_sha(temp_dir)

            # Detect repository structure (priority order)
            root_manifest = temp_dir / "SKILL.md"
            skill_subdir_manifest = temp_dir / "skill" / "SKILL.md"
            plugins_dir = temp_dir / "plugins"

            if root_manifest.exists():
                # Scenario 1: Single-skill repository (SKILL.md in root)
                logger.info("Detected single-skill repo (SKILL.md at root)")
                return self._install_single_skill(
                    temp_dir, git_url, commit_sha, branch, tag, trusted, skill_name
                )
            elif skill_subdir_manifest.exists():
                # Scenario 2: Single-skill in skill/ subdirectory
                # Common for repos with docs/tests at root, skill in subfolder
                logger.info("Detected single-skill repo (SKILL.md in skill/ subdirectory)")
                skill_dir = temp_dir / "skill"
                return self._install_single_skill(
                    skill_dir, git_url, commit_sha, branch, tag, trusted, skill_name
                )
            elif plugins_dir.exists() and plugins_dir.is_dir():
                # Scenario 3: Claude Code marketplace structure
                # Check if plugins/ contains subdirectories with skills/ subdirectory
                has_marketplace_structure = False
                for item in plugins_dir.iterdir():
                    if item.is_dir() and (item / "skills").is_dir():
                        has_marketplace_structure = True
                        break

                if has_marketplace_structure:
                    logger.info("Detected Claude Code marketplace structure")
                    return self._install_marketplace_plugins(
                        temp_dir, git_url, commit_sha, branch, tag, trusted
                    )

            # Scenario 4: Monorepo - scan for subdirectories with SKILL.md
            logger.info("Scanning for monorepo structure (multiple skills)")
            return self._install_monorepo_skills(
                temp_dir, git_url, commit_sha, branch, tag, trusted
            )

        except Exception as e:
            logger.error(f"Failed to install skill: {e}")
            raise SkillError(f"Installation failed: {e}")

        finally:
            # Close git repository to release file handles (important on Windows)
            if repo is not None:
                repo.close()
                # On Windows, GitPython may not immediately release all file handles
                # Force garbage collection to ensure cleanup
                if sys.platform == "win32":
                    del repo
                    gc.collect()

            # Cleanup temp directory if it still exists
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except (PermissionError, FileNotFoundError) as e:
                    # On Windows, sometimes file handles aren't immediately released (PermissionError)
                    # or the directory was already moved (FileNotFoundError)
                    # Log the error but don't fail the installation if it succeeded
                    if isinstance(e, PermissionError):
                        logger.warning(
                            f"Could not delete temporary directory {temp_dir}: {e}. "
                            "This is harmless and will be cleaned up on next run."
                        )

    def _install_single_skill(
        self,
        temp_dir: Path,
        git_url: str,
        commit_sha: str,
        branch: str | None,
        tag: str | None,
        trusted: bool,
        skill_name: str | None = None,
    ) -> list[SkillRegistryEntry]:
        """Install a single skill from repository root.

        Args:
            temp_dir: Temporary directory with cloned repo
            git_url: Git repository URL
            commit_sha: Commit SHA
            branch: Git branch used
            tag: Git tag used
            trusted: Trusted flag
            skill_name: Optional custom skill name

        Returns:
            List with single SkillRegistryEntry
        """
        # Validate SKILL.md
        manifest_path = temp_dir / "SKILL.md"
        validate_manifest(manifest_path)

        # Parse manifest
        manifest = parse_skill_manifest(temp_dir)

        # Use manifest name or custom name
        final_name = skill_name or manifest.name
        canonical_name = normalize_skill_name(final_name)

        # Check if already installed
        if self.registry.exists(canonical_name):
            raise SkillError(f"Skill '{canonical_name}' is already installed")

        # Move to final location
        final_path = self.skills_dir / canonical_name
        if final_path.exists():
            shutil.rmtree(final_path)

        shutil.move(str(temp_dir), str(final_path))

        # Register skill
        entry = SkillRegistryEntry(
            name=final_name,
            name_canonical=canonical_name,
            git_url=git_url,
            commit_sha=commit_sha,
            branch=branch,
            tag=tag,
            installed_path=final_path,
            trusted=trusted,
            installed_at=datetime.now(),
        )

        self.registry.register(entry)

        logger.info(f"Successfully installed skill '{final_name}' at {final_path}")
        return [entry]

    def _install_monorepo_skills(
        self,
        temp_dir: Path,
        git_url: str,
        commit_sha: str,
        branch: str | None,
        tag: str | None,
        trusted: bool,
    ) -> list[SkillRegistryEntry]:
        """Install multiple skills from a monorepo structure.

        Scans for subdirectories containing SKILL.md and installs each as a separate skill.

        Args:
            temp_dir: Temporary directory with cloned repo
            git_url: Git repository URL
            commit_sha: Commit SHA
            branch: Git branch used
            tag: Git tag used
            trusted: Trusted flag

        Returns:
            List of SkillRegistryEntry for all installed skills
        """
        # Scan for skill subdirectories
        skill_dirs = []
        for item in temp_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                skill_md = item / "SKILL.md"
                if skill_md.exists() and skill_md.is_file():
                    skill_dirs.append(item)

        if not skill_dirs:
            raise SkillError(
                "No skills found in repository. Expected SKILL.md in root or subdirectories."
            )

        logger.info(f"Found {len(skill_dirs)} skills in monorepo")

        # Install each skill
        installed_entries = []
        for skill_dir in skill_dirs:
            try:
                # Validate SKILL.md
                manifest_path = skill_dir / "SKILL.md"
                validate_manifest(manifest_path)

                # Parse manifest
                manifest = parse_skill_manifest(skill_dir)
                canonical_name = normalize_skill_name(manifest.name)

                # Check if already installed
                if self.registry.exists(canonical_name):
                    logger.warning(f"Skill '{canonical_name}' already installed, skipping")
                    continue

                # Copy skill directory to final location
                final_path = self.skills_dir / canonical_name
                if final_path.exists():
                    shutil.rmtree(final_path)

                shutil.copytree(skill_dir, final_path)

                # Register skill
                entry = SkillRegistryEntry(
                    name=manifest.name,
                    name_canonical=canonical_name,
                    git_url=git_url,
                    commit_sha=commit_sha,
                    branch=branch,
                    tag=tag,
                    installed_path=final_path,
                    trusted=trusted,
                    installed_at=datetime.now(),
                )

                self.registry.register(entry)
                installed_entries.append(entry)

                logger.info(f"Successfully installed skill '{manifest.name}' at {final_path}")

            except Exception as e:
                logger.error(f"Failed to install skill from {skill_dir.name}: {e}")
                # Continue with other skills
                continue

        if not installed_entries:
            raise SkillError("No skills were successfully installed from repository")

        return installed_entries

    def _install_marketplace_plugins(
        self,
        temp_dir: Path,
        git_url: str,
        commit_sha: str,
        branch: str | None,
        tag: str | None,
        trusted: bool,
    ) -> list[SkillRegistryEntry]:
        """Install skills from Claude Code marketplace structure.

        Scans plugins/{plugin-name}/skills/{skill-name}/SKILL.md pattern
        and installs each skill found.

        Args:
            temp_dir: Temporary directory with cloned repo
            git_url: Git repository URL
            commit_sha: Commit SHA
            branch: Git branch used
            tag: Git tag used
            trusted: Trusted flag

        Returns:
            List of SkillRegistryEntry for all installed skills
        """
        plugins_dir = temp_dir / "plugins"
        skill_dirs = []

        # Scan marketplace structure: plugins/*/skills/*/SKILL.md
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue

            skills_subdir = plugin_dir / "skills"
            if not skills_subdir.exists() or not skills_subdir.is_dir():
                continue

            # Scan for skills within this plugin's skills/ directory
            for skill_dir in skills_subdir.iterdir():
                if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                    skill_md = skill_dir / "SKILL.md"
                    if skill_md.exists() and skill_md.is_file():
                        skill_dirs.append(skill_dir)

        if not skill_dirs:
            raise SkillError(
                "No skills found in marketplace structure. "
                "Expected plugins/{plugin}/skills/{skill}/SKILL.md"
            )

        logger.info(f"Found {len(skill_dirs)} skills in marketplace structure")

        # Install each skill
        installed_entries = []
        for skill_dir in skill_dirs:
            try:
                # Validate SKILL.md
                manifest_path = skill_dir / "SKILL.md"
                validate_manifest(manifest_path)

                # Parse manifest
                manifest = parse_skill_manifest(skill_dir)
                canonical_name = normalize_skill_name(manifest.name)

                # Check if already installed
                if self.registry.exists(canonical_name):
                    logger.warning(f"Skill '{canonical_name}' already installed, skipping")
                    continue

                # Copy skill directory to final location
                final_path = self.skills_dir / canonical_name
                if final_path.exists():
                    shutil.rmtree(final_path)

                shutil.copytree(skill_dir, final_path)

                # Register skill
                entry = SkillRegistryEntry(
                    name=manifest.name,
                    name_canonical=canonical_name,
                    git_url=git_url,
                    commit_sha=commit_sha,
                    branch=branch,
                    tag=tag,
                    installed_path=final_path,
                    trusted=trusted,
                    installed_at=datetime.now(),
                )

                self.registry.register(entry)
                installed_entries.append(entry)

                logger.info(f"Successfully installed skill '{manifest.name}' at {final_path}")

            except Exception as e:
                logger.error(f"Failed to install skill from {skill_dir.name}: {e}")
                # Continue with other skills
                continue

        if not installed_entries:
            raise SkillError("No skills were successfully installed from marketplace")

        return installed_entries

    def update(self, skill_name: str, confirm: bool = True) -> SkillRegistryEntry:
        """Update a skill to the latest version.

        Uses uninstall + reinstall strategy to ensure clean updates.
        Works with all repository structures (single-skill, monorepo, marketplace).

        Args:
            skill_name: Skill name to update
            confirm: Require confirmation for update (Phase 2)

        Returns:
            Updated SkillRegistryEntry

        Raises:
            SkillNotFoundError: If skill not found
            SkillError: If update fails
        """
        canonical_name = normalize_skill_name(skill_name)
        entry = self.registry.get(canonical_name)

        if entry.git_url is None:
            raise SkillError(f"Skill '{skill_name}' is a bundled skill and cannot be updated")

        # Save installation parameters
        git_url = entry.git_url
        branch = entry.branch
        tag = entry.tag
        trusted = entry.trusted
        old_sha = entry.commit_sha

        try:
            logger.info(f"Updating skill '{skill_name}' (uninstall + reinstall)")

            # Step 1: Remove existing installation
            self.remove(skill_name)

            # Step 2: Reinstall from original source (use entry.name to preserve original casing)
            entries = self.install(
                git_url=git_url, branch=branch, tag=tag, trusted=trusted, skill_name=entry.name
            )

            # Find the updated entry (should be first for single-skill, or match name for monorepo)
            updated_entry = next((e for e in entries if e.name_canonical == canonical_name), None)
            if not updated_entry:
                raise SkillError(f"Skill '{skill_name}' not found after reinstall")

            new_sha = updated_entry.commit_sha

            # Format SHAs for logging (should always exist for git skills, but handle None for type safety)
            old_sha_short = old_sha[:8] if old_sha else "unknown"
            new_sha_short = new_sha[:8] if new_sha else "unknown"

            logger.info(
                f"Successfully updated skill '{skill_name}' from {old_sha_short} to {new_sha_short}"
            )
            return updated_entry

        except Exception as e:
            logger.error(f"Failed to update skill: {e}")
            raise SkillError(f"Update failed: {e}")

    def remove(self, skill_name: str) -> None:
        """Remove an installed skill.

        Args:
            skill_name: Skill name to remove

        Raises:
            SkillNotFoundError: If skill not found
            SkillError: If removal fails
        """
        canonical_name = normalize_skill_name(skill_name)
        entry = self.registry.get(canonical_name)

        try:
            # Remove directory
            if entry.installed_path.exists():
                shutil.rmtree(entry.installed_path)
                logger.info(f"Removed skill directory: {entry.installed_path}")

            # Unregister
            self.registry.unregister(canonical_name)

            logger.info(f"Successfully removed skill '{skill_name}'")

        except Exception as e:
            logger.error(f"Failed to remove skill: {e}")
            raise SkillError(f"Removal failed: {e}")

    def list_installed(self) -> list[SkillRegistryEntry]:
        """List all installed skills.

        Returns:
            List of SkillRegistryEntry, sorted by canonical name
        """
        return self.registry.list()

    def info(self, skill_name: str) -> dict:
        """Get detailed information about a skill.

        Args:
            skill_name: Skill name

        Returns:
            Dict with skill metadata, manifest, scripts, and toolsets

        Raises:
            SkillNotFoundError: If skill not found
        """
        canonical_name = normalize_skill_name(skill_name)
        entry = self.registry.get(canonical_name)

        # Parse manifest
        manifest = parse_skill_manifest(entry.installed_path)

        # Count scripts
        scripts_dir = entry.installed_path / "scripts"
        script_count = 0
        if scripts_dir.exists():
            script_count = len(list(scripts_dir.glob("*.py")))

        return {
            "name": entry.name,
            "canonical_name": entry.name_canonical,
            "description": manifest.description,
            "version": manifest.version,
            "author": manifest.author,
            "repository": manifest.repository,
            "git_url": entry.git_url,
            "commit_sha": entry.commit_sha,
            "branch": entry.branch,
            "tag": entry.tag,
            "installed_path": str(entry.installed_path),
            "trusted": entry.trusted,
            "installed_at": entry.installed_at.isoformat(),
            "toolsets_count": len(manifest.toolsets),
            "scripts_count": script_count,
            "toolsets": manifest.toolsets,
        }

    def _cleanup_temp_dirs(self) -> None:
        """Clean up temporary directories from previous runs.

        On Windows, GitPython sometimes doesn't release file handles immediately,
        leaving temporary directories behind. This method attempts to clean them up.

        Only removes temp directories that are "stale" - either older than 1 hour,
        or from a timestamp that's clearly invalid (e.g., from test mocking in the past).
        """
        if not self.skills_dir.exists():
            return

        current_time = datetime.now().timestamp()
        one_minute_ago = current_time - 60  # 1 minute in seconds
        one_hour_ago = current_time - 3600  # 1 hour in seconds

        for item in self.skills_dir.iterdir():
            if item.is_dir() and item.name.startswith(".temp-"):
                try:
                    # Extract timestamp from directory name: .temp-{timestamp}
                    timestamp_str = item.name[len(".temp-") :]
                    dir_timestamp = float(timestamp_str)

                    # Only remove if older than 1 hour OR if timestamp is in the far past (likely from tests)
                    # Directories created within the last minute are considered "in progress" and left alone
                    is_stale = (
                        dir_timestamp < one_hour_ago  # Older than 1 hour
                        and dir_timestamp < one_minute_ago  # Not brand new
                    )

                    if is_stale:
                        shutil.rmtree(item)
                        logger.debug(f"Cleaned up leftover temp directory: {item}")
                except ValueError:
                    # Invalid timestamp format, skip
                    logger.debug(f"Skipping temp directory with invalid timestamp: {item}")
                except Exception as e:
                    # If we can't delete it now, it might still be in use
                    # or have permission issues. Just log and continue.
                    logger.debug(f"Could not clean up temp directory {item}: {e}")
