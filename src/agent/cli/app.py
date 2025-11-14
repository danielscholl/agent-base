"""CLI entry point for Agent."""

import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
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
    handle_memory_command,
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
from agent.cli.utils import get_console
from agent.config import AgentConfig
from agent.display import DisplayMode, set_execution_context
from agent.persistence import ThreadPersistence
from agent.utils.keybindings import ClearPromptHandler, KeybindingManager

app = typer.Typer(help="Agent - Conversational Assistant")

# Use shared utility for Windows console encoding setup
console = get_console()

logger = logging.getLogger(__name__)

# Cache git branch lookup to avoid spawning a subprocess every prompt
_BRANCH_CACHE_CWD: Path | None = None
_BRANCH_CACHE_VALUE: str = ""


def _hide_connection_string_if_otel_disabled(config: AgentConfig) -> str | None:
    """Conditionally hide Azure Application Insights connection string.

    The agent_framework auto-enables OpenTelemetry when it sees
    APPLICATIONINSIGHTS_CONNECTION_STRING in the environment, which causes
    1-3s exit lag from daemon threads flushing metrics.

    This helper hides the connection string ONLY when telemetry is disabled,
    allowing users who explicitly enable OTEL to still use it.

    Args:
        config: Loaded AgentConfig (must be loaded first to check enable_otel)

    Returns:
        The connection string if it was hidden, None otherwise

    Example:
        >>> config = AgentConfig.from_combined()
        >>> saved = _hide_connection_string_if_otel_disabled(config)
        >>> # ... create agent ...
        >>> if saved:
        ...     os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = saved
    """
    should_enable_otel = config.enable_otel and config.enable_otel_explicit

    if not should_enable_otel and config.applicationinsights_connection_string:
        saved = os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)
        if saved:
            logger.debug(
                "[PERF] Hiding Azure connection string to prevent OpenTelemetry "
                "auto-init (set ENABLE_OTEL=true to enable telemetry)"
            )
        return saved

    return None


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

    # Get git branch (cached per CWD to reduce startup/prompt lag)
    branch_display = ""
    global _BRANCH_CACHE_CWD, _BRANCH_CACHE_VALUE
    try:
        if _BRANCH_CACHE_CWD != cwd:
            # Compute branch once for this working directory
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=0.3,
                cwd=cwd,
            )
            if result.returncode == 0 and result.stdout.strip():
                _BRANCH_CACHE_VALUE = result.stdout.strip()
            else:
                _BRANCH_CACHE_VALUE = ""
            _BRANCH_CACHE_CWD = cwd

        if _BRANCH_CACHE_VALUE:
            branch_display = f" [⎇ {_BRANCH_CACHE_VALUE}]"
    except (subprocess.SubprocessError, OSError):
        # Silently ignore git errors - branch info is optional
        _BRANCH_CACHE_VALUE = ""

    # Right-justify the path and branch
    status = f"{cwd_display}{branch_display}"
    padding = max(0, console.width - len(status))

    return f"{' ' * padding}{status}"


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a single prompt and exit"),
    check: bool = typer.Option(False, "--check", help="Show configuration and connectivity status"),
    version_flag: bool = typer.Option(False, "--version", help="Show version"),
    telemetry: str = typer.Option(
        None, "--telemetry", help="Manage telemetry dashboard (start|stop|status|url)"
    ),
    memory: str = typer.Option(None, "--memory", help="Show memory configuration (help|info)"),
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
        agent config init                           # Configure agent interactively
    """
    # If a subcommand was invoked (e.g., 'agent config'), skip main logic
    if ctx.invoked_subcommand is not None:
        return

    # Apply CLI overrides to environment variables (temporary for this process)
    if provider:
        os.environ["LLM_PROVIDER"] = provider
    if model:
        os.environ["AGENT_MODEL"] = model

    if version_flag:
        console.print(f"Agent version {__version__}")
        return

    if check:
        run_health_check()
        return

    if telemetry:
        # Run telemetry command and exit
        asyncio.run(_run_telemetry_cli(telemetry))
        return

    if memory:
        # Run memory command and exit
        asyncio.run(_run_memory_cli(memory))
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
        provider: Provider name (local, github, openai, anthropic, gemini, azure, foundry)
        config: Agent configuration with credentials

    Returns:
        Tuple of (success, status_message)
    """
    # Temporarily suppress ERROR and WARNING logs during connectivity test
    # This includes Azure identity, agent-framework auth, and middleware loggers
    loggers_to_suppress = [
        logging.getLogger("agent.middleware"),
        logging.getLogger("azure.identity"),
        logging.getLogger("azure.identity._internal.decorators"),
        logging.getLogger("azure.identity._credentials.chained"),
        logging.getLogger("agent_framework.azure._entra_id_authentication"),
        logging.getLogger("agent_framework._clients"),  # Suppress conversation_id warnings
    ]
    original_levels = [(logger, logger.level) for logger in loggers_to_suppress]

    for logger in loggers_to_suppress:
        logger.setLevel(logging.CRITICAL)

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
            github_token=config.github_token,
            github_model=config.github_model,
            github_endpoint=config.github_endpoint,
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

        # Test actual connectivity with lightweight check
        # Instead of full agent.run() which makes expensive LLM call (~2.5s),
        # just create the client and verify it initializes successfully (~0.1-0.5s)
        agent = None
        try:
            agent = Agent(test_config)

            # Note: This validates configuration and client instantiation,
            # but does NOT guarantee endpoint reachability or credential validity.
            # Actual API calls may still fail. This is a lightweight config check,
            # not a true connectivity test.

            # Cleanup HTTP client before returning
            if hasattr(agent, "chat_client") and hasattr(agent.chat_client, "close"):
                try:
                    await agent.chat_client.close()
                except Exception as e:
                    logger.debug(f"Failed to close client during cleanup: {e}")

            return True, "Connected"

        except Exception as e:
            logger.debug(f"Connectivity test for {provider} failed: {e}")

            # Provide more specific error messages for Azure authentication issues
            error_str = str(e).lower()
            if provider in ["azure", "foundry"]:
                if "az login" in error_str or "azurecredential" in error_str:
                    return False, "Auth failed (run 'az login')"
                elif "failed to retrieve azure token" in error_str:
                    return False, "Auth failed (run 'az login')"

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
    finally:
        # Restore original logging levels
        for logger, level in original_levels:
            logger.setLevel(level)


async def _test_all_providers(config: AgentConfig) -> list[tuple[str, str, bool, str]]:
    """Test connectivity to enabled LLM providers in parallel.

    Only tests providers that are:
    1. In the enabled_providers list, OR
    2. The currently active provider (config.llm_provider)

    This optimization significantly reduces check time by skipping disabled providers
    and running tests concurrently.

    Args:
        config: Agent configuration

    Returns:
        List of tuples: (provider_id, provider_name, success, status)
    """
    # All available providers with their display names and models
    all_providers = [
        ("local", "Local", config.local_model),
        ("openai", "OpenAI", config.openai_model),
        ("anthropic", "Anthropic", config.anthropic_model),
        ("gemini", "Google Gemini", config.gemini_model),
        ("github", "GitHub Models", config.github_model),
        ("azure", "Azure OpenAI", config.azure_openai_deployment or "N/A"),
        ("foundry", "Azure AI Foundry", config.azure_model_deployment or "N/A"),
    ]

    # Determine which providers to test
    # Test enabled providers + always test the active provider
    providers_to_test = set(config.enabled_providers or [])
    if config.llm_provider:
        providers_to_test.add(config.llm_provider)

    # Filter to only providers we need to test
    providers = [
        (provider_id, provider_name, model)
        for provider_id, provider_name, model in all_providers
        if provider_id in providers_to_test
    ]

    # Test all providers in parallel using asyncio.gather
    tasks = [
        _test_provider_connectivity_async(provider_id, config) for provider_id, _, _ in providers
    ]
    test_results = await asyncio.gather(*tasks)

    # Combine provider info with test results
    results = [
        (provider_id, f"{provider_name} ({model})", success, status)
        for (provider_id, provider_name, model), (success, status) in zip(
            providers, test_results, strict=True
        )
    ]

    return results


def run_health_check() -> None:
    """Run unified health check with configuration and connectivity.

    Note: Uses Unicode characters (◉, ○, ✓, ⚠) for visual display.
    These render correctly in modern terminals (PowerShell, cmd, bash interactive)
    but may cause UnicodeEncodeError when output is piped through non-interactive
    shells with cp1252 encoding. This is acceptable since the primary use case
    is interactive terminal display, not scripted/piped output.
    """
    console.print()

    try:
        # Configuration validation
        config = AgentConfig.from_combined()
        config.validate()

        # System Information
        # Note: ◉ (U+25C9) renders correctly in PowerShell/cmd/modern terminals
        console.print("[bold]System:[/bold]")
        console.print(
            f"  [cyan]◉[/cyan] Python [cyan]{platform.python_version()}[/cyan]",
            highlight=False,
        )
        console.print(
            f"  [cyan]◉[/cyan] Platform: [cyan]{platform.platform()}[/cyan]",
            highlight=False,
        )
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

        # Memory Backend
        console.print("\n[bold]Memory:[/bold]")
        memory_type = config.memory_type

        if memory_type == "mem0":
            # Check if mem0 is actually available
            mem0_available = False
            unavailable_reason = ""

            try:
                from agent.memory.mem0_utils import get_storage_path, is_provider_compatible

                is_compatible, reason = is_provider_compatible(config)
                mem0_available = is_compatible
                unavailable_reason = reason
            except ImportError:
                unavailable_reason = "mem0ai package not installed"

            if not mem0_available:
                # Show actual backend (in_memory) with note about mem0
                console.print("  [cyan]◉[/cyan] Backend: [cyan]in_memory[/cyan]")
                console.print(
                    f"  [yellow]⚠[/yellow]  mem0 not available: [yellow]{unavailable_reason}[/yellow]"
                )
            else:
                # Show mem0 as backend with configuration
                console.print("  [cyan]◉[/cyan] Backend: [cyan]mem0[/cyan]")

                from agent.memory.mem0_utils import get_storage_path

                is_cloud = bool(config.mem0_api_key and config.mem0_org_id)

                if is_cloud:
                    console.print(
                        "  [green]◉[/green] Mode: [green]Cloud (mem0.ai)[/green]",
                        highlight=False,
                    )
                    console.print(f"  [cyan]◉[/cyan] Organization: [dim]{config.mem0_org_id}[/dim]")
                else:
                    storage_path = get_storage_path(config)
                    console.print(
                        "  [green]◉[/green] Mode: [green]Local (Chroma)[/green]",
                        highlight=False,
                    )
                    console.print(f"  [cyan]◉[/cyan] Storage: [dim]{storage_path}[/dim]")

                # Show namespace
                namespace = config.mem0_user_id or "default-user"
                if config.mem0_project_id:
                    namespace = f"{namespace}:{config.mem0_project_id}"
                console.print(f"  [cyan]◉[/cyan] Namespace: [dim]{namespace}[/dim]")
        else:
            # in_memory backend
            console.print(f"  [cyan]◉[/cyan] Backend: [cyan]{memory_type}[/cyan]")

        # Docker
        console.print("\n[bold]Docker:[/bold]")
        try:
            # First check if Docker CLI is installed
            version_result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if version_result.returncode == 0:
                version = version_result.stdout.strip().replace("Docker version ", "").split(",")[0]

                # Check if Docker daemon is actually running by attempting docker info
                daemon_running = False
                resources_info = ""
                try:
                    info_result = subprocess.run(
                        ["docker", "info", "--format", "{{json .}}"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if info_result.returncode == 0:
                        daemon_running = True
                        docker_info = json.loads(info_result.stdout)
                        ncpu = docker_info.get("NCPU", 0)
                        mem_total = docker_info.get("MemTotal", 0)
                        if ncpu > 0 and mem_total > 0:
                            mem_gb = mem_total / (1024**3)
                            resources_info = f" · {ncpu} cores, {mem_gb:.1f} GiB"
                    else:
                        # docker info failed - daemon is not running
                        logger.debug(f"Docker daemon not running: {info_result.stderr}")
                except subprocess.TimeoutExpired as e:
                    logger.debug(f"Docker info timed out: {e}")
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Failed to parse Docker info: {e}")

                if daemon_running:
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
                    console.print(
                        f"  [yellow]◉[/yellow] Not running [dim]({version} installed, daemon not started)[/dim]"
                    )
            else:
                console.print("  [dim]○[/dim] Not installed")
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
            # Skip disabled providers entirely if using new config system
            # But always show the active provider even if not in enabled list
            if (
                config.enabled_providers
                and provider_id not in config.enabled_providers
                and provider_id != config.llm_provider
            ):
                continue
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
                    "az auth"
                    if not config.azure_openai_api_key
                    else f"****{config.azure_openai_api_key[-6:]}"
                )
            elif provider_id == "foundry" and config.azure_project_endpoint:
                creds = "az auth"
            elif provider_id == "gemini":
                if config.gemini_use_vertexai:
                    creds = "Vertex AI auth"
                elif config.gemini_api_key:
                    creds = f"****{config.gemini_api_key[-6:]}"
                else:
                    creds = None
            elif provider_id == "github":
                if config.github_token:
                    creds = f"****{config.github_token[-4:]}"
                else:
                    creds = "gh auth"
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

    except typer.Exit:
        # Re-raise typer.Exit without wrapping in another exception
        raise
    except ValueError as e:
        error_msg = str(e)
        console.print(f"[red]✗[/red] Configuration error: {error_msg}\n")

        # If it's a "No configuration found" error, offer to run init
        if "No configuration found" in error_msg:
            # Only offer interactive setup if running in a TTY
            if sys.stdin.isatty():
                from rich.prompt import Confirm

                if Confirm.ask("Would you like to set up configuration now?", default=True):
                    from agent.cli.config_commands import config_init

                    config_init()
                    # Config init already shows checkmarks, no need for extra message
                    return
                else:
                    console.print("\n[dim]Run 'agent config init' when ready to configure.[/dim]")
            else:
                console.print(
                    "\n[yellow]Configuration not found.[/yellow] "
                    "Run 'agent config init' for interactive setup, "
                    "or set LLM_PROVIDER environment variable for non-interactive configuration."
                )
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


async def _run_memory_cli(action: str) -> None:
    """Run memory command from CLI flag.

    Args:
        action: Memory action (start, stop, status, url)
    """
    await handle_memory_command(f"/memory {action}", console)


def show_configuration() -> None:
    """Show current configuration and system information."""
    console.print()

    try:
        config = AgentConfig.from_combined()

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
        import time

        perf_start = time.perf_counter()

        config = AgentConfig.from_combined()
        config.validate()
        logger.info(f"[PERF] Config loaded: {(time.perf_counter() - perf_start)*1000:.1f}ms")

        # Hide Azure connection string if telemetry disabled (prevents 1-3s exit lag)
        saved_connection_string = _hide_connection_string_if_otel_disabled(config)

        # Skip observability auto-detection in single-prompt mode for speed
        should_enable_otel = config.enable_otel and config.enable_otel_explicit

        if should_enable_otel:
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
        logger.info(f"[PERF] Logging setup: {(time.perf_counter() - perf_start)*1000:.1f}ms")

        agent_start = time.perf_counter()
        agent = Agent(config=config)
        logger.info(f"[PERF] Agent created: {(time.perf_counter() - agent_start)*1000:.1f}ms")

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

        logger.info(
            f"[PERF] Total single-prompt execution: {(time.perf_counter() - perf_start)*1000:.1f}ms"
        )

    except ValueError as e:
        error_msg = str(e)
        console.print(f"\n[red]Configuration error:[/red] {error_msg}\n")

        # If it's a "No configuration found" error, offer to run init
        if "No configuration found" in error_msg:
            # Only offer interactive setup if running in a TTY
            if sys.stdin.isatty():
                from rich.prompt import Confirm

                if Confirm.ask("Would you like to set up configuration now?", default=True):
                    from agent.cli.config_commands import config_init

                    config_init()
                    # Config init already shows checkmarks, no need for extra message
                    return
                else:
                    console.print("\n[dim]Run 'agent config init' when ready to configure.[/dim]")
            else:
                console.print(
                    "\n[yellow]Configuration not found.[/yellow] "
                    "Run 'agent config init' for interactive setup, "
                    "or set LLM_PROVIDER environment variable for non-interactive configuration."
                )

        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(ExitCodes.INTERRUPTED)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    finally:
        # Restore connection string if we hid it
        if "saved_connection_string" in locals() and saved_connection_string:
            os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = saved_connection_string


def _ensure_history_size_limit(history_file: Path, max_lines: int = 10000) -> None:
    """Rotate history file if too large to prevent slow startup.

    Note: Reads entire file into memory for simplicity. For 10K lines (~500KB)
    this is negligible (~20ms). Could be optimized with tail/seek for huge files
    but current approach is simple and sufficient.

    Args:
        history_file: Path to history file
        max_lines: Maximum lines to keep (default: 10000)
    """
    if not history_file.exists():
        return

    try:
        with open(history_file) as f:
            lines = f.readlines()

        if len(lines) > max_lines:
            # Keep last max_lines entries
            logger.info(f"Rotating history file: {len(lines)} lines -> {max_lines} lines")
            with open(history_file, "w") as f:
                f.writelines(lines[-max_lines:])
    except Exception as e:
        logger.warning(f"Failed to rotate history file: {e}")


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
        import time

        perf_start = time.perf_counter()

        # Load configuration
        config = AgentConfig.from_combined()
        config.validate()
        logger.info(
            f"[PERF] Interactive mode - config loaded: {(time.perf_counter() - perf_start)*1000:.1f}ms"
        )

        # Hide Azure connection string if telemetry disabled (prevents 1-3s exit lag)
        saved_connection_string = _hide_connection_string_if_otel_disabled(config)

        # Disable observability auto-detection in interactive mode by default
        should_enable_otel = config.enable_otel and config.enable_otel_explicit

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

        # Initialize persistence manager with config directories
        persistence = ThreadPersistence(
            storage_dir=config.agent_session_dir, memory_dir=config.memory_dir
        )
        logger.info(
            f"[PERF] Persistence initialized: {(time.perf_counter() - perf_start)*1000:.1f}ms"
        )

        # Lazy agent initialization: only create when needed
        # This makes prompt appear instantly without waiting for SDK imports
        agent = None
        thread = None
        message_count = 0
        conversation_messages: list[dict] = (
            []
        )  # Track messages for providers without thread support

        # If resuming session, we need agent immediately to restore context
        if resume_session:
            agent_start = time.perf_counter()
            agent = Agent(config=config)
            logger.info(
                f"[PERF] Agent created for resume: {(time.perf_counter() - agent_start)*1000:.1f}ms"
            )

            # When resuming, use the resumed session name for logging
            setup_session_logging(resume_session, config)
            session_name = resume_session
            thread, _, message_count = await restore_session_context(
                agent, persistence, resume_session, console, quiet
            )

        # Setup keybinding manager
        keybinding_manager = KeybindingManager()
        keybinding_manager.register_handler(ClearPromptHandler())
        key_bindings = keybinding_manager.create_keybindings()

        # Setup prompt session with history (rotate if needed)
        data_dir = config.agent_data_dir or Path.home() / ".agent"
        history_file = data_dir / ".agent_history"

        hist_start = time.perf_counter()
        _ensure_history_size_limit(history_file, max_lines=10000)
        session: PromptSession = PromptSession(
            history=FileHistory(str(history_file)),
            key_bindings=key_bindings,
        )
        logger.info(f"[PERF] History loaded: {(time.perf_counter() - hist_start)*1000:.1f}ms")
        logger.info(f"[PERF] Ready for input: {(time.perf_counter() - perf_start)*1000:.1f}ms")

        # Interactive loop
        status_bar_enabled = os.getenv("AGENT_STATUS_BAR", "1").lower() not in ("0", "false", "off")
        first_prompt = True
        while True:
            try:
                # Print status bar before prompt
                if not quiet and status_bar_enabled:
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
                    exit_start = time.perf_counter()
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

                    # Cleanup to eliminate exit lag
                    client_close_start = time.perf_counter()
                    try:
                        if agent and hasattr(agent, "chat_client"):
                            # Close chat client (closes httpx connections)
                            if hasattr(agent.chat_client, "close"):
                                logger.debug("[PERF] Closing chat client...")
                                await agent.chat_client.close()
                                logger.debug(
                                    f"[PERF] Chat client closed: {(time.perf_counter() - client_close_start)*1000:.1f}ms"
                                )

                            # Force httpx client cleanup if available (best-effort)
                            # Note: Accesses _client private attribute - may not exist for all providers
                            if hasattr(agent.chat_client, "_client"):
                                try:
                                    if hasattr(agent.chat_client._client, "close"):
                                        agent.chat_client._client.close()
                                        logger.debug("[PERF] httpx client closed")
                                except Exception as e:
                                    logger.debug(f"[PERF] httpx cleanup: {e}")
                    except Exception as e:
                        logger.warning(f"[PERF] Chat client close failed: {e}")

                    logger.info(
                        f"[PERF] Exit cleanup completed: {(time.perf_counter() - exit_start)*1000:.1f}ms"
                    )
                    break

                # Dispatch other commands - cleaner than if/elif chain
                if cmd in Commands.HELP:
                    show_help(console)
                    continue
                elif cmd in Commands.CLEAR:
                    # Create agent if needed (lazy init)
                    if agent is None:
                        init_start = time.perf_counter()
                        agent = Agent(config=config)
                        logger.info(
                            f"[PERF] Agent lazy init for /clear: {(time.perf_counter() - init_start)*1000:.1f}ms"
                        )
                    thread, message_count = await handle_clear_command(agent, console)
                    continue
                elif cmd in Commands.CONTINUE:
                    # Create agent if needed (lazy init)
                    if agent is None:
                        init_start = time.perf_counter()
                        agent = Agent(config=config)
                        logger.info(
                            f"[PERF] Agent lazy init for /continue: {(time.perf_counter() - init_start)*1000:.1f}ms"
                        )
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
                elif user_input.strip().startswith("/memory"):
                    await handle_memory_command(user_input, console)
                    continue

                # Move past the old status bar with a newline
                console.print()

                # Lazy agent initialization: create on first actual query
                if agent is None:
                    init_start = time.perf_counter()
                    if not quiet:
                        with console.status("[bold blue]Initializing...", spinner="dots"):
                            agent = Agent(config=config)
                    else:
                        agent = Agent(config=config)
                    logger.info(
                        f"[PERF] Agent lazy init: {(time.perf_counter() - init_start)*1000:.1f}ms"
                    )
                    logger.info(
                        f"[PERF] Total time to first query: {(time.perf_counter() - perf_start)*1000:.1f}ms"
                    )

                # Initialize thread if needed
                if thread is None:
                    thread = agent.get_new_thread()

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
                exit_start = time.perf_counter()
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

                # Cleanup to eliminate exit lag
                client_close_start = time.perf_counter()
                try:
                    if agent and hasattr(agent, "chat_client"):
                        # Close chat client (closes httpx connections)
                        if hasattr(agent.chat_client, "close"):
                            logger.debug("[PERF] Closing chat client...")
                            await agent.chat_client.close()
                            logger.debug(
                                f"[PERF] Chat client closed: {(time.perf_counter() - client_close_start)*1000:.1f}ms"
                            )

                        # Force httpx client cleanup if available (best-effort)
                        # Note: Accesses _client private attribute - may not exist for all providers
                        if hasattr(agent.chat_client, "_client"):
                            try:
                                if hasattr(agent.chat_client._client, "close"):
                                    agent.chat_client._client.close()
                                    logger.debug("[PERF] httpx client closed")
                            except Exception as e:
                                logger.debug(f"[PERF] httpx cleanup: {e}")
                except Exception as e:
                    logger.warning(f"[PERF] Chat client close failed: {e}")

                logger.info(
                    f"[PERF] Exit cleanup completed: {(time.perf_counter() - exit_start)*1000:.1f}ms"
                )
                break

    except ValueError as e:
        error_msg = str(e)
        console.print(f"[red]Configuration error:[/red] {error_msg}\n")

        # If it's a "No configuration found" error, offer to run init
        if "No configuration found" in error_msg:
            # Only offer interactive setup if running in a TTY
            if sys.stdin.isatty():
                from rich.prompt import Confirm

                if Confirm.ask("Would you like to set up configuration now?", default=True):
                    from agent.cli.config_commands import config_init

                    config_init()
                    # Config init already shows checkmarks, no need for extra message
                    return
                else:
                    console.print("\n[dim]Run 'agent config init' when ready to configure.[/dim]")
            else:
                console.print(
                    "\n[yellow]Configuration not found.[/yellow] "
                    "Run 'agent config init' for interactive setup, "
                    "or set LLM_PROVIDER environment variable for non-interactive configuration."
                )

        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    finally:
        # Restore connection string if we hid it
        if "saved_connection_string" in locals() and saved_connection_string:
            os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = saved_connection_string
        # Log when function actually exits
        logger.info(
            f"[PERF] run_chat_mode() exiting after {(time.perf_counter() - perf_start)*1000:.1f}ms total"
        )


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


# Config command group - add with rich_help_panel to keep main command at root level
# Note: Typer doesn't support default commands with subcommands elegantly
# The pattern used here: main() is the primary command, config is a command group
config_app = typer.Typer(help="Manage agent configuration")
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    """Config command callback - shows help if no subcommand given."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@config_app.command("init")
def config_init_command() -> None:
    """Initialize configuration with interactive prompts."""
    from agent.cli.config_commands import config_init

    config_init()


@config_app.command("show")
def config_show_command() -> None:
    """Display current configuration."""
    from agent.cli.config_commands import config_show

    config_show()


@config_app.command("edit")
def config_edit_command() -> None:
    """Open configuration file in text editor."""
    from agent.cli.config_commands import config_edit

    config_edit()


@config_app.command("provider")
def config_provider_command(
    ctx: typer.Context,
    provider: str = typer.Argument(
        None, help="Provider to manage (local, github, openai, anthropic, gemini, azure, foundry)"
    ),
    action: str = typer.Argument(None, help="Action to perform (default, disable, configure)"),
) -> None:
    """Manage a provider (enable/disable/configure/default).

    Examples:
        agent config provider github           # Interactive menu
        agent config provider github default   # Set as default
        agent config provider github disable   # Disable provider
        agent config provider github configure # Reconfigure credentials
    """
    if provider is None:
        console.print(ctx.get_help())
        return

    from agent.cli.config_commands import config_provider

    config_provider(provider, action)


@config_app.command("validate")
def config_validate_command() -> None:
    """Validate configuration file."""
    from agent.cli.config_commands import config_validate

    config_validate()


@config_app.command("memory")
def config_memory_command() -> None:
    """Configure memory backend (in_memory or mem0)."""
    from agent.cli.config_commands import config_memory

    config_memory()


if __name__ == "__main__":
    app()
