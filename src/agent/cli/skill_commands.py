"""CLI commands for managing agent skills."""

import logging
from importlib import resources
from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt

from agent.cli.utils import get_console
from agent.config import (
    load_config,
    save_config,
)
from agent.config.schema import PluginSkillSource
from agent.skills.manager import SkillManager
from agent.skills.manifest import SkillManifest
from agent.skills.registry import SkillRegistry
from agent.skills.security import normalize_skill_name

console = get_console()
logger = logging.getLogger(__name__)


def _get_toolset_tools(manifest: SkillManifest, skill_path: Path) -> list[tuple[str, int]]:
    """Extract tools from skill's toolsets with their token counts.

    Args:
        manifest: Parsed skill manifest
        skill_path: Path to skill directory

    Returns:
        List of (tool_name, token_count) tuples
    """
    import importlib.util
    import sys

    from agent.config import AgentConfig
    from agent.utils.tokens import count_tokens

    tools_info: list[tuple[str, int]] = []

    if not manifest.toolsets:
        return tools_info

    for toolset_spec in manifest.toolsets:
        try:
            # Parse "module:Class" format
            if ":" not in toolset_spec:
                continue

            module_name, class_name = toolset_spec.split(":", 1)

            # Load module from skill directory
            module_path = skill_path / f"{module_name.replace('.', '/')}.py"
            if not module_path.exists():
                continue

            # Import module dynamically
            spec = importlib.util.spec_from_file_location(
                f"_skill_{skill_path.name}_{module_name}", module_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

                # Get toolset class and instantiate
                toolset_class = getattr(module, class_name, None)
                if toolset_class:
                    # Create minimal config for toolset instantiation
                    config = AgentConfig.from_combined()
                    toolset_instance = toolset_class(config)

                    # Get tools from toolset
                    tools = toolset_instance.get_tools()

                    # Extract docstrings and count tokens
                    for tool in tools:
                        docstring = tool.__doc__ or ""
                        first_line = docstring.strip().split("\n")[0] if docstring.strip() else ""
                        token_count = count_tokens(first_line) if first_line else 0
                        tools_info.append((tool.__name__, token_count))

        except Exception as e:
            # Silently skip failed toolset loads
            logger.debug(f"Failed to load toolset {toolset_spec}: {e}")
            continue

    return tools_info


def _get_repo_paths() -> tuple[Path, str]:
    """Get repository root and bundled skills directory paths.

    Uses importlib.resources to find bundled skills in package.
    Falls back to file-based detection for development.

    Returns:
        tuple: (repo_root, bundled_dir) where bundled_dir is a string path
    """
    # Try package-based location first (works when installed)
    try:
        bundled_skills_path = resources.files("agent").joinpath("_bundled_skills")
        bundled_dir = str(bundled_skills_path)
        # For repo_root, go up from the package location
        repo_root = Path(str(bundled_skills_path)).resolve().parents[2]
    except (ModuleNotFoundError, AttributeError, TypeError) as exc:
        logger.warning(
            "Could not locate bundled skills via importlib.resources: %s. "
            "Falling back to file-based detection.",
            exc,
        )
        # Fall back to file-based detection (development mode)
        repo_root = Path(__file__).resolve().parents[3]
        bundled_dir = str(repo_root / "src" / "agent" / "_bundled_skills")

    return repo_root, bundled_dir


class _MockConfig:
    """Minimal config class for SkillLoader, provides required skills.disabled_bundled attribute."""

    class Skills:
        disabled_bundled: list[str] = []

    skills = Skills()


def manage_skills() -> None:
    """Unified skill management interface (enable/disable/remove/update)."""
    console.print("\n[bold]Manage Skills[/bold]\n")

    try:
        settings = load_config()

        # Get all skills (bundled + plugins)
        bundled_dir = settings.skills.bundled_dir
        if bundled_dir is None:
            _, bundled_dir = _get_repo_paths()

        # Scan bundled skills
        bundled_path = Path(bundled_dir)
        all_skills = []

        if bundled_path.exists():
            from agent.skills.loader import SkillLoader
            from agent.skills.manifest import parse_skill_manifest

            loader = SkillLoader(_MockConfig())
            bundled_skills = loader.scan_skill_directory(bundled_path)

            disabled_bundled = {normalize_skill_name(s) for s in settings.skills.disabled_bundled}
            enabled_bundled = {normalize_skill_name(s) for s in settings.skills.enabled_bundled}

            for skill_dir in bundled_skills:
                skill_name = skill_dir.name
                canonical = normalize_skill_name(skill_name)

                # Three-state logic: user override > manifest default
                try:
                    manifest = parse_skill_manifest(skill_dir)
                    if canonical in enabled_bundled:
                        enabled = True
                    elif canonical in disabled_bundled:
                        enabled = False
                    else:
                        enabled = manifest.default_enabled
                except Exception:
                    enabled = True  # Fallback

                all_skills.append(
                    {
                        "name": skill_name,
                        "type": "bundled",
                        "enabled": enabled,
                        "source": "core",
                    }
                )

        # Add plugin skills
        for plugin in settings.skills.plugins:
            source_name = plugin.git_url.split("/")[-1].replace(".git", "")
            all_skills.append(
                {
                    "name": plugin.name,
                    "type": "plugin",
                    "enabled": plugin.enabled,
                    "source": source_name,
                    "git_url": plugin.git_url,
                }
            )

        if not all_skills:
            console.print("[yellow]No skills available[/yellow]\n")
            return

        # Display skills with status
        console.print("[bold]Installed Skills:[/bold]\n")
        for i, skill in enumerate(all_skills, 1):
            status_icon = "[green]◉[/green]" if skill["enabled"] else "[dim]○[/dim]"
            type_label = f"[dim]({skill['type']})[/dim]"
            console.print(f"{i}. {status_icon} {skill['name']} {type_label} · {skill['source']}")

        console.print(f"{len(all_skills) + 1}. Back")

        choice = Prompt.ask("\nSelect skill to manage", default=str(len(all_skills) + 1))

        try:
            choice_num = int(choice)
            if choice_num == len(all_skills) + 1:
                console.print()
                return
            if choice_num < 1 or choice_num > len(all_skills):
                console.print(f"[red]Invalid choice: {choice}[/red]\n")
                return

            selected_skill = all_skills[choice_num - 1]
            skill_name = str(selected_skill["name"])
            skill_type = str(selected_skill["type"])
            skill_enabled = bool(selected_skill["enabled"])

            # Show actions for selected skill
            console.print(f"\n[bold]{skill_name}[/bold] ({skill_type})\n")

            actions = []
            if skill_enabled:
                actions.append(("1", "Disable", "disable"))
            else:
                actions.append(("1", "Enable", "enable"))

            if skill_type == "plugin":
                actions.append(("2", "Update", "update"))
                actions.append(("3", "Remove", "remove"))
                actions.append(("4", "Cancel", "cancel"))
            else:
                actions.append(("2", "Cancel", "cancel"))

            for num, label, _ in actions:
                console.print(f"{num}. {label}")

            action_choice = Prompt.ask("\nChoose action", default=actions[-1][0])

            selected_action = next((a for a in actions if a[0] == action_choice), None)

            if not selected_action or selected_action[2] == "cancel":
                console.print()
                return

            # Execute action
            if selected_action[2] == "enable":
                enable_skill(skill_name)
            elif selected_action[2] == "disable":
                disable_skill(skill_name)
            elif selected_action[2] == "update":
                update_skill(skill_name)
            elif selected_action[2] == "remove":
                remove_skill(skill_name, yes=True)

        except ValueError:
            console.print(f"[red]Invalid choice: {choice}[/red]\n")
            return

    except Exception as e:
        console.print(f"[red]Error managing skills: {e}[/red]")
        raise typer.Exit(1)


def show_skills() -> None:
    """Show all bundled and installed plugin skills with their status.

    Shows:
    - Bundled skills (auto-discovered from agent._bundled_skills/)
    - Plugin skills (from config.skills.plugins)
    - Status: ◉ enabled / ○ disabled
    - Token count per skill (context cost)
    - Inline info matching --tools style
    """
    console.print()

    try:
        # Load config
        settings = load_config()

        # Get skills directories
        bundled_dir = settings.skills.bundled_dir
        if bundled_dir is None:
            # Auto-detect
            _, bundled_dir = _get_repo_paths()

        # Scan bundled skills
        bundled_path = Path(bundled_dir)
        bundled_skills = []
        if bundled_path.exists():
            from agent.skills.loader import SkillLoader
            from agent.skills.manifest import parse_skill_manifest
            from agent.utils.tokens import count_tokens

            loader = SkillLoader(_MockConfig())
            bundled_skills = loader.scan_skill_directory(bundled_path)

        # Display bundled skills
        if bundled_skills:
            console.print("[bold]Bundled:[/bold]")
            disabled_bundled = {normalize_skill_name(s) for s in settings.skills.disabled_bundled}
            enabled_bundled = {normalize_skill_name(s) for s in settings.skills.enabled_bundled}

            for skill_dir in bundled_skills:
                from agent.skills.manifest import parse_skill_manifest
                from agent.utils.tokens import count_tokens

                skill_name = skill_dir.name
                canonical = normalize_skill_name(skill_name)

                # Calculate token count and determine enabled state
                try:
                    manifest = parse_skill_manifest(skill_dir)
                    token_count = (
                        count_tokens(manifest.instructions) if manifest.instructions else 0
                    )

                    # Three-state logic: user override > manifest default
                    if canonical in enabled_bundled:
                        enabled = True  # User explicitly enabled
                    elif canonical in disabled_bundled:
                        enabled = False  # User explicitly disabled
                    else:
                        enabled = manifest.default_enabled  # Manifest default

                except Exception:
                    token_count = 0
                    enabled = True  # Fallback to enabled if can't parse

                status_icon = "[green]◉[/green]" if enabled else "[dim]○[/dim]"
                location = str(skill_dir.relative_to(bundled_path.parent))

                console.print(
                    f"  {status_icon} {skill_name} [dim]({location})[/dim] · [dim]{token_count} tokens[/dim]"
                )

                # Display tools if skill has toolsets
                try:
                    tools_info = _get_toolset_tools(manifest, skill_dir)
                    if tools_info:
                        console.print("    [dim]Tools:[/dim]")
                        for tool_name, tool_tokens in tools_info:
                            console.print(
                                f"      [dim]• {tool_name}[/dim] · [dim]{tool_tokens} tokens[/dim]"
                            )
                except Exception:
                    # Silently skip if tool extraction fails
                    pass
        else:
            console.print("[bold]Bundled:[/bold] [dim]None found[/dim]")

        # Display plugin skills
        console.print()  # Blank line before plugins section
        if settings.skills.plugins:
            console.print("[bold]Plugins:[/bold]")

            # Load registry to get commit SHA info
            registry = SkillRegistry()
            from agent.skills.manifest import parse_skill_manifest
            from agent.utils.tokens import count_tokens

            for plugin in settings.skills.plugins:
                status_icon = "[green]◉[/green]" if plugin.enabled else "[dim]○[/dim]"
                git_url_short = plugin.git_url.split("/")[-1].replace(".git", "")

                # Get commit SHA from registry
                canonical_name = normalize_skill_name(plugin.name)
                commit_short = "unknown"
                token_count = 0

                try:
                    entry = registry.get(canonical_name)
                    commit_short = entry.commit_sha[:7] if entry.commit_sha else "unknown"

                    # Calculate token count from installed skill
                    if entry.installed_path and Path(entry.installed_path).exists():
                        manifest = parse_skill_manifest(Path(entry.installed_path))
                        token_count = (
                            count_tokens(manifest.instructions) if manifest.instructions else 0
                        )
                except Exception:
                    # Registry entry not found or error reading manifest
                    pass

                source_info = f"{git_url_short}, {plugin.branch}@{commit_short}"

                console.print(
                    f"  {status_icon} {plugin.name} [dim]({source_info})[/dim] · [dim]{token_count} tokens[/dim]"
                )

                # Display tools if skill has toolsets
                try:
                    if entry.installed_path and Path(entry.installed_path).exists():
                        skill_path = Path(entry.installed_path)
                        manifest = parse_skill_manifest(skill_path)
                        tools_info = _get_toolset_tools(manifest, skill_path)
                        if tools_info:
                            console.print("    [dim]Tools:[/dim]")
                            for tool_name, tool_tokens in tools_info:
                                console.print(
                                    f"      [dim]• {tool_name}[/dim] · [dim]{tool_tokens} tokens[/dim]"
                                )
                except Exception:
                    # Silently skip if tool extraction fails
                    pass
        else:
            console.print("[bold]Plugins:[/bold] [dim]None installed[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing skills: {e}[/red]")
        raise typer.Exit(1)


def install_skill(
    git_url: str | None = None, name: str | None = None, branch: str = "main"
) -> None:
    """Install plugin skill(s) from a git repository.

    Supports both single-skill and monorepo structures:
    - Single-skill: SKILL.md in repository root
    - Monorepo: Multiple subdirectories each with SKILL.md

    Args:
        git_url: Git repository URL (prompts if None)
        name: Optional skill name override for single-skill repos (default: inferred from SKILL.md)
        branch: Git branch to use (default: main)
    """
    # Prompt for git_url if not provided
    if git_url is None:
        console.print()
        git_url = Prompt.ask("[bold]Git repository URL[/bold]")
        if not git_url:
            console.print("[yellow]Cancelled[/yellow]\n")
            return

    console.print(f"\n[bold]Installing skill(s) from:[/bold] {git_url}\n")

    try:
        # Load config
        settings = load_config()

        # Use skill manager to install
        manager = SkillManager()

        console.print("Cloning repository...")
        installed_entries = manager.install(
            git_url=git_url, skill_name=name, branch=branch, trusted=True
        )

        # Display installed skills
        if len(installed_entries) == 1:
            entry = installed_entries[0]
            console.print(f"[green]✓[/green] Installed skill: {entry.name}")
            console.print(f"[dim]Location: {entry.installed_path}[/dim]\n")
        else:
            console.print(f"[green]✓[/green] Installed {len(installed_entries)} skills:\n")
            for entry in installed_entries:
                console.print(f"  [cyan]◉[/cyan] {entry.name}")
                console.print(f"    [dim]{entry.installed_path}[/dim]")
            console.print()

        # Add each skill to config.skills.plugins
        for entry in installed_entries:
            canonical_name = entry.name_canonical

            # Check if already exists in config
            existing = next(
                (
                    p
                    for p in settings.skills.plugins
                    if normalize_skill_name(p.name) == canonical_name
                ),
                None,
            )

            if existing:
                console.print(
                    f"[yellow]Skill '{entry.name}' already in config, updating...[/yellow]"
                )
                existing.git_url = git_url
                existing.branch = branch
                existing.installed_path = str(entry.installed_path)
                existing.enabled = True
            else:
                # Add new plugin
                plugin = PluginSkillSource(
                    name=canonical_name,
                    git_url=git_url,
                    branch=branch,
                    enabled=True,
                    installed_path=str(entry.installed_path),
                )
                settings.skills.plugins.append(plugin)

        # Save config
        save_config(settings)
        console.print("[green]✓[/green] Configuration updated\n")

        if len(installed_entries) == 1:
            console.print(
                f"Skill '{installed_entries[0].name}' is now enabled. Restart agent to load."
            )
        else:
            console.print(
                f"All {len(installed_entries)} skills are now enabled. Restart agent to load."
            )

    except Exception as e:
        console.print(f"[red]Error installing skill: {e}[/red]")
        raise typer.Exit(1)


def update_skill(name: str) -> None:
    """Update an installed plugin skill to the latest version.

    Args:
        name: Skill name to update
    """
    console.print(f"\n[bold]Updating skill:[/bold] {name}\n")

    try:
        # Load config
        settings = load_config()
        canonical_name = normalize_skill_name(name)

        # Find plugin in config
        plugin: PluginSkillSource | None = next(
            (p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name),
            None,
        )

        if not plugin:
            console.print(f"[red]Error: Skill '{name}' not found in plugin list[/red]")
            console.print("[dim]Run 'agent skill show' to see installed skills[/dim]")
            raise typer.Exit(1)

        # Use skill manager to update
        manager = SkillManager()

        console.print(f"Pulling latest changes from {plugin.branch} branch...")
        updated_path = manager.update(canonical_name)

        console.print(f"[green]✓[/green] Updated skill: {name}")
        console.print(f"[dim]Location: {updated_path}[/dim]\n")
        console.print("Restart agent to load updated version.")

    except Exception as e:
        console.print(f"[red]Error updating skill: {e}[/red]")
        raise typer.Exit(1)


def remove_skill(name: str | None = None, keep_files: bool = False, yes: bool = False) -> None:
    """Remove an installed plugin skill.

    Args:
        name: Skill name to remove (shows picker if None)
        keep_files: If True, keep files but remove from config only
        yes: If True, skip confirmation prompt
    """
    try:
        # Load config
        settings = load_config()

        # If no name provided, show picker
        if name is None:
            if not settings.skills.plugins:
                console.print("\n[yellow]No plugin skills installed[/yellow]")
                console.print("[dim]Run 'agent skill install <git-url>' to install skills[/dim]\n")
                return

            console.print("\n[bold]Select skill to remove:[/bold]\n")
            for i, p in enumerate(settings.skills.plugins, 1):
                status = "[green]enabled[/green]" if p.enabled else "[red]disabled[/red]"
                console.print(f"{i}. {p.name} · {status}")

            console.print(f"{len(settings.skills.plugins) + 1}. Cancel")

            choice = Prompt.ask(
                "\nChoose skill number", default=str(len(settings.skills.plugins) + 1)
            )

            try:
                choice_num = int(choice)
                if choice_num == len(settings.skills.plugins) + 1:
                    console.print("Cancelled\n")
                    return
                if choice_num < 1 or choice_num > len(settings.skills.plugins):
                    console.print(f"[red]Invalid choice: {choice}[/red]\n")
                    raise typer.Exit(1)

                name = settings.skills.plugins[choice_num - 1].name
            except ValueError:
                console.print(f"[red]Invalid choice: {choice}[/red]\n")
                raise typer.Exit(1)

        console.print(f"\n[bold]Removing skill:[/bold] {name}\n")

        canonical_name = normalize_skill_name(name)

        # Find plugin in config
        plugin: PluginSkillSource | None = next(
            (p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name),
            None,
        )

        if not plugin:
            console.print(f"[red]Error: Skill '{name}' not found in plugin list[/red]")
            console.print("[dim]Run 'agent skill show' to see installed skills[/dim]")
            raise typer.Exit(1)

        # Confirm removal (unless --yes flag is set)
        if not yes and not Confirm.ask(f"Remove skill '{name}' from configuration?"):
            console.print("Cancelled")
            return

        if not keep_files:
            # Use skill manager to delete files
            manager = SkillManager()
            console.print("Deleting skill files...")
            manager.remove(canonical_name)
            console.print("[green]✓[/green] Deleted skill files")

        # Remove from config
        settings.skills.plugins = [
            p for p in settings.skills.plugins if normalize_skill_name(p.name) != canonical_name
        ]

        # Save config
        save_config(settings)
        console.print(f"[green]✓[/green] Removed '{name}' from configuration\n")

    except Exception as e:
        console.print(f"[red]Error removing skill: {e}[/red]")
        raise typer.Exit(1)


def enable_skill(name: str | None = None) -> None:
    """Enable a skill (bundled or plugin).

    For bundled skills: Removes from disabled_bundled list
    For plugin skills: Sets enabled=true

    Args:
        name: Skill name to enable (shows picker if None)
    """
    try:
        # Load config
        settings = load_config()

        # If no name provided, show picker of disabled skills
        if name is None:
            # Get bundled skills directory to scan for disabled bundled skills
            bundled_dir = settings.skills.bundled_dir
            if bundled_dir is None:
                _, bundled_dir = _get_repo_paths()

            # Scan for bundled skills
            bundled_path = Path(bundled_dir)
            disabled_skills = []

            if bundled_path.exists():
                from agent.skills.loader import SkillLoader

                loader = SkillLoader(_MockConfig())
                bundled_skills = loader.scan_skill_directory(bundled_path)

                disabled_bundled = {
                    normalize_skill_name(s) for s in settings.skills.disabled_bundled
                }

                for skill_dir in bundled_skills:
                    skill_name = skill_dir.name
                    canonical = normalize_skill_name(skill_name)
                    if canonical in disabled_bundled:
                        disabled_skills.append((skill_name, "bundled"))

            # Add disabled plugin skills
            for p in settings.skills.plugins:
                if not p.enabled:
                    disabled_skills.append((p.name, "plugin"))

            if not disabled_skills:
                console.print("\n[yellow]All skills are already enabled[/yellow]")
                console.print("[dim]Run 'agent skill show' to see all skills[/dim]\n")
                return

            console.print("\n[bold]Select skill to enable:[/bold]\n")
            for i, (skill_name, skill_type) in enumerate(disabled_skills, 1):
                console.print(f"{i}. {skill_name} [dim]({skill_type})[/dim]")

            console.print(f"{len(disabled_skills) + 1}. Cancel")

            choice = Prompt.ask("\nChoose skill number", default=str(len(disabled_skills) + 1))

            try:
                choice_num = int(choice)
                if choice_num == len(disabled_skills) + 1:
                    console.print("Cancelled\n")
                    return
                if choice_num < 1 or choice_num > len(disabled_skills):
                    console.print(f"[red]Invalid choice: {choice}[/red]\n")
                    raise typer.Exit(1)

                name = disabled_skills[choice_num - 1][0]
            except ValueError:
                console.print(f"[red]Invalid choice: {choice}[/red]\n")
                raise typer.Exit(1)

        console.print(f"\n[bold]Enabling skill:[/bold] {name}\n")

        canonical_name = normalize_skill_name(name)

        # Check if it's a plugin
        plugin = next(
            (p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name),
            None,
        )

        if plugin:
            # Enable plugin
            if plugin.enabled:
                console.print(f"[yellow]Skill '{name}' is already enabled[/yellow]")
                return

            plugin.enabled = True
            save_config(settings)
            console.print(f"[green]✓[/green] Enabled plugin skill: {name}")
            console.print("Restart agent to load skill.")
        else:
            # Bundled skill - check manifest for default_enabled
            bundled_dir = settings.skills.bundled_dir
            if bundled_dir is None:
                _, bundled_dir = _get_repo_paths()

            # Find and parse manifest to check default_enabled
            bundled_path = Path(bundled_dir)
            from agent.skills.loader import SkillLoader
            from agent.skills.manifest import parse_skill_manifest

            loader = SkillLoader(_MockConfig())
            skill_dirs = loader.scan_skill_directory(bundled_path)
            found_skill_dir = next(
                (d for d in skill_dirs if normalize_skill_name(d.name) == canonical_name), None
            )

            if found_skill_dir is not None:
                manifest = parse_skill_manifest(found_skill_dir)

                # Remove from disabled_bundled (if present)
                settings.skills.disabled_bundled = [
                    s
                    for s in settings.skills.disabled_bundled
                    if normalize_skill_name(s) != canonical_name
                ]

                # If skill defaults to disabled, add to enabled_bundled
                if not manifest.default_enabled:
                    if canonical_name not in [
                        normalize_skill_name(s) for s in settings.skills.enabled_bundled
                    ]:
                        settings.skills.enabled_bundled.append(canonical_name)

                save_config(settings)
                console.print(f"[green]✓[/green] Enabled bundled skill: {name}")
                console.print("Restart agent to load skill.")
            else:
                console.print(f"[red]Bundled skill '{name}' not found[/red]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error enabling skill: {e}[/red]")
        raise typer.Exit(1)


def disable_skill(name: str | None = None) -> None:
    """Disable a skill (bundled or plugin).

    For bundled skills: Adds to disabled_bundled list
    For plugin skills: Sets enabled=false

    Args:
        name: Skill name to disable (shows picker if None)
    """
    try:
        # Load config
        settings = load_config()

        # If no name provided, show picker of enabled skills
        if name is None:
            # Get bundled skills directory
            bundled_dir = settings.skills.bundled_dir
            if bundled_dir is None:
                _, bundled_dir = _get_repo_paths()

            # Scan for enabled bundled skills
            bundled_path = Path(bundled_dir)
            enabled_skills = []

            if bundled_path.exists():
                from agent.skills.loader import SkillLoader

                loader = SkillLoader(_MockConfig())
                bundled_skills = loader.scan_skill_directory(bundled_path)

                disabled_bundled = {
                    normalize_skill_name(s) for s in settings.skills.disabled_bundled
                }

                for skill_dir in bundled_skills:
                    skill_name = skill_dir.name
                    canonical = normalize_skill_name(skill_name)
                    if canonical not in disabled_bundled:
                        enabled_skills.append((skill_name, "bundled"))

            # Add enabled plugin skills
            for p in settings.skills.plugins:
                if p.enabled:
                    enabled_skills.append((p.name, "plugin"))

            if not enabled_skills:
                console.print("\n[yellow]No skills are currently enabled[/yellow]\n")
                return

            console.print("\n[bold]Select skill to disable:[/bold]\n")
            for i, (skill_name, skill_type) in enumerate(enabled_skills, 1):
                console.print(f"{i}. {skill_name} [dim]({skill_type})[/dim]")

            console.print(f"{len(enabled_skills) + 1}. Cancel")

            choice = Prompt.ask("\nChoose skill number", default=str(len(enabled_skills) + 1))

            try:
                choice_num = int(choice)
                if choice_num == len(enabled_skills) + 1:
                    console.print("Cancelled\n")
                    return
                if choice_num < 1 or choice_num > len(enabled_skills):
                    console.print(f"[red]Invalid choice: {choice}[/red]\n")
                    raise typer.Exit(1)

                name = enabled_skills[choice_num - 1][0]
            except ValueError:
                console.print(f"[red]Invalid choice: {choice}[/red]\n")
                raise typer.Exit(1)

        console.print(f"\n[bold]Disabling skill:[/bold] {name}\n")

        canonical_name = normalize_skill_name(name)

        # Check if it's a plugin
        plugin = next(
            (p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name),
            None,
        )

        if plugin:
            # Disable plugin
            if not plugin.enabled:
                console.print(f"[yellow]Skill '{name}' is already disabled[/yellow]")
                return

            plugin.enabled = False
            save_config(settings)
            console.print(f"[green]✓[/green] Disabled plugin skill: {name}")
        else:
            # Bundled skill - check manifest for default_enabled
            bundled_dir = settings.skills.bundled_dir
            if bundled_dir is None:
                _, bundled_dir = _get_repo_paths()

            # Find and parse manifest to check default_enabled
            bundled_path = Path(bundled_dir)
            from agent.skills.loader import SkillLoader
            from agent.skills.manifest import parse_skill_manifest

            loader = SkillLoader(_MockConfig())
            skill_dirs = loader.scan_skill_directory(bundled_path)
            found_skill_dir = next(
                (d for d in skill_dirs if normalize_skill_name(d.name) == canonical_name), None
            )

            if found_skill_dir is not None:
                manifest = parse_skill_manifest(found_skill_dir)

                # Remove from enabled_bundled (if present)
                settings.skills.enabled_bundled = [
                    s
                    for s in settings.skills.enabled_bundled
                    if normalize_skill_name(s) != canonical_name
                ]

                # If skill defaults to enabled, add to disabled_bundled
                if manifest.default_enabled:
                    if canonical_name not in [
                        normalize_skill_name(s) for s in settings.skills.disabled_bundled
                    ]:
                        settings.skills.disabled_bundled.append(canonical_name)

                save_config(settings)
                console.print(f"[green]✓[/green] Disabled bundled skill: {name}")
            else:
                console.print(f"[red]Bundled skill '{name}' not found[/red]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error disabling skill: {e}[/red]")
        raise typer.Exit(1)
