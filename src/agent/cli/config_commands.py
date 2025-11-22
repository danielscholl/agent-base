"""Interactive CLI commands for managing agent configuration."""

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from rich.prompt import Confirm, Prompt
from rich.table import Table

from agent.config import (
    ConfigurationError,
    EditorError,
    edit_and_validate,
    get_config_path,
    get_default_config,
    load_config,
    load_config_with_env,
    save_config,
    validate_config,
)

# Optional import for model checking

# Timeout constants for Docker operations
DOCKER_ENABLE_TIMEOUT = 30  # seconds
MODEL_CHECK_TIMEOUT = 5  # seconds
MODEL_PULL_TIMEOUT = 1200  # seconds (20 minutes)
TOOL_REINSTALL_TIMEOUT = 300  # seconds (5 minutes)

# Use shared utility for Windows console encoding setup
from agent.cli.utils import get_console

console = get_console()


def _check_mem0_local_dependencies() -> tuple[bool, list[str]]:
    """Check if mem0 dependencies (mem0ai, chromadb) are installed.

    Returns:
        Tuple of (all_installed, missing_packages)
    """
    missing = []

    try:
        import mem0  # type: ignore[import-untyped]  # noqa: F401
    except ImportError:
        missing.append("mem0ai")

    try:
        import chromadb  # noqa: F401
    except ImportError:
        missing.append("chromadb")

    return len(missing) == 0, missing


def _install_mem0_dependencies() -> bool:
    """Install mem0 optional dependencies using uv or pip.

    Detects if running as a uv tool and uses appropriate installation method:
    - For uv tools: reinstalls tool with --with flags to add dependencies.
        - Reads uv-receipt.toml to determine original install source.
        - Falls back to "agent-base" package name if receipt cannot be read or is malformed.
        - Reinstallation may take several minutes (up to 5 minutes).
        - Potential failure modes: timeout, permission errors, malformed receipt, missing uv command.
    - For regular installs: uses uv pip install or pip install.

    All exceptions are caught and logged; no exceptions are raised.

    Returns:
        True if installation succeeded, False otherwise.
    """
    console.print("\n[bold]Installing mem0 dependencies...[/bold]")
    console.print("  [dim]This will install: mem0ai, chromadb[/dim]")

    # Check if running as a uv tool by examining sys.executable
    # Support both Unix (.local/share/uv/tools/) and Windows (AppData\Local\uv\tools) paths
    is_uv_tool = "/uv/tools/" in sys.executable or "\\uv\\tools" in sys.executable

    if is_uv_tool:
        # Running as uv tool - need to reinstall with --with flags
        console.print(
            "  [dim]Detected uv tool installation, reinstalling with mem0 extras...[/dim]"
        )

        # Determine the package source from uv-receipt.toml
        package_source = "agent-base"  # Default fallback
        try:
            # Parse uv-receipt.toml to get original install source
            tool_dir = Path(
                sys.executable
            ).parent.parent  # e.g., ~/.local/share/uv/tools/agent-base
            receipt_file = tool_dir / "uv-receipt.toml"

            if receipt_file.exists():
                try:
                    with open(receipt_file, "rb") as f:
                        receipt = tomllib.load(f)
                except FileNotFoundError:
                    # File doesn't exist, use default
                    pass
                except (PermissionError, tomllib.TOMLDecodeError) as e:
                    console.print(f"  [yellow]⚠[/yellow] Could not read install source: {e}")
                except Exception as e:
                    console.print(f"  [dim]Unexpected error reading receipt: {e}[/dim]")
                else:
                    # Extract the requirement spec
                    requirements = receipt.get("tool", {}).get("requirements", [])
                    if requirements and isinstance(requirements, list):
                        req = requirements[0]  # First requirement is the tool itself
                        if isinstance(req, dict):
                            # Build source string from requirement dict
                            name = req.get("name", "agent-base")
                            if "git" in req:
                                git_url = req["git"]

                                # Validate git URL format for security
                                if not git_url.startswith(
                                    ("https://", "http://", "git+https://", "git+http://")
                                ):
                                    console.print(
                                        f"  [yellow]⚠[/yellow] Invalid git URL format: {git_url}"
                                    )
                                else:
                                    # Handle various git reference formats
                                    for param in ["?rev=", "?branch=", "?tag="]:
                                        if param in git_url:
                                            base_url, ref = git_url.split(param, 1)
                                            # Extract just the ref value before any other parameters/fragments
                                            ref = ref.split("&")[0].split("#")[0]

                                            # Validate revision parameter
                                            if not re.match(r"^[a-zA-Z0-9._/-]+$", ref):
                                                console.print(
                                                    f"  [yellow]⚠[/yellow] Invalid revision parameter: {ref}"
                                                )
                                                break

                                            # Ensure git+ prefix
                                            if not base_url.startswith("git+"):
                                                base_url = f"git+{base_url}"
                                            package_source = f"{base_url}@{ref}"
                                            break
                                    else:
                                        # No parameters, just ensure git+ prefix
                                        if not git_url.startswith("git+"):
                                            git_url = f"git+{git_url}"
                                        package_source = git_url
                            else:
                                package_source = name
        except Exception as e:
            # If we can't read receipt, fall back to package name
            console.print(
                f"  [dim]Could not determine original install source ({e}), using package name as fallback[/dim]"
            )

        try:
            result = subprocess.run(
                [
                    "uv",
                    "tool",
                    "install",
                    "--force",
                    "--prerelease=allow",
                    "--with",
                    "mem0ai",
                    "--with",
                    "chromadb",
                    package_source,
                ],
                capture_output=True,
                text=True,
                timeout=TOOL_REINSTALL_TIMEOUT,  # Longer timeout for tool reinstall
            )

            if result.returncode == 0:
                console.print(
                    "[green]✓[/green] Successfully reinstalled agent-base with mem0 dependencies"
                )
                console.print("  [dim]Restart may be required for changes to take effect[/dim]")
                return True
            else:
                console.print(f"[red]✗[/red] Tool reinstall failed: {result.stderr}")
                return False
        except FileNotFoundError:
            console.print("[red]✗[/red] uv command not found")
            return False
        except subprocess.TimeoutExpired:
            console.print("[red]✗[/red] Installation timed out")
            return False
        except Exception as e:
            console.print(f"[red]✗[/red] Installation failed: {e}")
            return False

    # Not a uv tool - use regular pip installation
    # Try uv first (faster and preferred)
    try:
        result = subprocess.run(
            ["uv", "pip", "install", "mem0ai", "chromadb"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Successfully installed mem0 dependencies")
            return True
        else:
            # uv failed, try pip
            console.print("[yellow]⚠[/yellow] uv install failed, trying pip...")
            if result.stderr:
                console.print(f"  [dim]Error: {result.stderr[:100]}[/dim]")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # uv not found or timed out, try pip
        pass

    # Fallback to pip
    try:
        result = subprocess.run(
            ["pip", "install", "mem0ai", "chromadb"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            console.print("[green]✓[/green] Successfully installed mem0 dependencies")
            return True
        else:
            console.print(f"[red]✗[/red] Installation failed: {result.stderr}")
            return False
    except Exception as e:
        console.print(f"[red]✗[/red] Installation failed: {e}")
        return False


def _mask_api_key(api_key: str | None) -> str:
    """Mask API key for display, showing only last 4 characters."""
    if api_key and len(api_key) >= 4:
        return "***" + api_key[-4:]
    return "****"


def config_init() -> None:
    """Initialize configuration with interactive prompts.

    Creates ~/.agent/settings.json with guided setup.
    """
    console.print("\n[bold cyan]Agent Configuration Setup[/bold cyan]")

    config_path = get_config_path()

    # Check if config already exists
    if config_path.exists():
        console.print(f"[yellow]Configuration file already exists at {config_path}[/yellow]")
        if not Confirm.ask("Do you want to overwrite it?"):
            console.print("[dim]Configuration unchanged.[/dim]")
            return

    # Start with defaults
    settings = get_default_config()

    # Ask about provider
    console.print("\n[bold]Select LLM Provider:[/bold]")
    console.print("1. local   - Docker Desktop Model Runner (free, no API key)")
    console.print("2. github  - GitHub Models (gh auth login)")
    console.print("3. openai  - OpenAI API (requires API key)")
    console.print("4. anthropic - Anthropic Claude API (requires API key)")
    console.print("5. gemini  - Google Gemini API (requires API key)")
    console.print("6. azure   - Azure OpenAI (requires endpoint and deployment)")
    console.print("7. foundry - Azure AI Foundry (requires endpoint and deployment)")

    provider_choice = Prompt.ask(
        "\nWhich provider do you want to use?",
        default="1",
    )

    provider_map = {
        "1": "local",
        "2": "github",
        "3": "openai",
        "4": "anthropic",
        "5": "gemini",
        "6": "azure",
        "7": "foundry",
    }

    # Validate choice
    if provider_choice not in provider_map:
        console.print(f"[red]Invalid choice: {provider_choice}[/red]")
        console.print("[dim]Please run 'agent config init' again and select 1-7[/dim]")
        return

    provider = provider_map[provider_choice]

    # Update enabled providers
    settings.providers.enabled = [provider]

    # Get provider-specific configuration using registry
    from agent.config.providers import get_provider_setup

    provider_setup = get_provider_setup(provider)
    provider_config = provider_setup.configure(console)

    # Apply configuration to settings
    provider_obj = getattr(settings.providers, provider)
    for key, value in provider_config.items():
        setattr(provider_obj, key, value)

    # Telemetry is auto-configured via --telemetry flag, no need to ask during init

    # Save configuration
    try:
        save_config(settings, config_path)
        console.print(f"\n[green]✓[/green] Configuration saved to {config_path}")

        # Validate
        errors = validate_config(settings)
        if errors:
            console.print("\n[yellow]Configuration warnings:[/yellow]")
            for error in errors:
                console.print(f"  [yellow]•[/yellow] {error}")
        else:
            console.print("[green]✓[/green] Configuration is valid")

    except ConfigurationError as e:
        console.print(f"\n[red]✗[/red] Failed to save configuration: {e}")


def config_show() -> None:
    """Display current effective configuration."""
    from agent.config import load_config

    config_path = get_config_path()

    # Load effective configuration (file + env overrides, or just env if no file)
    if config_path.exists():
        settings = load_config(config_path)

        # Check for environment overrides and apply them
        from agent.config.manager import deep_merge, merge_with_env
        from agent.config.schema import AgentSettings

        env_overrides = merge_with_env(settings)
        if env_overrides:
            # Apply overrides to show effective configuration
            settings_dict = settings.model_dump()
            merged_dict = deep_merge(settings_dict, env_overrides)
            settings = AgentSettings(**merged_dict)
    else:
        # No config file - load from environment
        import os

        llm_provider_env = os.getenv("LLM_PROVIDER")

        if llm_provider_env:
            # Load config with environment overrides
            from agent.config import load_config_with_env

            settings = load_config_with_env()

            # Check if provider was successfully enabled
            if settings.providers.enabled:
                console.print(
                    f"[yellow]No configuration file at {config_path}[/yellow]\n"
                    f"[dim]Using environment variable: LLM_PROVIDER={llm_provider_env}[/dim]\n"
                )

                console.print("[bold cyan]Active Configuration (from environment)[/bold cyan]\n")
                console.print(f"[bold]Provider:[/bold] {settings.llm_provider}")
                console.print(f"[bold]Model:[/bold] {settings.get_model_display_name()}")
                console.print(f"[bold]Data Directory:[/bold] {settings.agent_data_dir}")
                console.print(f"[bold]Memory:[/bold] {settings.memory.type}")
                console.print(
                    f"[bold]Telemetry:[/bold] {'Enabled' if settings.telemetry.enabled else 'Disabled'}"
                )

                console.print(
                    "\n[dim]💡 Tip: Run 'agent config init' to create a configuration file.[/dim]"
                )
            else:
                # LLM_PROVIDER set but no API key or other required config
                console.print(
                    f"[yellow]No configuration file at {config_path}[/yellow]\n"
                    f"[red]Environment variable LLM_PROVIDER={llm_provider_env} is set, "
                    f"but provider configuration is incomplete.[/red]\n"
                )
                console.print("[dim]💡 Run 'agent config init' to configure your provider.[/dim]")
        else:
            # No config file, no LLM_PROVIDER - auto-run init
            console.print("[yellow]No configuration found.[/yellow]")
            if Confirm.ask("\nWould you like to set up configuration now?", default=True):
                config_init()
            else:
                console.print(
                    "\n[dim]You can configure later with:[/dim]\n"
                    "  • [cyan]agent config init[/cyan]\n"
                    "  • [cyan]agent config enable <provider>[/cyan]\n"
                    "  • [cyan]export LLM_PROVIDER=<provider>[/cyan]\n"
                )
        return

    try:

        # Create main table
        table = Table(title="Agent Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="white")

        # Provider info
        enabled_providers = ", ".join(settings.providers.enabled)
        table.add_row("Enabled Providers", enabled_providers)
        if settings.providers.enabled:
            table.add_row("Default Provider", settings.providers.enabled[0])

        # Provider-specific details
        for provider_name in settings.providers.enabled:
            provider = getattr(settings.providers, provider_name)

            if provider_name == "local":
                table.add_row(f"  {provider_name} URL", provider.base_url)
                table.add_row(f"  {provider_name} Model", provider.model)
            elif provider_name == "openai":
                table.add_row(f"  {provider_name} API Key", _mask_api_key(provider.api_key))
                table.add_row(f"  {provider_name} Model", provider.model)
            elif provider_name == "anthropic":
                table.add_row(f"  {provider_name} API Key", _mask_api_key(provider.api_key))
                table.add_row(f"  {provider_name} Model", provider.model)
            elif provider_name == "azure":
                table.add_row(f"  {provider_name} Endpoint", provider.endpoint or "Not set")
                table.add_row(f"  {provider_name} Deployment", provider.deployment or "Not set")
            elif provider_name == "gemini":
                if provider.use_vertexai:
                    table.add_row(f"  {provider_name} Mode", "Vertex AI")
                    table.add_row(f"  {provider_name} Project", provider.project_id or "Not set")
                else:
                    table.add_row(f"  {provider_name} API Key", _mask_api_key(provider.api_key))

        # Telemetry
        telemetry_status = "Enabled" if settings.telemetry.enabled else "Disabled"
        table.add_row("Telemetry", telemetry_status)

        # Memory
        memory_status = f"{settings.memory.type} (limit: {settings.memory.history_limit})"
        table.add_row("Memory", memory_status)

        # Data directory
        table.add_row("Data Directory", settings.agent.data_dir)

        console.print()
        console.print(table)
        console.print()

        # Show config source
        console.print(f"[dim]Configuration file: {config_path}[/dim]")

        # Validate and show any warnings
        errors = validate_config(settings)
        if errors:
            console.print("\n[yellow]Configuration warnings:[/yellow]")
            for error in errors:
                console.print(f"  [yellow]•[/yellow] {error}")

    except ConfigurationError as e:
        console.print(f"[red]✗[/red] Failed to load configuration: {e}")


def config_edit() -> None:
    """Open configuration file in text editor."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print(
            f"[yellow]No configuration file found at {config_path}[/yellow]\n"
            "[dim]Run 'agent config init' to create one first.[/dim]"
        )
        return

    try:
        console.print(f"Opening {config_path} in editor...")
        is_valid, errors = edit_and_validate(config_path)

        if is_valid:
            console.print("[green]✓[/green] Configuration is valid")
        else:
            console.print("\n[red]✗[/red] Configuration has errors:")
            for error in errors:
                console.print(f"  [red]•[/red] {error}")
            console.print("\n[dim]Please fix these errors and save again.[/dim]")

    except EditorError as e:
        console.print(f"[red]✗[/red] {e}")


def config_provider(provider: str, action: str | None = None) -> None:
    """Manage a specific provider (enable/disable/configure/set-default).

    Args:
        provider: Provider name to manage
        action: Optional action (default, disable, configure) - if None, shows interactive menu
    """
    valid_providers = ["local", "openai", "anthropic", "azure", "foundry", "gemini", "github"]
    if provider not in valid_providers:
        console.print(
            f"[red]✗[/red] Unknown provider: {provider}\n"
            f"[dim]Valid providers: {', '.join(valid_providers)}[/dim]"
        )
        return

    config_path = get_config_path()

    # Load or create config
    if config_path.exists():
        settings = load_config(config_path)
    else:
        console.print("[yellow]No configuration file found. Creating new one...[/yellow]")
        settings = get_default_config()

    # Handle direct action commands
    if action in ["default", "set-default"]:
        # Set as default provider
        if provider not in settings.providers.enabled:
            console.print(f"[yellow]Provider '{provider}' is not enabled.[/yellow]")
            console.print(f"[dim]Run 'agent config provider {provider}' to enable it first.[/dim]")
            return

        settings.providers.enabled.remove(provider)
        settings.providers.enabled.insert(0, provider)
        save_config(settings, config_path)
        console.print(f"[green]✓[/green] '{provider}' set as default provider")
        return

    elif action == "disable":
        # Disable provider
        if provider not in settings.providers.enabled:
            console.print(f"[yellow]Provider '{provider}' is already disabled.[/yellow]")
            return

        settings.providers.enabled.remove(provider)
        provider_obj = getattr(settings.providers, provider)
        provider_obj.enabled = False
        save_config(settings, config_path)
        console.print(f"[green]✓[/green] Provider '{provider}' disabled")
        return

    elif action == "configure":
        # Force reconfiguration
        if provider not in settings.providers.enabled:
            settings.providers.enabled.append(provider)
        # Continue to configuration below

    elif action is not None:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("[dim]Valid actions: default, disable, configure[/dim]")
        return

    # Interactive menu (when no action specified)
    # Check if already enabled
    if provider in settings.providers.enabled:
        # Provider already enabled - show options
        console.print(f"\n[bold]Provider '{provider}' is enabled[/bold]")
        console.print("\nWhat would you like to do?")
        console.print("1. Set as default provider")
        console.print("2. Reconfigure credentials")
        console.print("3. Disable provider")
        console.print("4. Cancel")

        choice = Prompt.ask("Choose an option", default="4")

        # Validate choice
        if choice not in ["1", "2", "3", "4"]:
            console.print(f"[red]Invalid choice: {choice}[/red]")
            return

        if choice == "1":
            # Set as default
            settings.providers.enabled.remove(provider)
            settings.providers.enabled.insert(0, provider)
            save_config(settings, config_path)
            console.print(f"[green]✓[/green] '{provider}' set as default provider")
            return

        elif choice == "2":
            # Reconfigure - continue to configuration below
            pass

        elif choice == "3":
            # Disable
            settings.providers.enabled.remove(provider)
            provider_obj = getattr(settings.providers, provider)
            provider_obj.enabled = False
            save_config(settings, config_path)
            console.print(f"[green]✓[/green] Provider '{provider}' disabled")
            return

        else:
            # Cancel
            console.print("[dim]No changes made.[/dim]")
            return
    else:
        # Not enabled - enable it
        settings.providers.enabled.append(provider)

    # Configure provider
    console.print(f"\n[bold]Configuring {provider} provider:[/bold]")

    # Use provider registry for configuration
    from agent.config.providers import PROVIDER_REGISTRY

    provider_setup = PROVIDER_REGISTRY[provider]
    provider_config = provider_setup.configure(console)

    # Apply configuration to settings
    provider_obj = getattr(settings.providers, provider)
    for key, value in provider_config.items():
        setattr(provider_obj, key, value)

    # Save
    try:
        save_config(settings, config_path)
        console.print(f"\n[green]✓[/green] Provider '{provider}' enabled and configured")

        # Show tip about setting as default if multiple providers
        if len(settings.providers.enabled) > 1 and settings.providers.enabled[0] != provider:
            console.print(
                f"\n[dim]💡 Tip: Run 'agent config provider {provider}' and select 'Set as default'.[/dim]"
            )

        # Validate
        errors = validate_config(settings)
        if errors:
            console.print("\n[yellow]Configuration warnings:[/yellow]")
            for error in errors:
                console.print(f"  [yellow]•[/yellow] {error}")

    except ConfigurationError as e:
        console.print(f"\n[red]✗[/red] Failed to save configuration: {e}")


# Legacy functions for backward compatibility
def config_enable(provider: str) -> None:
    """Enable a provider and configure it.

    Args:
        provider: Provider name (openai, anthropic, azure, gemini, github, local)
    """
    valid_providers = ["local", "openai", "anthropic", "azure", "foundry", "gemini", "github"]
    if provider not in valid_providers:
        console.print(
            f"[red]✗[/red] Unknown provider: {provider}\n"
            f"[dim]Valid providers: {', '.join(valid_providers)}[/dim]"
        )
        return

    config_path = get_config_path()

    # Load or create config
    if config_path.exists():
        settings = load_config(config_path)
    else:
        console.print("[yellow]No configuration file found. Creating new one...[/yellow]")
        settings = get_default_config()

    # Check if already enabled
    if provider in settings.providers.enabled:
        console.print(f"[yellow]Provider '{provider}' is already enabled.[/yellow]")
        if not Confirm.ask("Do you want to reconfigure it?"):
            return
    else:
        # Add to enabled list
        settings.providers.enabled.append(provider)

    # Configure provider
    console.print(f"\n[bold]Configuring {provider} provider:[/bold]")

    # Use provider registry for configuration
    from agent.config.providers import PROVIDER_REGISTRY

    provider_setup = PROVIDER_REGISTRY[provider]
    provider_config = provider_setup.configure(console)

    # Apply configuration to settings
    provider_obj = getattr(settings.providers, provider)
    for key, value in provider_config.items():
        setattr(provider_obj, key, value)

    # Save
    try:
        save_config(settings, config_path)
        console.print(f"\n[green]✓[/green] Provider '{provider}' enabled and configured")

        # Show tip about setting as default if multiple providers
        if len(settings.providers.enabled) > 1 and settings.providers.enabled[0] != provider:
            console.print(
                f"\n[dim]💡 Tip: Run 'agent config set-default {provider}' to make it the default provider.[/dim]"
            )

        # Validate
        errors = validate_config(settings)
        if errors:
            console.print("\n[yellow]Configuration warnings:[/yellow]")
            for error in errors:
                console.print(f"  [yellow]•[/yellow] {error}")

    except ConfigurationError as e:
        console.print(f"\n[red]✗[/red] Failed to save configuration: {e}")


def config_disable(provider: str) -> None:
    """Disable a provider (alias for 'agent config provider <name>')."""
    config_provider(provider)


def config_set_default(provider: str) -> None:
    """Set default provider (alias for 'agent config provider <name>')."""
    config_provider(provider)


def config_memory() -> None:
    """Configure memory backend (in_memory or mem0)."""
    config_path = get_config_path()

    # Load or create config
    if config_path.exists():
        settings = load_config(config_path)
    else:
        console.print("[yellow]No configuration file found. Creating new one...[/yellow]")
        settings = get_default_config()

    # Show current memory config
    console.print("\n[bold]Current Memory Configuration:[/bold]")
    console.print(f"  Type: [cyan]{settings.memory.type}[/cyan]")
    console.print(f"  History Limit: [cyan]{settings.memory.history_limit}[/cyan]")

    if settings.memory.type == "mem0":
        if settings.memory.mem0.api_key:
            console.print("  Mode: [cyan]Cloud (mem0.ai)[/cyan]")
            console.print(f"  Organization: [dim]{settings.memory.mem0.org_id or 'Not set'}[/dim]")
        else:
            console.print("  Mode: [cyan]Local (Chroma)[/cyan]")
            console.print(f"  Storage: [dim]{settings.memory.mem0.storage_path or 'Default'}[/dim]")

    # Ask what to do
    console.print("\n[bold]What would you like to do?[/bold]")
    console.print("1. Configure in_memory (simple, no persistence)")
    console.print("2. Configure mem0 (semantic search with long-term memory)")
    console.print("3. Cancel")

    choice = Prompt.ask("Choose an option", default="3")

    # Validate choice
    if choice not in ["1", "2", "3"]:
        console.print(f"[red]Invalid choice: {choice}[/red]")
        return

    if choice == "1":
        # Configure in_memory
        was_using_mem0 = settings.memory.type == "mem0"

        # Optionally allow changing history limit
        current_limit = settings.memory.history_limit
        if Confirm.ask("Change history limit?", default=False):
            limit = Prompt.ask(
                "Enter history limit (number of messages to keep)", default=str(current_limit)
            )
            try:
                settings.memory.history_limit = int(limit)
            except ValueError:
                console.print(f"[yellow]⚠[/yellow] Invalid number, using default: {current_limit}")

        settings.memory.type = "in_memory"
        settings.memory.enabled = True

        # If switching from mem0, offer to clean up the database
        if was_using_mem0:
            console.print("\n[yellow]⚠[/yellow] You're switching from mem0 to in_memory.")

            # Determine what to clean up
            cleanup_paths = []
            if settings.memory.mem0.storage_path:
                storage_path = Path(settings.memory.mem0.storage_path).expanduser()
                if storage_path.exists():
                    cleanup_paths.append(("Local database", storage_path))

            if cleanup_paths:
                console.print("  [dim]The following mem0 data will be left behind:[/dim]")
                for label, path in cleanup_paths:
                    console.print(f"  [dim]• {label}: {path}[/dim]")

                if Confirm.ask("\nDelete mem0 database?", default=False):
                    for label, path in cleanup_paths:
                        try:
                            if path.is_dir():
                                shutil.rmtree(path)
                                console.print(f"[green]✓[/green] Deleted {label}: {path}")
                            elif path.is_file():
                                path.unlink()
                                console.print(f"[green]✓[/green] Deleted {label}: {path}")
                        except Exception as e:
                            console.print(f"[yellow]⚠[/yellow] Failed to delete {label}: {e}")

                    # Clear mem0 config from settings
                    settings.memory.mem0.storage_path = None
                    settings.memory.mem0.api_key = None
                    settings.memory.mem0.org_id = None
                    settings.memory.mem0.user_id = None
                    settings.memory.mem0.project_id = None
                else:
                    console.print(
                        "[dim]Database preserved. You can manually delete it later if needed.[/dim]"
                    )

        save_config(settings, config_path)
        console.print("[green]✓[/green] Memory backend configured to use in_memory")
        return

    elif choice == "2":
        # Configure mem0
        console.print("\n[bold]Configuring mem0 memory backend:[/bold]")

        # Check provider compatibility first
        try:
            from agent.memory.mem0_utils import SUPPORTED_PROVIDERS, is_provider_compatible

            # Load current provider from settings (including env vars)
            current_config = load_config_with_env()
            is_compatible, reason = is_provider_compatible(current_config)

            if not is_compatible:
                console.print("\n[yellow]⚠[/yellow] Warning: mem0 requires a cloud LLM provider")
                console.print(f"  [dim]Current provider: {current_config.llm_provider}[/dim]")
                console.print(f"  [dim]Issue: {reason}[/dim]")
                console.print(f"  [dim]Supported providers: {', '.join(SUPPORTED_PROVIDERS)}[/dim]")
                console.print(
                    "\n[dim]mem0 will fall back to in_memory until you switch to a compatible provider.[/dim]"
                )

                if not Confirm.ask("\nContinue anyway?", default=False):
                    console.print("[dim]Cancelled. No changes made.[/dim]")
                    return
        except ImportError:
            # mem0 not installed, we'll detect this later during actual usage
            pass

        # Check environment variables first (smart detection)
        env_api_key = os.getenv("MEM0_API_KEY")
        env_org_id = os.getenv("MEM0_ORG_ID")
        env_storage_path = os.getenv("MEM0_STORAGE_PATH")

        # Determine mode: cloud or local
        if env_api_key and env_org_id:
            console.print("[green]✓[/green] Found MEM0_API_KEY and MEM0_ORG_ID in environment")
            console.print("  [dim]Using cloud mode (mem0.ai)[/dim]")
            console.print(f"  [dim]Organization: {env_org_id}[/dim]")
            settings.memory.mem0.api_key = env_api_key
            settings.memory.mem0.org_id = env_org_id
            # Optional user/project IDs
            if os.getenv("MEM0_USER_ID"):
                settings.memory.mem0.user_id = os.getenv("MEM0_USER_ID")
            if os.getenv("MEM0_PROJECT_ID"):
                settings.memory.mem0.project_id = os.getenv("MEM0_PROJECT_ID")
        elif env_storage_path:
            console.print("[green]✓[/green] Found MEM0_STORAGE_PATH in environment")
            console.print("  [dim]Using local mode with custom storage[/dim]")
            settings.memory.mem0.storage_path = env_storage_path
        else:
            # Prompt for configuration (local is the expected/default path)
            use_local = Confirm.ask("\nUse local storage (Chroma)?", default=True)

            if use_local:
                # Local mode - check if dependencies are installed
                deps_installed, missing = _check_mem0_local_dependencies()

                if not deps_installed:
                    console.print(
                        f"\n[yellow]⚠[/yellow] Missing required packages: {', '.join(missing)}"
                    )
                    console.print(
                        "  [dim]mem0 with local storage requires chromadb for vector storage[/dim]"
                    )

                    if Confirm.ask("\nInstall missing dependencies now?", default=True):
                        if _install_mem0_dependencies():
                            console.print("[green]✓[/green] Dependencies installed successfully\n")
                        else:
                            console.print(
                                "\n[yellow]⚠[/yellow] Installation failed. "
                                "You can manually install with:"
                            )
                            console.print("  [cyan]uv pip install mem0ai chromadb[/cyan]")
                            console.print("  [dim]or[/dim]")
                            console.print("  [cyan]pip install mem0ai chromadb[/cyan]\n")

                            if not Confirm.ask(
                                "Continue with configuration anyway?", default=False
                            ):
                                console.print("[dim]Cancelled. No changes made.[/dim]")
                                return
                    else:
                        console.print(
                            "\n[yellow]⚠[/yellow] You'll need to install dependencies before using mem0:"
                        )
                        console.print("  [cyan]uv pip install mem0ai chromadb[/cyan]")
                        console.print("  [dim]or[/dim]")
                        console.print("  [cyan]pip install mem0ai chromadb[/cyan]\n")

                        if not Confirm.ask("Continue with configuration anyway?", default=True):
                            console.print("[dim]Cancelled. No changes made.[/dim]")
                            return

                # Configure storage path
                if Confirm.ask("Set custom storage path?", default=False):
                    storage_path_str = Prompt.ask("Enter storage path", default="~/.agent/mem0")
                    settings.memory.mem0.storage_path = storage_path_str
            else:
                # Cloud mode (mem0.ai)
                api_key = Prompt.ask("Enter your mem0.ai API key", password=True)
                org_id = Prompt.ask("Enter your mem0.ai organization ID")
                settings.memory.mem0.api_key = api_key
                settings.memory.mem0.org_id = org_id

                # Optional identifiers
                if Confirm.ask("Set custom user ID?", default=False):
                    user_id = Prompt.ask("Enter user ID")
                    settings.memory.mem0.user_id = user_id

                if Confirm.ask("Set custom project ID?", default=False):
                    project_id = Prompt.ask("Enter project ID")
                    settings.memory.mem0.project_id = project_id

        settings.memory.type = "mem0"
        settings.memory.enabled = True
        save_config(settings, config_path)
        console.print("[green]✓[/green] Memory backend configured to use mem0")
        return

    else:
        # Cancel (choice == "3")
        console.print("[dim]No changes made.[/dim]")
        return


def config_validate() -> None:
    """Validate configuration file."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print(
            f"[yellow]No configuration file found at {config_path}[/yellow]\n"
            "[dim]Run 'agent config init' to create one.[/dim]"
        )
        return

    try:
        console.print(f"Validating {config_path}...")
        settings = load_config(config_path)

        errors = validate_config(settings)

        if errors:
            console.print("\n[red]✗[/red] Configuration has errors:")
            for error in errors:
                console.print(f"  [red]•[/red] {error}")
            console.print("\n[dim]Run 'agent config edit' to fix these errors.[/dim]")
        else:
            console.print("[green]✓[/green] Configuration is valid")

    except ConfigurationError as e:
        console.print(f"\n[red]✗[/red] Configuration error: {e}")
