"""CLI entry point for Agent."""

import asyncio
import json
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from agent import __version__
from agent.agent import Agent
from agent.cli.commands import (
    handle_clear_command,
    handle_continue_command,
    handle_purge_command,
    handle_shell_command,
    handle_telemetry_command,
    show_help,
)
from agent.cli.constants import Commands, ExitCodes
from agent.cli.display import (
    create_execution_context,
    execute_quiet_mode,
    execute_with_visualization,
)
from agent.cli.session import (
    auto_save_session,
    get_last_session,
    restore_session_context,
    setup_session_logging,
    track_conversation,
)
from agent.config import AgentConfig
from agent.display import DisplayMode, set_execution_context
from agent.persistence import ThreadPersistence
from agent.utils.keybindings import ClearPromptHandler, KeybindingManager

app = typer.Typer(help="Agent - Conversational Assistant")
console = Console()
logger = logging.getLogger(__name__)


def _render_startup_banner(config: AgentConfig) -> None:
    """Render startup banner with branding.

    Args:
        config: Agent configuration
    """
    console.print("[bold cyan]Agent[/bold cyan] - Conversational Assistant")
    # Disable both markup and highlighting to prevent Rich from coloring numbers
    console.print(
        f"Version {__version__} • {config.get_model_display_name()}",
        style="dim",
        markup=False,
        highlight=False,
    )


def _get_status_bar_text() -> str:
    """Get status bar text without printing.

    Returns:
        Status bar text as string (path and branch, right-justified)
    """
    # Get current directory
    cwd = Path.cwd()
    try:
        cwd_display = f"~/{cwd.relative_to(Path.home())}"
    except ValueError:
        cwd_display = str(cwd)

    # Get git branch
    branch_display = ""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=1,
            cwd=cwd,
        )
        if result.returncode == 0 and result.stdout.strip():
            branch = result.stdout.strip()
            branch_display = f" [⎇ {branch}]"
    except (subprocess.SubprocessError, OSError):
        # Silently ignore git errors - branch info is optional
        pass

    # Right-justify the path and branch
    status = f"{cwd_display}{branch_display}"
    padding = max(0, console.width - len(status))

    return f"{' ' * padding}{status}"


@app.command()
def main(
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a single prompt and exit"),
    check: bool = typer.Option(False, "--check", help="Show configuration and connectivity status"),
    config_flag: bool = typer.Option(
        False, "--config", help="Show configuration and connectivity status (alias for --check)"
    ),
    version_flag: bool = typer.Option(False, "--version", help="Show version"),
    telemetry: str = typer.Option(
        None, "--telemetry", help="Manage telemetry dashboard (start|stop|status|url)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", help="Show detailed execution tree (single prompt mode only)"
    ),
    resume: bool = typer.Option(False, "--continue", help="Resume last saved session"),
    provider: str = typer.Option(
        None,
        "--provider",
        help="LLM provider (local, openai, anthropic, azure, foundry, gemini)",
    ),
    model: str = typer.Option(
        None, "--model", help="Model name (overrides AGENT_MODEL environment variable)"
    ),
) -> None:
    """Agent - Conversational Assistant with multi-provider LLM support.

    \b
    Examples:
        agent                                       # Interactive mode
        agent --check                               # Show configuration and connectivity
        agent -p "Say hello to Alice"               # Single query (clean output)
        agent -p "Say hello" --verbose              # Single query with execution details
        agent --provider openai                     # Use OpenAI provider
        agent --provider local --model ai/qwen3     # Use local provider with qwen3
        agent --continue                            # Resume last session
        agent --telemetry start                     # Start observability dashboard
    """
    # Apply CLI overrides to environment variables (temporary for this process)
    if provider:
        os.environ["LLM_PROVIDER"] = provider
    if model:
        os.environ["AGENT_MODEL"] = model

    if version_flag:
        console.print(f"Agent version {__version__}")
        return

    if check or config_flag:
        run_health_check()
        return

    if telemetry:
        # Run telemetry command and exit
        asyncio.run(_run_telemetry_cli(telemetry))
        return

    if prompt:
        # Single-prompt mode: default to quiet (clean output for scripting)
        # Unless --verbose is specified for detailed execution tree
        quiet_mode = not verbose  # Quiet by default unless verbose requested
        asyncio.run(run_single_prompt(prompt, verbose=verbose, quiet=quiet_mode))
    else:
        # Interactive chat mode
        # Handle --continue flag: resume last session
        resume_session = None
        if resume:
            resume_session = get_last_session()
            if not resume_session:
                console.print("[yellow]No previous session found. Starting new session.[/yellow]\n")

        asyncio.run(run_chat_mode(quiet=False, verbose=verbose, resume_session=resume_session))


async def _test_provider_connectivity_async(provider: str, config: AgentConfig) -> tuple[bool, str]:
    """Test connectivity to a specific LLM provider asynchronously.

    Args:
        provider: Provider name (openai, anthropic, azure, foundry, gemini, local)
        config: Agent configuration with credentials

    Returns:
        Tuple of (success, status_message)
    """
    try:
        # Create temporary config for this provider
        test_config = AgentConfig(
            llm_provider=provider,
            openai_api_key=config.openai_api_key,
            openai_model=config.openai_model,
            anthropic_api_key=config.anthropic_api_key,
            anthropic_model=config.anthropic_model,
            azure_openai_endpoint=config.azure_openai_endpoint,
            azure_openai_deployment=config.azure_openai_deployment,
            azure_openai_api_version=config.azure_openai_api_version,
            azure_openai_api_key=config.azure_openai_api_key,
            azure_project_endpoint=config.azure_project_endpoint,
            azure_model_deployment=config.azure_model_deployment,
            gemini_api_key=config.gemini_api_key,
            gemini_model=config.gemini_model,
            gemini_project_id=config.gemini_project_id,
            gemini_location=config.gemini_location,
            gemini_use_vertexai=config.gemini_use_vertexai,
            local_base_url=config.local_base_url,
            local_model=config.local_model,
            agent_data_dir=config.agent_data_dir,
            agent_session_dir=config.agent_session_dir,
        )

        # Validate this provider's configuration
        try:
            test_config.validate()
        except ValueError:
            return False, "Not configured"

        # Test actual connectivity
        agent = None
        try:
            agent = Agent(test_config)
            response = await agent.run("test", thread=None)

            # Cleanup HTTP client before returning
            if hasattr(agent, "chat_client") and hasattr(agent.chat_client, "close"):
                try:
                    await agent.chat_client.close()
                except Exception as e:
                    logger.debug(f"Failed to close client during cleanup: {e}")

            return (True, "Connected") if response else (False, "Connection failed")

        except Exception as e:
            logger.debug(f"Connectivity test for {provider} failed: {e}")
            return False, "Connection failed"
        finally:
            # Final cleanup attempt
            if agent and hasattr(agent, "chat_client") and hasattr(agent.chat_client, "close"):
                try:
                    await agent.chat_client.close()
                except Exception as e:
                    logger.debug(f"Failed to close client in finally block: {e}")

    except Exception as e:
        logger.debug(f"Provider test for {provider} failed: {e}")
        return False, "Error testing provider"


async def _test_all_providers(config: AgentConfig) -> list[tuple[str, str, bool, str]]:
    """Test connectivity to all LLM providers in parallel.

    Args:
        config: Agent configuration

    Returns:
        List of tuples: (provider_id, provider_name, success, status)
    """
    providers = [
        ("local", "Local", config.local_model),
        ("openai", "OpenAI", config.openai_model),
        ("anthropic", "Anthropic", config.anthropic_model),
        ("gemini", "Google Gemini", config.gemini_model),
        ("azure", "Azure OpenAI", config.azure_openai_deployment or "N/A"),
        ("foundry", "Azure AI Foundry", config.azure_model_deployment or "N/A"),
    ]

    results = []
    for provider_id, provider_name, model in providers:
        success, status = await _test_provider_connectivity_async(provider_id, config)
        results.append((provider_id, f"{provider_name} ({model})", success, status))

    return results


def run_health_check() -> None:
    """Run unified health check with configuration and connectivity."""
    console.print()

    try:
        # Configuration validation
        config = AgentConfig.from_env()
        config.validate()

        # System Information
        console.print("[bold]System:[/bold]")
        console.print(f"  [cyan]◉[/cyan] Python [cyan]{platform.python_version()}[/cyan]")
        console.print(f"  [cyan]◉[/cyan] Platform: [cyan]{platform.platform()}[/cyan]")
        console.print(f"  [cyan]◉[/cyan] Data: [cyan]{config.agent_data_dir}[/cyan]")

        # Agent Settings
        console.print("\n[bold]Agent:[/bold]")
        log_level = os.getenv("AGENT_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO"
        console.print(f"  [magenta]◉[/magenta] Log Level: [magenta]{log_level.upper()}[/magenta]")

        # System prompt source
        if config.system_prompt_file:
            prompt_display = str(config.system_prompt_file)
        else:
            user_default = config.agent_data_dir / "system.md" if config.agent_data_dir else None
            prompt_display = (
                "Default" if not user_default or not user_default.exists() else str(user_default)
            )

        console.print(f"  [magenta]◉[/magenta] System Prompt: [magenta]{prompt_display}[/magenta]")

        # Docker
        console.print("\n[bold]Docker:[/bold]")
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip().replace("Docker version ", "").split(",")[0]

                # Get Docker resources
                resources_info = ""
                try:
                    info_result = subprocess.run(
                        ["docker", "info", "--format", "{{json .}}"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if info_result.returncode == 0:
                        docker_info = json.loads(info_result.stdout)
                        ncpu = docker_info.get("NCPU", 0)
                        mem_total = docker_info.get("MemTotal", 0)
                        if ncpu > 0 and mem_total > 0:
                            mem_gb = mem_total / (1024**3)
                            resources_info = f" · {ncpu} cores, {mem_gb:.1f} GiB"
                except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to get Docker resources: {e}")

                console.print(
                    f"  [green]◉[/green] Running [dim]({version})[/dim]{resources_info}",
                    highlight=False,
                )

                # Check for Docker Model Runner models
                try:
                    import requests

                    response = requests.get(
                        "http://localhost:12434/engines/llama.cpp/v1/models", timeout=2
                    )
                    if response.status_code == 200:
                        models_data = response.json()
                        models = models_data.get("data", [])
                        for model in models:
                            model_id = model.get("id", "unknown")
                            console.print(
                                f"  [green]•[/green] [dim]{model_id}[/dim]",
                                highlight=False,
                            )
                except Exception as e:
                    logger.debug(f"Failed to fetch Docker models: {e}")
                    # Silently continue - DMR might not be enabled
            else:
                console.print("  [yellow]◉[/yellow] Not running")
        except FileNotFoundError:
            console.print("  [dim]○[/dim] Not installed")
        except subprocess.TimeoutExpired:
            console.print("  [yellow]◉[/yellow] Timeout (check if running)")

        # LLM Providers - Test all with connectivity
        console.print("\n[bold]LLM Providers:[/bold]")

        active_connected = False
        with console.status("[bold blue]Testing provider connectivity...", spinner="dots"):
            results = asyncio.run(_test_all_providers(config))

        # Display results with configuration details
        for provider_id, provider_display, success, status in results:
            is_active = provider_id == config.llm_provider

            if is_active and success:
                active_connected = True

            # Get credentials display
            if provider_id == "openai" and config.openai_api_key:
                creds = f"****{config.openai_api_key[-6:]}"
            elif provider_id == "anthropic" and config.anthropic_api_key:
                creds = f"****{config.anthropic_api_key[-6:]}"
            elif provider_id == "azure" and config.azure_openai_endpoint:
                creds = (
                    "Azure CLI auth"
                    if not config.azure_openai_api_key
                    else f"****{config.azure_openai_api_key[-6:]}"
                )
            elif provider_id == "foundry" and config.azure_project_endpoint:
                creds = "Azure CLI auth"
            elif provider_id == "gemini":
                if config.gemini_use_vertexai:
                    creds = "Vertex AI auth"
                elif config.gemini_api_key:
                    creds = f"****{config.gemini_api_key[-6:]}"
                else:
                    creds = None
            elif provider_id == "local" and config.local_base_url:
                creds = config.local_base_url
            else:
                creds = None

            # Format output with dimmed models
            active_prefix = "[green]✓[/green] " if is_active else "  "

            # Split provider name and model for styling
            if "(" in provider_display:
                provider_name = provider_display.split("(")[0].strip()
                model = "(" + provider_display.split("(")[1]
            else:
                provider_name = provider_display
                model = ""

            if success and creds:
                console.print(
                    f"{active_prefix}[green]◉[/green] {provider_name} [dim]{model}[/dim] · [dim cyan]{creds}[/dim cyan]",
                    highlight=False,
                )
            elif success:
                console.print(
                    f"{active_prefix}[green]◉[/green] {provider_name} [dim]{model}[/dim]",
                    highlight=False,
                )
            elif status == "Not configured":
                console.print(f"  [dim]○[/dim] {provider_name} - Not configured", highlight=False)
            else:
                console.print(
                    f"{active_prefix}[red]◉[/red] {provider_name} [dim]{model}[/dim] - {status}",
                    highlight=False,
                )

        # Final status
        console.print()
        if not active_connected:
            console.print(
                f"[yellow]⚠ Active provider ({config.llm_provider}) is not connected[/yellow]\n"
            )
            raise typer.Exit(ExitCodes.GENERAL_ERROR)

    except ValueError as e:
        console.print(f"[red]✗[/red] Configuration error: {e}")
        console.print("\n[yellow]See .env.example for configuration template[/yellow]")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


async def _run_telemetry_cli(action: str) -> None:
    """Run telemetry command from CLI flag.

    Args:
        action: Telemetry action (start, stop, status, url)
    """
    await handle_telemetry_command(f"/telemetry {action}", console)


def show_configuration() -> None:
    """Show current configuration and system information."""
    console.print()

    try:
        config = AgentConfig.from_env()

        # System Information
        console.print("[bold]System:[/bold]")
        console.print(f" • Python: [cyan]{platform.python_version()}[/cyan]")
        console.print(f" • Platform: [cyan]{platform.platform()}[/cyan]")

        # Agent Settings
        console.print("\n[bold]Agent Settings:[/bold]")
        console.print(f" • Data Directory: {config.agent_data_dir}")
        if config.agent_session_dir:
            console.print(f" • Session Directory: {config.agent_session_dir}")

        # Get log level (support both AGENT_LOG_LEVEL and LOG_LEVEL)
        log_level = os.getenv("AGENT_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO"
        console.print(f" • Log Level: [magenta]{log_level.upper()}[/magenta]")

        # System prompt source (purple value)
        if config.system_prompt_file:
            console.print(f" • System Prompt: [magenta]{config.system_prompt_file}[/magenta]")
        else:
            user_default = config.agent_data_dir / "system.md" if config.agent_data_dir else None
            if user_default and user_default.exists():
                console.print(f" • System Prompt: [magenta]{user_default}[/magenta]")
            else:
                console.print(" • System Prompt: [magenta]Agent Default[/magenta]")

        # LLM Providers (show all)
        console.print("\n[bold]LLM Providers:[/bold]")

        # Active provider indicator
        console.print(
            f" • Active: [cyan]{config.llm_provider}[/cyan] ({config.get_model_display_name()})"
        )
        console.print()

        # OpenAI
        if config.openai_api_key:
            masked_key = f"****{config.openai_api_key[-6:]}"
            console.print(f" • [cyan]OpenAI[/cyan] ({config.openai_model})")
            console.print(f"   API Key: {masked_key}")
        else:
            console.print(" • [dim]OpenAI - Not configured[/dim]")

        # Anthropic
        if config.anthropic_api_key:
            masked_key = f"****{config.anthropic_api_key[-6:]}"
            console.print(f" • [cyan]Anthropic[/cyan] ({config.anthropic_model})")
            console.print(f"   API Key: {masked_key}")
        else:
            console.print(" • [dim]Anthropic - Not configured[/dim]")

        # Azure OpenAI
        if config.azure_openai_endpoint and config.azure_openai_deployment:
            console.print(f" • [cyan]Azure OpenAI[/cyan] ({config.azure_openai_deployment})")
            console.print(f"   Endpoint: {config.azure_openai_endpoint}")
            if config.azure_openai_api_key:
                masked_key = f"****{config.azure_openai_api_key[-6:]}"
                console.print(f"   API Key: {masked_key}")
            else:
                console.print("   Auth: Azure CLI")
        else:
            console.print(" • [dim]Azure OpenAI - Not configured[/dim]")

        # Azure AI Foundry
        if config.azure_project_endpoint and config.azure_model_deployment:
            console.print(f" • [cyan]Azure AI Foundry[/cyan] ({config.azure_model_deployment})")
            console.print(f"   Endpoint: {config.azure_project_endpoint}")
            console.print("   Auth: Azure CLI")
        else:
            console.print(" • [dim]Azure AI Foundry - Not configured[/dim]")

        console.print()

    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


async def run_single_prompt(prompt: str, verbose: bool = False, quiet: bool = False) -> None:
    """Run single prompt and display response.

    Args:
        prompt: User prompt to execute
        verbose: Show verbose execution tree
        quiet: Minimal output mode
    """
    try:
        config = AgentConfig.from_env()
        config.validate()

        # Setup observability if enabled
        if config.enable_otel:
            from agent_framework.observability import setup_observability

            setup_observability(
                enable_sensitive_data=config.enable_sensitive_data,
                otlp_endpoint=config.otlp_endpoint,
                applicationinsights_connection_string=config.applicationinsights_connection_string,
            )

        # Setup session-specific logging (follows copilot pattern: ~/.agent/logs/session-{timestamp}.log)
        from datetime import datetime

        session_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        setup_session_logging(session_name, config)

        agent = Agent(config=config)

        # Setup execution context for visualization
        ctx = create_execution_context(verbose, quiet, is_interactive=False)
        set_execution_context(ctx)

        # Wrap execution in observability span with custom attributes if enabled
        if config.enable_otel:
            from agent_framework.observability import get_tracer
            from opentelemetry.trace import SpanKind

            tracer = get_tracer()
            with tracer.start_as_current_span(
                "agent-base.cli.single-prompt", kind=SpanKind.CLIENT
            ) as span:
                # Add custom attributes
                span.set_attribute("session.id", session_name)
                span.set_attribute("mode", "single-prompt")
                span.set_attribute("gen_ai.system", config.llm_provider or "unknown")
                if config.llm_provider == "openai" and config.openai_model:
                    span.set_attribute("gen_ai.request.model", config.openai_model)
                elif config.llm_provider == "anthropic" and config.anthropic_model:
                    span.set_attribute("gen_ai.request.model", config.anthropic_model)
                elif config.llm_provider == "azure" and config.azure_openai_deployment:
                    span.set_attribute("gen_ai.request.model", config.azure_openai_deployment)
                elif config.llm_provider == "foundry" and config.azure_model_deployment:
                    span.set_attribute("gen_ai.request.model", config.azure_model_deployment)

                # Execute with or without visualization
                if not quiet:
                    display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
                    try:
                        response = await execute_with_visualization(
                            agent, prompt, None, console, display_mode
                        )
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Interrupted by user[/yellow]\n")
                        raise typer.Exit(ExitCodes.INTERRUPTED)
                else:
                    response = await execute_quiet_mode(agent, prompt, None)
        else:
            # Execute without observability wrapper
            if not quiet:
                display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
                try:
                    response = await execute_with_visualization(
                        agent, prompt, None, console, display_mode
                    )
                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted by user[/yellow]\n")
                    raise typer.Exit(ExitCodes.INTERRUPTED)
            else:
                response = await execute_quiet_mode(agent, prompt, None)

        # Display response after completion summary
        if response:
            console.print(response)

    except ValueError as e:
        console.print(f"\n[red]Configuration error:[/red] {e}")
        console.print("[yellow]Run 'agent --check' to diagnose issues[/yellow]")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(ExitCodes.INTERRUPTED)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


async def run_chat_mode(
    quiet: bool = False,
    verbose: bool = False,
    resume_session: str | None = None,
) -> None:
    """Run interactive chat mode.

    Args:
        quiet: Minimal output mode
        verbose: Verbose output mode with detailed execution tree
        resume_session: Session name to resume (from --continue flag)
    """
    try:
        # Load configuration
        config = AgentConfig.from_env()
        config.validate()

        # Setup observability if enabled
        if config.enable_otel:
            from agent_framework.observability import setup_observability

            setup_observability(
                enable_sensitive_data=config.enable_sensitive_data,
                otlp_endpoint=config.otlp_endpoint,
                applicationinsights_connection_string=config.applicationinsights_connection_string,
            )

        # Generate session name for this session (used for both logging and saving)
        from datetime import datetime

        session_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        # Setup session-specific logging (follows copilot pattern: ~/.agent/logs/session-{name}.log)
        # Logs go to file, not console, to keep output clean
        setup_session_logging(session_name, config)

        # Set session ID for telemetry correlation
        os.environ["SESSION_ID"] = session_name

        # Show startup banner
        if not quiet:
            _render_startup_banner(config)

        # Create agent
        agent = Agent(config=config)

        # Initialize persistence manager with config directories
        persistence = ThreadPersistence(
            storage_dir=config.agent_session_dir, memory_dir=config.memory_dir
        )

        # Create or resume conversation thread
        thread = None
        message_count = 0
        conversation_messages: list[dict] = (
            []
        )  # Track messages for providers without thread support

        if resume_session:
            # When resuming, use the resumed session name for logging
            setup_session_logging(resume_session, config)
            session_name = resume_session
            thread, _, message_count = await restore_session_context(
                agent, persistence, resume_session, console, quiet
            )

        if thread is None:
            thread = agent.get_new_thread()

        # Setup keybinding manager
        keybinding_manager = KeybindingManager()
        keybinding_manager.register_handler(ClearPromptHandler())
        key_bindings = keybinding_manager.create_keybindings()

        # Setup prompt session with history
        data_dir = config.agent_data_dir or Path.home() / ".agent"
        history_file = data_dir / ".agent_history"

        session: PromptSession = PromptSession(
            history=FileHistory(str(history_file)),
            key_bindings=key_bindings,
        )

        # Interactive loop
        first_prompt = True
        while True:
            try:
                # Print status bar before prompt
                if not quiet:
                    status_text = _get_status_bar_text()
                    # Don't add newline before first prompt (already follows banner)
                    separator = "" if first_prompt else "\n"
                    console.print(f"{separator}[dim]{status_text}[/dim]")
                    console.print(f"[dim]{'─' * console.width}[/dim]")
                    first_prompt = False

                # Get user input
                user_input = await session.prompt_async("> ")

                if not user_input or not user_input.strip():
                    continue

                # Handle shell commands (lines starting with !)
                if user_input.strip().startswith("!"):
                    command = user_input.strip()[1:].strip()
                    await handle_shell_command(command, console)
                    continue

                # Handle special commands
                cmd = user_input.strip().lower()

                # Check for exit first (needs special handling to break loop)
                if cmd in Commands.EXIT:
                    # Auto-save session before exit
                    await auto_save_session(
                        persistence,
                        thread,
                        message_count,
                        quiet,
                        conversation_messages,
                        console,
                        session_name,
                        agent,
                    )
                    console.print("\n[dim]Goodbye![/dim]")
                    break

                # Dispatch other commands - cleaner than if/elif chain
                if cmd in Commands.HELP:
                    show_help(console)
                    continue
                elif cmd in Commands.CLEAR:
                    thread, message_count = await handle_clear_command(agent, console)
                    continue
                elif cmd in Commands.CONTINUE:
                    result_thread, result_count = await handle_continue_command(
                        agent, persistence, session, console
                    )
                    if result_thread is not None:
                        thread = result_thread
                        message_count = result_count
                    continue
                elif cmd in Commands.PURGE:
                    await handle_purge_command(persistence, session, console)
                    continue
                elif any(user_input.strip().startswith(c) for c in Commands.TELEMETRY):
                    await handle_telemetry_command(user_input, console)
                    continue

                # Move past the old status bar with a newline
                console.print()

                # Execute agent query
                response = await _execute_agent_query(
                    agent, user_input, thread, quiet, verbose, console
                )

                # Track conversation
                message_count += 1
                track_conversation(conversation_messages, user_input, response)

                # Print response
                console.print(f"{response}")

            except KeyboardInterrupt:
                console.print("\n[yellow]Use Ctrl+D to exit or type 'exit'[/yellow]")
                continue
            except EOFError:
                # Ctrl+D - exit gracefully
                await auto_save_session(
                    persistence,
                    thread,
                    message_count,
                    quiet,
                    conversation_messages,
                    console,
                    session_name,
                    agent,
                )
                console.print("\n[dim]Goodbye![/dim]")
                break

    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print("[yellow]Run 'agent --check' to diagnose issues[/yellow]")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


async def _execute_agent_query(
    agent: Agent,
    user_input: str,
    thread: Any,
    quiet: bool,
    verbose: bool,
    console: Console,
) -> str:
    """Execute agent query with appropriate visualization.

    Args:
        agent: Agent instance
        user_input: User's input
        thread: Conversation thread
        quiet: Quiet mode flag
        verbose: Verbose mode flag
        console: Console for output

    Returns:
        Agent response
    """
    # Setup execution context
    ctx = create_execution_context(verbose, quiet, is_interactive=True)
    set_execution_context(ctx)

    # Wrap in observability span if enabled (adds session context)
    config = agent.config
    if config.enable_otel:
        from agent_framework.observability import get_tracer
        from opentelemetry.trace import SpanKind

        tracer = get_tracer()
        session_id = os.getenv("SESSION_ID", "unknown")

        with tracer.start_as_current_span("agent-base.message", kind=SpanKind.CLIENT) as span:
            # Add session context to each message span
            span.set_attribute("session.id", session_id)
            span.set_attribute("mode", "interactive")
            span.set_attribute("gen_ai.system", config.llm_provider or "unknown")
            if config.llm_provider == "openai" and config.openai_model:
                span.set_attribute("gen_ai.request.model", config.openai_model)
            elif config.llm_provider == "anthropic" and config.anthropic_model:
                span.set_attribute("gen_ai.request.model", config.anthropic_model)
            elif config.llm_provider == "azure" and config.azure_openai_deployment:
                span.set_attribute("gen_ai.request.model", config.azure_openai_deployment)
            elif config.llm_provider == "foundry" and config.azure_model_deployment:
                span.set_attribute("gen_ai.request.model", config.azure_model_deployment)

            # Execute with or without visualization
            if not quiet:
                display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
                try:
                    return await execute_with_visualization(
                        agent, user_input, thread, console, display_mode
                    )
                except KeyboardInterrupt:
                    console.print(
                        "\n[yellow]Operation cancelled[/yellow] - Press Ctrl+C again to exit\n"
                    )
                    raise
            else:
                try:
                    return await execute_quiet_mode(agent, user_input, thread)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Operation cancelled[/yellow]\n")
                    raise
    else:
        # Execute without observability wrapper
        if not quiet:
            display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
            try:
                return await execute_with_visualization(
                    agent, user_input, thread, console, display_mode
                )
            except KeyboardInterrupt:
                console.print(
                    "\n[yellow]Operation cancelled[/yellow] - Press Ctrl+C again to exit\n"
                )
                raise
        else:
            try:
                return await execute_quiet_mode(agent, user_input, thread)
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled[/yellow]\n")
                raise


if __name__ == "__main__":
    app()
