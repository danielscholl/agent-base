"""Interactive CLI commands for managing agent configuration."""

import subprocess

from rich.console import Console
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
    requests = None

console = Console()


def config_init() -> None:
    """Initialize configuration with interactive prompts.

    Creates ~/.agent/settings.json with guided setup.
    """
    console.print("\n[bold cyan]Agent Configuration Setup[/bold cyan]\n")

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
    console.print("1. local  - Docker Desktop Model Runner (free, no API key)")
    console.print("2. openai - OpenAI API (requires API key)")
    console.print("3. anthropic - Anthropic Claude API (requires API key)")
    console.print("4. azure - Azure OpenAI (requires endpoint and deployment)")
    console.print("5. gemini - Google Gemini API (requires API key)")

    provider_choice = Prompt.ask(
        "\nWhich provider do you want to use?",
        choices=["1", "2", "3", "4", "5"],
        default="1",
    )

    provider_map = {
        "1": "local",
        "2": "openai",
        "3": "anthropic",
        "4": "azure",
        "5": "gemini",
    }
    provider = provider_map[provider_choice]

    # Update enabled providers
    settings.providers.enabled = [provider]

    # Get provider-specific configuration
    if provider == "local":
        # Auto-setup Docker Model Runner
        console.print("\n[bold]Setting up Docker Model Runner...[/bold]")

        # Enable model runner
        console.print("Enabling Docker Model Runner...")
        try:
            result = subprocess.run(
                ["docker", "desktop", "enable", "model-runner", "--tcp=12434"],
                capture_output=True,
                text=True,
                timeout=30,
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
                    "http://localhost:12434/engines/llama.cpp/v1/models", timeout=5
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
                                timeout=1200,  # 20 minutes for model download
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

    elif provider == "openai":
        api_key = Prompt.ask("\nEnter your OpenAI API key", password=True)
        settings.providers.openai.api_key = api_key
        settings.providers.openai.enabled = True

    elif provider == "anthropic":
        api_key = Prompt.ask("\nEnter your Anthropic API key", password=True)
        settings.providers.anthropic.api_key = api_key
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
        settings.providers.gemini.enabled = True

    # Ask about telemetry
    if Confirm.ask("\n[bold]Enable OpenTelemetry observability?[/bold]", default=False):
        settings.telemetry.enabled = True
        endpoint = Prompt.ask(
            "OTLP endpoint",
            default="http://localhost:4317",
        )
        settings.telemetry.otlp_endpoint = endpoint

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

        console.print("\n[dim]You can edit this file anytime with: agent config edit[/dim]")

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
                api_key_display = "***" + (provider.api_key[-4:] if provider.api_key else "None")
                table.add_row(f"  {provider_name} API Key", api_key_display)
                table.add_row(f"  {provider_name} Model", provider.model)
            elif provider_name == "anthropic":
                api_key_display = "***" + (provider.api_key[-4:] if provider.api_key else "None")
                table.add_row(f"  {provider_name} API Key", api_key_display)
                table.add_row(f"  {provider_name} Model", provider.model)
            elif provider_name == "azure":
                table.add_row(f"  {provider_name} Endpoint", provider.endpoint or "Not set")
                table.add_row(f"  {provider_name} Deployment", provider.deployment or "Not set")
            elif provider_name == "gemini":
                if provider.use_vertexai:
                    table.add_row(f"  {provider_name} Mode", "Vertex AI")
                    table.add_row(f"  {provider_name} Project", provider.project_id or "Not set")
                else:
                    api_key_display = "***" + (
                        provider.api_key[-4:] if provider.api_key else "None"
                    )
                    table.add_row(f"  {provider_name} API Key", api_key_display)

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


def config_provider(provider: str) -> None:
    """Manage a specific provider (enable/disable/configure/set-default).

    Args:
        provider: Provider name to manage
    """
    valid_providers = ["local", "openai", "anthropic", "azure", "foundry", "gemini"]
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


def _configure_provider(provider: str, provider_obj: any, settings: any) -> None:
    """Configure a specific provider (helper function).

    Args:
        provider: Provider name
        provider_obj: Provider configuration object
        settings: AgentSettings instance
    """
    if provider == "local":
        # Auto-setup Docker Model Runner
        console.print("\n[bold]Setting up Docker Model Runner...[/bold]")

        # Enable model runner
        console.print("Enabling Docker Model Runner...")
        try:
            result = subprocess.run(
                ["docker", "desktop", "enable", "model-runner", "--tcp=12434"],
                capture_output=True,
                text=True,
                timeout=30,
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
                    "http://localhost:12434/engines/llama.cpp/v1/models", timeout=5
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
                                timeout=1200,  # 20 minutes for model download
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

    elif provider == "openai":
        api_key = Prompt.ask("Enter your OpenAI API key", password=True)
        provider_obj.api_key = api_key

    elif provider == "anthropic":
        api_key = Prompt.ask("Enter your Anthropic API key", password=True)
        provider_obj.api_key = api_key

    elif provider == "azure":
        endpoint = Prompt.ask("Enter your Azure OpenAI endpoint")
        deployment = Prompt.ask("Enter your deployment name")
        api_key = Prompt.ask("Enter your API key (or press Enter to use Azure CLI)", password=True)
        provider_obj.endpoint = endpoint
        provider_obj.deployment = deployment
        if api_key:
            provider_obj.api_key = api_key

    elif provider == "foundry":
        endpoint = Prompt.ask("Enter your Azure AI Foundry project endpoint")
        deployment = Prompt.ask("Enter your model deployment name")
        provider_obj.project_endpoint = endpoint
        provider_obj.model_deployment = deployment

    elif provider == "gemini":
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


# Legacy functions for backward compatibility
def config_enable(provider: str) -> None:
    """Enable a provider and configure it.

    Args:
        provider: Provider name (openai, anthropic, azure, gemini, local)
    """
    valid_providers = ["local", "openai", "anthropic", "azure", "foundry", "gemini"]
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

    if provider == "openai":
        api_key = Prompt.ask("Enter your OpenAI API key", password=True)
        provider_obj.api_key = api_key

    elif provider == "anthropic":
        api_key = Prompt.ask("Enter your Anthropic API key", password=True)
        provider_obj.api_key = api_key

    elif provider == "azure":
        endpoint = Prompt.ask("Enter your Azure OpenAI endpoint")
        deployment = Prompt.ask("Enter your deployment name")
        api_key = Prompt.ask("Enter your API key (or press Enter to use Azure CLI)", password=True)
        provider_obj.endpoint = endpoint
        provider_obj.deployment = deployment
        if api_key:
            provider_obj.api_key = api_key

    elif provider == "foundry":
        endpoint = Prompt.ask("Enter your Azure AI Foundry project endpoint")
        deployment = Prompt.ask("Enter your model deployment name")
        provider_obj.project_endpoint = endpoint
        provider_obj.model_deployment = deployment

    elif provider == "gemini":
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
