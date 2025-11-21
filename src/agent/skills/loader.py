"""Skill loader for discovering and loading skills.

This module handles skill discovery, manifest parsing, script metadata collection,
and dynamic toolset importing.
"""

import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent.skills.errors import SkillManifestError
from agent.skills.manifest import SkillManifest, parse_skill_manifest
from agent.skills.registry import SkillRegistry
from agent.skills.security import normalize_script_name, normalize_skill_name
from agent.tools.toolset import AgentToolset

if TYPE_CHECKING:
    from agent.skills.documentation_index import SkillDocumentationIndex

logger = logging.getLogger(__name__)


class SkillLoader:
    """Load and manage skills for the agent.

    Handles skill discovery, manifest parsing, toolset instantiation,
    and script metadata collection.

    Example:
        >>> from agent.config import AgentConfig
        >>> config = AgentConfig.from_env()
        >>> loader = SkillLoader(config)
        >>> toolsets, script_tools, skill_instructions = loader.load_enabled_skills()
    """

    def __init__(self, config: Any):
        """Initialize skill loader.

        Args:
            config: AgentConfig with skill paths and enabled skills list
        """
        self.config = config
        self.registry = SkillRegistry()
        self._loaded_scripts: dict[str, list[dict[str, Any]]] = {}

    def scan_skill_directory(self, directory: Path) -> list[Path]:
        """Scan directory for skills (SKILL.md files).

        Args:
            directory: Directory to scan for skills

        Returns:
            List of skill directory paths containing SKILL.md
        """
        if not directory.exists():
            return []

        skill_dirs = []
        for item in directory.iterdir():
            if not item.is_dir():
                continue

            skill_md = item / "SKILL.md"
            if skill_md.exists() and skill_md.is_file():
                skill_dirs.append(item)

        return skill_dirs

    def discover_scripts(self, skill_path: Path, manifest: SkillManifest) -> list[dict[str, Any]]:
        """Discover scripts in skill's scripts/ directory.

        Args:
            skill_path: Path to skill directory
            manifest: Parsed SKILL.md manifest

        Returns:
            List of script metadata dicts with 'name' and 'path' keys
        """
        scripts_dir = skill_path / "scripts"
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return []

        scripts = []

        # If manifest specifies scripts explicitly, use those
        if manifest.scripts is not None:
            for script_name in manifest.scripts:
                # SECURITY: Reject script names with path separators (prevent traversal)
                if "/" in script_name or "\\" in script_name or ".." in script_name:
                    logger.error(
                        f"Security: Rejected script '{script_name}' with path separators "
                        f"in skill '{manifest.name}'"
                    )
                    continue

                # Normalize script name (add .py if missing)
                normalized = normalize_script_name(script_name)
                script_path = scripts_dir / normalized

                # SECURITY: Verify script is actually within scripts_dir
                try:
                    script_path.resolve().relative_to(scripts_dir.resolve())
                except ValueError:
                    logger.error(
                        f"Security: Rejected script '{script_name}' - "
                        f"path escapes scripts directory in skill '{manifest.name}'"
                    )
                    continue

                if script_path.exists() and script_path.is_file():
                    scripts.append({"name": normalized.removesuffix(".py"), "path": script_path})
                else:
                    logger.warning(
                        f"Script '{script_name}' listed in manifest but not found: {script_path}"
                    )
        else:
            # Auto-discover: scan for *.py files, excluding patterns
            for script_file in scripts_dir.glob("*.py"):
                # Skip if matches ignore patterns
                if self._should_ignore_script(script_file, manifest.scripts_ignore):
                    continue

                # Skip non-files (shouldn't happen with glob but be safe)
                if not script_file.is_file():
                    continue

                # Skip symbolic links for security
                if script_file.is_symlink():
                    logger.warning(f"Skipping symbolic link script: {script_file}")
                    continue

                script_name = script_file.stem  # Remove .py extension
                scripts.append({"name": script_name, "path": script_file})

        return scripts

    def _should_ignore_script(self, script_path: Path, ignore_patterns: list[str]) -> bool:
        """Check if script matches any ignore pattern.

        Args:
            script_path: Path to script file
            ignore_patterns: List of glob patterns to exclude

        Returns:
            True if script should be ignored
        """
        for pattern in ignore_patterns:
            if script_path.match(pattern):
                return True
        return False

    def _import_toolset(
        self, skill_path: Path, skill_name: str, toolset_def: str
    ) -> AgentToolset | None:
        """Dynamically import and instantiate a toolset class.

        Args:
            skill_path: Path to skill directory
            skill_name: Skill name (for logging)
            toolset_def: Toolset definition in "module:Class" format

        Returns:
            Instantiated toolset or None if import failed
        """
        try:
            # Parse "module:Class" format
            if ":" not in toolset_def:
                logger.error(f"Invalid toolset format '{toolset_def}' in skill '{skill_name}'")
                return None

            module_path, class_name = toolset_def.split(":", 1)

            # Convert module path to file path (e.g., "toolsets.hello" -> "toolsets/hello.py")
            file_path = skill_path / f"{module_path.replace('.', '/')}.py"

            if not file_path.exists():
                logger.error(f"Toolset file not found: {file_path}")
                return None

            # Dynamic import
            spec = importlib.util.spec_from_file_location(
                f"skill.{skill_name}.{module_path}", file_path
            )
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get class and validate it's an AgentToolset
            if not hasattr(module, class_name):
                logger.error(f"Class '{class_name}' not found in {file_path}")
                return None

            toolset_class = getattr(module, class_name)

            if not issubclass(toolset_class, AgentToolset):
                logger.error(f"Class '{class_name}' must inherit from AgentToolset")
                return None

            # Instantiate with config
            instance: AgentToolset = toolset_class(self.config)
            return instance

        except Exception as e:
            logger.error(f"Failed to import toolset '{toolset_def}' from skill '{skill_name}': {e}")
            return None

    def load_skill(self, skill_path: Path) -> tuple[SkillManifest, list[AgentToolset], list[dict]]:
        """Load a single skill from a directory.

        Args:
            skill_path: Path to skill directory containing SKILL.md

        Returns:
            Tuple of (manifest, toolset_instances, script_metadata)

        Raises:
            SkillManifestError: If manifest is invalid
        """
        # Parse manifest
        manifest = parse_skill_manifest(skill_path)

        # Load toolsets (if any)
        toolsets = []
        for toolset_def in manifest.toolsets:
            toolset = self._import_toolset(skill_path, manifest.name, toolset_def)
            if toolset is not None:
                toolsets.append(toolset)

        # Discover scripts (metadata only, don't load code)
        scripts = self.discover_scripts(skill_path, manifest)

        return manifest, toolsets, scripts

    def load_enabled_skills(self) -> tuple[list[AgentToolset], Any, "SkillDocumentationIndex"]:
        """Load all enabled skills based on configuration.

        This is the main entry point called by Agent.__init__().

        Behavior:
        - Auto-discovers all bundled skills (opt-out via disabled_bundled)
        - Loads plugin skills from config.skills.plugins (only if enabled=true)

        Returns:
            Tuple of (skill_toolsets, script_wrapper_toolset, skill_documentation_index)

        Raises:
            SkillError: If critical skill loading fails
        """
        # Get skills config
        skills_config = self.config.skills

        # Get disabled bundled skills list
        disabled_bundled = getattr(skills_config, "disabled_bundled", [])

        # Get canonical names for disabled skills (normalize for matching)
        disabled_canonical = {normalize_skill_name(name) for name in disabled_bundled}

        # Collect all skill directories to scan
        bundled_skill_dirs = []
        plugin_skill_dirs = []

        # 1. Auto-discover bundled skills (always scan unless explicitly disabled)
        bundled_dir = getattr(skills_config, "bundled_dir", None)
        if bundled_dir:
            bundled_path = Path(bundled_dir) if isinstance(bundled_dir, str) else Path(bundled_dir)
            if bundled_path.exists():
                bundled_skill_dirs = self.scan_skill_directory(bundled_path)
                logger.info(f"Auto-discovered {len(bundled_skill_dirs)} bundled skills")

        # 2. Load enabled plugin skills from config.skills.plugins
        plugins = getattr(skills_config, "plugins", [])
        user_dir = getattr(skills_config, "user_dir", None)

        for plugin in plugins:
            if not plugin.enabled:
                continue

            # Try installed_path first, fall back to user_dir/name
            if plugin.installed_path:
                plugin_path = Path(plugin.installed_path)
            elif user_dir:
                plugin_path = Path(user_dir) / normalize_skill_name(plugin.name)
            else:
                logger.warning(f"Plugin '{plugin.name}' has no installed_path and no user_dir set")
                continue

            if plugin_path.exists() and (plugin_path / "SKILL.md").exists():
                plugin_skill_dirs.append(plugin_path)
            else:
                logger.warning(
                    f"Plugin skill '{plugin.name}' not found at {plugin_path}. "
                    f"Run: agent skill install {plugin.git_url}"
                )

        # Load all skills (bundled + plugins)
        all_toolsets = []
        all_scripts = {}

        # Create documentation index for runtime context injection
        from agent.skills.documentation_index import SkillDocumentationIndex

        skill_docs = SkillDocumentationIndex()

        for skill_dir in bundled_skill_dirs + plugin_skill_dirs:
            try:
                manifest, toolsets, scripts = self.load_skill(skill_dir)
                canonical_name = normalize_skill_name(manifest.name)

                # Check if bundled skill is disabled
                is_bundled = skill_dir in bundled_skill_dirs
                if is_bundled and canonical_name in disabled_canonical:
                    logger.info(f"Skipping disabled bundled skill: {manifest.name}")
                    continue

                # Load the skill
                all_toolsets.extend(toolsets)
                if scripts:
                    all_scripts[canonical_name] = scripts
                    self._loaded_scripts[canonical_name] = scripts

                # Add skill to documentation index for progressive disclosure
                # Always add, even if instructions are empty - skill may have triggers/toolsets/scripts
                skill_docs.add_skill(canonical_name, manifest)

                logger.info(
                    f"Loaded {'bundled' if is_bundled else 'plugin'} skill '{manifest.name}': "
                    f"{len(toolsets)} toolsets, {len(scripts)} scripts"
                )

            except SkillManifestError as e:
                logger.error(f"Failed to load skill from {skill_dir}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error loading skill from {skill_dir}: {e}", exc_info=True)
                continue

        # Create script wrapper toolset if we have scripts
        script_wrapper = None
        if all_scripts:
            from agent.skills.script_tools import ScriptToolset

            script_wrapper = ScriptToolset(self.config, all_scripts)

        return all_toolsets, script_wrapper, skill_docs

    def validate_dependencies(self, manifest: SkillManifest) -> None:
        """Validate skill dependencies (for future use).

        Currently a no-op. Phase 2 will add dependency checking for:
        - min/max agent-base version compatibility
        - Python package dependencies for toolsets

        Args:
            manifest: Skill manifest to validate

        Raises:
            SkillDependencyError: If dependencies are not met
        """
        # Phase 2: Check min/max_agent_base_version
        # Phase 2: Check Python package availability for toolsets
        pass
