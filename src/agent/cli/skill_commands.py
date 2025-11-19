"""CLI commands for managing agent skills."""

import logging
from pathlib import Path

import typer
from rich.prompt import Confirm, Prompt
from rich.table import Table

from agent.cli.utils import get_console
from agent.config import (
    ConfigurationError,
    get_config_path,
    load_config,
    save_config,
)
from agent.config.schema import PluginSkillSource
from agent.skills.manager import SkillManager
from agent.skills.registry import SkillRegistry
from agent.skills.security import normalize_skill_name

console = get_console()
logger = logging.getLogger(__name__)


def list_skills() -> None:
    """List all bundled and installed plugin skills with their status.

    Shows:
    - Bundled skills (auto-discovered from skills/core/)
    - Plugin skills (from config.skills.plugins)
    - Status: enabled/disabled
    - Source: bundled/plugin (git URL for plugins)
    """
    console.print("\n[bold]Agent Skills[/bold]\n")

    try:
        # Load config
        settings = load_config()

        # Get skills directories
        bundled_dir = settings.skills.bundled_dir
        if bundled_dir is None:
            # Auto-detect
            from agent.agent import Agent
            repo_root = Path(__file__).parent.parent.parent.parent
            bundled_dir = str(repo_root / "skills" / "core")

        # Scan bundled skills
        bundled_path = Path(bundled_dir)
        bundled_skills = []
        if bundled_path.exists():
            from agent.skills.loader import SkillLoader
            class MockConfig:
                def __init__(self):
                    pass
            loader = SkillLoader(MockConfig())
            bundled_skills = loader.scan_skill_directory(bundled_path)

        # Create table for bundled skills
        if bundled_skills:
            table = Table(title="Bundled Skills (Auto-Discovered)", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Location", style="dim")

            disabled_bundled = {normalize_skill_name(s) for s in settings.skills.disabled_bundled}

            for skill_dir in bundled_skills:
                skill_name = skill_dir.name
                canonical = normalize_skill_name(skill_name)
                status = "[red]disabled[/red]" if canonical in disabled_bundled else "[green]enabled[/green]"
                table.add_row(skill_name, status, str(skill_dir.relative_to(bundled_path.parent)))

            console.print(table)
            console.print()
        else:
            console.print("[dim]No bundled skills found[/dim]\n")

        # Create table for plugin skills
        if settings.skills.plugins:
            table = Table(title="Plugin Skills (Installed)", show_header=True)
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Source", style="blue")
            table.add_column("Branch", style="dim")

            for plugin in settings.skills.plugins:
                status = "[green]enabled[/green]" if plugin.enabled else "[red]disabled[/red]"
                git_url_short = plugin.git_url.split("/")[-1].replace(".git", "")
                table.add_row(plugin.name, status, git_url_short, plugin.branch)

            console.print(table)
            console.print()
        else:
            console.print("[dim]No plugin skills installed[/dim]\n")

        # Show summary
        total_bundled = len(bundled_skills)
        total_plugins = len(settings.skills.plugins)
        enabled_bundled = total_bundled - len(settings.skills.disabled_bundled)
        enabled_plugins = sum(1 for p in settings.skills.plugins if p.enabled)

        console.print(f"[bold]Summary:[/bold] {enabled_bundled}/{total_bundled} bundled enabled, "
                     f"{enabled_plugins}/{total_plugins} plugins enabled")
        console.print()

    except Exception as e:
        console.print(f"[red]Error listing skills: {e}[/red]")
        raise typer.Exit(1)


def install_skill(git_url: str, name: str | None = None, branch: str = "main") -> None:
    """Install plugin skill(s) from a git repository.

    Supports both single-skill and monorepo structures:
    - Single-skill: SKILL.md in repository root
    - Monorepo: Multiple subdirectories each with SKILL.md

    Args:
        git_url: Git repository URL (e.g., https://github.com/user/skill.git)
        name: Optional skill name override for single-skill repos (default: inferred from SKILL.md)
        branch: Git branch to use (default: main)
    """
    console.print(f"\n[bold]Installing skill(s) from:[/bold] {git_url}\n")

    try:
        # Load config
        settings = load_config()

        # Use skill manager to install
        manager = SkillManager()

        console.print("Cloning repository...")
        installed_entries = manager.install(
            git_url=git_url,
            skill_name=name,
            branch=branch,
            trusted=True
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
                (p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name),
                None
            )

            if existing:
                console.print(f"[yellow]Skill '{entry.name}' already in config, updating...[/yellow]")
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
                    installed_path=str(entry.installed_path)
                )
                settings.skills.plugins.append(plugin)

        # Save config
        save_config(settings)
        console.print("[green]✓[/green] Configuration updated\n")

        if len(installed_entries) == 1:
            console.print(f"Skill '{installed_entries[0].name}' is now enabled. Restart agent to load.")
        else:
            console.print(f"All {len(installed_entries)} skills are now enabled. Restart agent to load.")

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
        plugin = next((p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name), None)

        if not plugin:
            console.print(f"[red]Error: Skill '{name}' not found in plugin list[/red]")
            console.print(f"[dim]Run 'agent skill list' to see installed skills[/dim]")
            raise typer.Exit(1)

        # Use skill manager to update
        manager = SkillManager()

        console.print(f"Pulling latest changes from {plugin.branch} branch...")
        updated_path = manager.update(canonical_name)

        console.print(f"[green]✓[/green] Updated skill: {name}")
        console.print(f"[dim]Location: {updated_path}[/dim]\n")
        console.print(f"Restart agent to load updated version.")

    except Exception as e:
        console.print(f"[red]Error updating skill: {e}[/red]")
        raise typer.Exit(1)


def remove_skill(name: str, keep_files: bool = False) -> None:
    """Remove an installed plugin skill.

    Args:
        name: Skill name to remove
        keep_files: If True, keep files but remove from config only
    """
    console.print(f"\n[bold]Removing skill:[/bold] {name}\n")

    try:
        # Load config
        settings = load_config()
        canonical_name = normalize_skill_name(name)

        # Find plugin in config
        plugin = next((p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name), None)

        if not plugin:
            console.print(f"[red]Error: Skill '{name}' not found in plugin list[/red]")
            console.print(f"[dim]Run 'agent skill list' to see installed skills[/dim]")
            raise typer.Exit(1)

        # Confirm removal
        if not Confirm.ask(f"Remove skill '{name}' from configuration?"):
            console.print("Cancelled")
            return

        if not keep_files:
            # Use skill manager to delete files
            manager = SkillManager()
            console.print("Deleting skill files...")
            manager.remove(canonical_name)
            console.print(f"[green]✓[/green] Deleted skill files")

        # Remove from config
        settings.skills.plugins = [p for p in settings.skills.plugins if normalize_skill_name(p.name) != canonical_name]

        # Save config
        save_config(settings)
        console.print(f"[green]✓[/green] Removed '{name}' from configuration\n")

    except Exception as e:
        console.print(f"[red]Error removing skill: {e}[/red]")
        raise typer.Exit(1)


def enable_skill(name: str) -> None:
    """Enable a skill (bundled or plugin).

    For bundled skills: Removes from disabled_bundled list
    For plugin skills: Sets enabled=true

    Args:
        name: Skill name to enable
    """
    console.print(f"\n[bold]Enabling skill:[/bold] {name}\n")

    try:
        # Load config
        settings = load_config()
        canonical_name = normalize_skill_name(name)

        # Check if it's a plugin
        plugin = next((p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name), None)

        if plugin:
            # Enable plugin
            if plugin.enabled:
                console.print(f"[yellow]Skill '{name}' is already enabled[/yellow]")
                return

            plugin.enabled = True
            save_config(settings)
            console.print(f"[green]✓[/green] Enabled plugin skill: {name}")
            console.print(f"Restart agent to load skill.")
        else:
            # Must be a bundled skill - remove from disabled list
            if canonical_name in [normalize_skill_name(s) for s in settings.skills.disabled_bundled]:
                settings.skills.disabled_bundled = [
                    s for s in settings.skills.disabled_bundled
                    if normalize_skill_name(s) != canonical_name
                ]
                save_config(settings)
                console.print(f"[green]✓[/green] Enabled bundled skill: {name}")
                console.print(f"Restart agent to load skill.")
            else:
                console.print(f"[yellow]Bundled skill '{name}' is already enabled (not in disabled list)[/yellow]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error enabling skill: {e}[/red]")
        raise typer.Exit(1)


def disable_skill(name: str) -> None:
    """Disable a skill (bundled or plugin).

    For bundled skills: Adds to disabled_bundled list
    For plugin skills: Sets enabled=false

    Args:
        name: Skill name to disable
    """
    console.print(f"\n[bold]Disabling skill:[/bold] {name}\n")

    try:
        # Load config
        settings = load_config()
        canonical_name = normalize_skill_name(name)

        # Check if it's a plugin
        plugin = next((p for p in settings.skills.plugins if normalize_skill_name(p.name) == canonical_name), None)

        if plugin:
            # Disable plugin
            if not plugin.enabled:
                console.print(f"[yellow]Skill '{name}' is already disabled[/yellow]")
                return

            plugin.enabled = False
            save_config(settings)
            console.print(f"[green]✓[/green] Disabled plugin skill: {name}")
        else:
            # Must be a bundled skill - add to disabled list
            if canonical_name not in [normalize_skill_name(s) for s in settings.skills.disabled_bundled]:
                settings.skills.disabled_bundled.append(canonical_name)
                save_config(settings)
                console.print(f"[green]✓[/green] Disabled bundled skill: {name}")
            else:
                console.print(f"[yellow]Bundled skill '{name}' is already disabled[/yellow]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error disabling skill: {e}[/red]")
        raise typer.Exit(1)
