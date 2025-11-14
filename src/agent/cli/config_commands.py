"""Interactive CLI commands for managing agent configuration."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from rich.prompt import Confirm, Prompt
from rich.table import Table

from agent.config import (
    ConfigurationError,
    EditorError,
    edit_and_validate,
    get_config_path,
    get_default_config,
    load_config,
    save_config,
    validate_config,
)

# Optional import for model checking
try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

# Timeout constants for Docker operations
DOCKER_ENABLE_TIMEOUT = 30  # seconds
MODEL_CHECK_TIMEOUT = 5  # seconds
MODEL_PULL_TIMEOUT = 1200  # seconds (20 minutes)

# Use shared utility for Windows console encoding setup
from agent.cli.utils import get_console

console = get_console()


def _setup_github_org(provider_obj: Any) -> None:
    """Helper to configure GitHub organization for enterprise rate limits.

    Args:
        provider_obj: GitHub provider config object with 'org' attribute
    """
    console.print("\n[bold]GitHub Organization (Optional)[/bold]")
    console.print("  [dim]For enterprise users with organization access:[/dim]")
    console.print("  [dim]• Personal: 20-150 requests/day (depending on model)[/dim]")
    console.print("  [dim]• Enterprise: 15,000 requests/hour[/dim]")

    setup_org = Confirm.ask(
        "\nDo you have a GitHub organization with models enabled?", default=False
    )
    if setup_org:
        # Try to auto-detect first
        try:
            from agent.providers.github.auth import get_github_org

            detected_org = get_github_org()
            if detected_org:
                console.print(
                    f"\n[green]✓[/green] Detected organization: [cyan]{detected_org}[/cyan]"
                )
                use_detected = Confirm.ask(
                    "Use this organization?",
                    default=True,
                )
                if use_detected:
                    provider_obj.org = detected_org
                    console.print("  [dim]Using enterprise endpoint for higher rate limits[/dim]")
                else:
                    manual_org = Prompt.ask("Enter organization name")
                    provider_obj.org = manual_org
            else:
                manual_org = Prompt.ask("Enter your GitHub organization name")
                provider_obj.org = manual_org
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not auto-detect organization: {e}")
            manual_org = Prompt.ask("Enter your GitHub organization name")
            provider_obj.org = manual_org


def _mask_api_key(api_key: str | None) -> str:
    """Mask API key for display, showing only last 4 characters."""
    if api_key and len(api_key) >= 4:
        return "***" + api_key[-4:]
    return "****"


def _setup_local_provider() -> None:
    """Set up Docker Model Runner and pull phi4 model (shared helper function)."""
    # Auto-setup Docker Model Runner
    console.print("\n[bold]Setting up Docker Model Runner...[/bold]")

    # Enable model runner
    console.print("Enabling Docker Model Runner...")
    try:
        result = subprocess.run(
            ["docker", "desktop", "enable", "model-runner", "--tcp=12434"],
            capture_output=True,
            text=True,
            timeout=DOCKER_ENABLE_TIMEOUT,
        )
        if result.returncode == 0:
            console.print("[green]✓[/green] Model Runner enabled")
        else:
            console.print(f"[yellow]⚠[/yellow] Model Runner enable: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        console.print("[yellow]⚠[/yellow] Timeout enabling model runner")
    except FileNotFoundError:
        console.print("[red]✗[/red] Docker not found. Please install Docker Desktop.")

    # Check for existing models
    console.print("Checking for models...")
    if requests is None:
        console.print("[yellow]⚠[/yellow] requests library not available, skipping model check")
    else:
        try:
            response = requests.get(
                "http://localhost:12434/engines/llama.cpp/v1/models", timeout=MODEL_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                models = response.json().get("data", [])
                if models:
                    console.print(f"[green]✓[/green] Found {len(models)} model(s)")
                else:
                    # No models - pull phi4
                    console.print(
                        "\n[bold yellow]No models found. Pulling phi4 model (9GB)...[/bold yellow]"
                    )
                    console.print(
                        "[dim]This may take 10-20 minutes depending on your connection.[/dim]\n"
                    )

                    # Run with live output so user sees progress
                    try:
                        result = subprocess.run(
                            ["docker", "model", "pull", "phi4"],
                            timeout=MODEL_PULL_TIMEOUT,
                            text=True,
                        )
                        if result.returncode == 0:
                            console.print("\n[green]✓[/green] phi4 model pulled successfully")
                        else:
                            console.print(
                                f"\n[yellow]⚠[/yellow] Model pull exited with code {result.returncode}"
                            )
                            console.print(
                                "[dim]You can manually pull with: docker model pull phi4[/dim]"
                            )
                    except subprocess.TimeoutExpired:
                        console.print("\n[red]✗[/red] Model pull timed out after 20 minutes")
                        console.print(
                            "[dim]You can manually pull with: docker model pull phi4[/dim]"
                        )
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Model pull cancelled.[/yellow]")
                        console.print(
                            "[dim]You can manually pull later with: docker model pull phi4[/dim]"
                        )
            else:
                console.print(
                    "[yellow]⚠[/yellow] Model Runner not responding. It may need a moment to start."
                )
        except requests.RequestException:
            console.print("[yellow]⚠[/yellow] Model Runner not responding yet")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not check models: {e}")


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

    # Get provider-specific configuration
    if provider == "local":
        _setup_local_provider()
        # Ask for model (with recommended default)
        model = Prompt.ask("\nModel", default="ai/phi4", show_default=True)
        settings.providers.local.model = model
        settings.providers.local.enabled = True

    elif provider == "github":
        # GitHub uses gh CLI for auth - just verify it's available
        gh_available = shutil.which("gh") is not None
        env_token = os.getenv("GITHUB_TOKEN")

        if env_token:
            console.print("\n[green]✓[/green] Found GITHUB_TOKEN in environment")
            settings.providers.github.token = env_token
        elif gh_available:
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                if result.stdout.strip():
                    console.print("\n[green]✓[/green] GitHub authentication ready (gh CLI)")
                else:
                    console.print("\n[yellow]⚠[/yellow] gh CLI not authenticated")
                    console.print("  [dim]Run 'gh auth login' to authenticate[/dim]")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                console.print("\n[yellow]⚠[/yellow] Could not verify gh authentication")
                console.print("  [dim]Run 'gh auth login' to authenticate[/dim]")
        else:
            console.print("\n[yellow]⚠[/yellow] gh CLI not found")
            console.print("  [dim]Install: brew install gh && gh auth login[/dim]")
            console.print("  [dim]Or set GITHUB_TOKEN environment variable[/dim]")

        # Ask for model (with recommended default)
        model = Prompt.ask("\nModel", default="gpt-4o-mini", show_default=True)
        settings.providers.github.model = model
        settings.providers.github.endpoint = "https://models.github.ai"
        settings.providers.github.enabled = True

        # Ask about organization for enterprise rate limits
        _setup_github_org(settings.providers.github)

    elif provider == "openai":
        api_key = Prompt.ask("\nEnter your OpenAI API key", password=True)
        # Ask for model (with recommended default)
        model = Prompt.ask("\nModel", default="gpt-5-mini", show_default=True)
        settings.providers.openai.api_key = api_key
        settings.providers.openai.model = model
        settings.providers.openai.enabled = True

    elif provider == "anthropic":
        api_key = Prompt.ask("\nEnter your Anthropic API key", password=True)
        # Ask for model (with recommended default)
        model = Prompt.ask("\nModel", default="claude-haiku-4-5-20251001", show_default=True)
        settings.providers.anthropic.api_key = api_key
        settings.providers.anthropic.model = model
        settings.providers.anthropic.enabled = True

    elif provider == "azure":
        endpoint = Prompt.ask("\nEnter your Azure OpenAI endpoint")
        deployment = Prompt.ask("Enter your deployment name")
        api_key = Prompt.ask("Enter your API key (or press Enter to use Azure CLI)", password=True)
        settings.providers.azure.endpoint = endpoint
        settings.providers.azure.deployment = deployment
        if api_key:
            settings.providers.azure.api_key = api_key
        settings.providers.azure.enabled = True

    elif provider == "gemini":
        use_vertex = Confirm.ask("\nUse Vertex AI instead of Gemini API?", default=False)
        if use_vertex:
            project_id = Prompt.ask("Enter your GCP project ID")
            location = Prompt.ask("Enter your GCP location", default="us-central1")
            settings.providers.gemini.use_vertexai = True
            settings.providers.gemini.project_id = project_id
            settings.providers.gemini.location = location
        else:
            api_key = Prompt.ask("Enter your Gemini API key", password=True)
            settings.providers.gemini.api_key = api_key
        # Ask for model (with recommended default)
        model = Prompt.ask("\nModel", default="gemini-2.0-flash-exp", show_default=True)
        settings.providers.gemini.model = model
        settings.providers.gemini.enabled = True

    elif provider == "foundry":
        endpoint = Prompt.ask("\nEnter your Azure AI Foundry project endpoint")
        deployment = Prompt.ask("Enter your model deployment name")
        settings.providers.foundry.project_endpoint = endpoint
        settings.providers.foundry.model_deployment = deployment
        settings.providers.foundry.enabled = True

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
    from agent.config import AgentConfig

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
        # No config file - check if LLM_PROVIDER is set
        import os

        llm_provider_env = os.getenv("LLM_PROVIDER")

        if llm_provider_env:
            # Show config from environment
            agent_config = AgentConfig.from_env()
            console.print(
                f"[yellow]No configuration file at {config_path}[/yellow]\n"
                f"[dim]Using environment variable: LLM_PROVIDER={llm_provider_env}[/dim]\n"
            )

            console.print("[bold cyan]Active Configuration (from environment)[/bold cyan]\n")
            console.print(f"[bold]Provider:[/bold] {agent_config.llm_provider}")
            console.print(f"[bold]Model:[/bold] {agent_config.get_model_display_name()}")
            console.print(f"[bold]Data Directory:[/bold] {agent_config.agent_data_dir}")
            console.print(f"[bold]Memory:[/bold] {agent_config.memory_type}")
            console.print(
                f"[bold]Telemetry:[/bold] {'Enabled' if agent_config.enable_otel else 'Disabled'}"
            )

            console.print(
                "\n[dim]💡 Tip: Run 'agent config init' to create a configuration file.[/dim]"
            )
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

        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"], default="4")

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

    provider_obj = getattr(settings.providers, provider)
    provider_obj.enabled = True

    _configure_provider(provider, provider_obj, settings)

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


def _configure_provider(provider: str, provider_obj: Any, settings: Any) -> None:
    """Configure a specific provider (helper function).

    Args:
        provider: Provider name
        provider_obj: Provider configuration object
        settings: AgentSettings instance
    """
    if provider == "local":
        _setup_local_provider()

    elif provider == "openai":
        # Check environment first (smart enable)
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            console.print("[green]✓[/green] Found OPENAI_API_KEY in environment")
            console.print("  [dim]Using: [from environment][/dim]")
            provider_obj.api_key = env_key
        else:
            api_key = Prompt.ask("Enter your OpenAI API key", password=True)
            provider_obj.api_key = api_key

    elif provider == "anthropic":
        # Check environment first (smart enable)
        env_key = os.getenv("ANTHROPIC_API_KEY")
        if env_key:
            console.print("[green]✓[/green] Found ANTHROPIC_API_KEY in environment")
            console.print("  [dim]Using: [from environment][/dim]")
            provider_obj.api_key = env_key
        else:
            api_key = Prompt.ask("Enter your Anthropic API key", password=True)
            provider_obj.api_key = api_key

    elif provider == "azure":
        # Check environment first (smart enable)
        env_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        env_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        env_key = os.getenv("AZURE_OPENAI_API_KEY")

        if env_endpoint and env_deployment:
            console.print("[green]✓[/green] Found Azure OpenAI config in environment")
            console.print(f"  [dim]Endpoint: {env_endpoint}[/dim]")
            console.print(f"  [dim]Deployment: {env_deployment}[/dim]")
            provider_obj.endpoint = env_endpoint
            provider_obj.deployment = env_deployment
            if env_key:
                console.print("  [dim]API Key: [from environment][/dim]")
                provider_obj.api_key = env_key
        else:
            endpoint = Prompt.ask("Enter your Azure OpenAI endpoint")
            deployment = Prompt.ask("Enter your deployment name")
            api_key = Prompt.ask(
                "Enter your API key (or press Enter to use Azure CLI)", password=True
            )
            provider_obj.endpoint = endpoint
            provider_obj.deployment = deployment
            if api_key:
                provider_obj.api_key = api_key

    elif provider == "foundry":
        # Check environment first (smart enable)
        env_endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
        env_deployment = os.getenv("AZURE_MODEL_DEPLOYMENT")

        if env_endpoint and env_deployment:
            console.print("[green]✓[/green] Found Azure AI Foundry config in environment")
            console.print(f"  [dim]Endpoint: {env_endpoint}[/dim]")
            console.print(f"  [dim]Deployment: {env_deployment}[/dim]")
            provider_obj.project_endpoint = env_endpoint
            provider_obj.model_deployment = env_deployment
        else:
            endpoint = Prompt.ask("Enter your Azure AI Foundry project endpoint")
            deployment = Prompt.ask("Enter your model deployment name")
            provider_obj.project_endpoint = endpoint
            provider_obj.model_deployment = deployment

    elif provider == "gemini":
        # Check environment first (smart enable)
        env_use_vertex = os.getenv("GEMINI_USE_VERTEXAI", "false").lower() == "true"
        env_key = os.getenv("GEMINI_API_KEY")
        env_project = os.getenv("GEMINI_PROJECT_ID")
        env_location = os.getenv("GEMINI_LOCATION")

        if env_use_vertex and env_project:
            console.print("[green]✓[/green] Found Gemini Vertex AI config in environment")
            console.print(f"  [dim]Project: {env_project}[/dim]")
            console.print(f"  [dim]Location: {env_location or 'us-central1'}[/dim]")
            provider_obj.use_vertexai = True
            provider_obj.project_id = env_project
            provider_obj.location = env_location or "us-central1"
        elif env_key:
            console.print("[green]✓[/green] Found GEMINI_API_KEY in environment")
            console.print("  [dim]Using: [from environment][/dim]")
            provider_obj.api_key = env_key
        else:
            use_vertex = Confirm.ask("Use Vertex AI instead of Gemini API?", default=False)
            if use_vertex:
                project_id = Prompt.ask("Enter your GCP project ID")
                location = Prompt.ask("Enter your GCP location", default="us-central1")
                provider_obj.use_vertexai = True
                provider_obj.project_id = project_id
                provider_obj.location = location
            else:
                api_key = Prompt.ask("Enter your Gemini API key", password=True)
                provider_obj.api_key = api_key

    elif provider == "github":
        # GitHub uses gh CLI for authentication - no manual token entry needed
        # Just verify gh is available and show status
        env_token = os.getenv("GITHUB_TOKEN")
        gh_available = shutil.which("gh") is not None

        if env_token:
            console.print("[green]✓[/green] Found GITHUB_TOKEN in environment")
            console.print("  [dim]Using: [from environment][/dim]")
            provider_obj.token = env_token
        elif gh_available:
            # Verify gh is authenticated
            try:
                result = subprocess.run(
                    ["gh", "auth", "token"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                if result.stdout.strip():
                    console.print("[green]✓[/green] GitHub authentication ready")
                    console.print("  [dim]Using: gh CLI[/dim]")
                    # Token will be fetched at runtime
                    provider_obj.token = None
                else:
                    console.print("[yellow]⚠[/yellow] gh CLI not authenticated")
                    console.print("  [dim]Run 'gh auth login' to authenticate[/dim]")
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                console.print("[yellow]⚠[/yellow] gh CLI authentication failed")
                console.print("  [dim]Run 'gh auth login' to authenticate[/dim]")
        else:
            console.print("[yellow]⚠[/yellow] No GitHub authentication found")
            console.print("[dim]Install gh CLI: brew install gh && gh auth login[/dim]")
            console.print("[dim]Or set GITHUB_TOKEN: export GITHUB_TOKEN=ghp_...[/dim]")

        # Model selection
        model = Prompt.ask(
            "Model",
            default="gpt-4o-mini",
            show_default=True,
        )
        provider_obj.model = model
        provider_obj.endpoint = "https://models.github.ai"

        # Ask about organization for enterprise rate limits
        _setup_github_org(provider_obj)


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

    provider_obj = getattr(settings.providers, provider)
    provider_obj.enabled = True

    _configure_provider(provider, provider_obj, settings)

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

    choice = Prompt.ask("Choose an option", choices=["1", "2", "3"], default="3")

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
            from agent.config import AgentConfig
            from agent.memory.mem0_utils import SUPPORTED_PROVIDERS, is_provider_compatible

            # Load current provider from settings
            current_config = AgentConfig.from_combined()
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
                # Local mode
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
