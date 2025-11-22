"""Health check and system diagnostics for Agent CLI.

This module provides health check functionality including:
- System information display (Python version, platform, data directory)
- LLM provider connectivity testing (async parallel testing)
- Docker status and Model Runner detection
- Memory backend configuration display
- Configuration validation

Extracted from cli/app.py to improve maintainability and testability.
"""

import asyncio
import json
import logging
import os
import platform
import subprocess
import sys

import typer
from rich.console import Console
from rich.prompt import Confirm

from agent.agent import Agent
from agent.cli.constants import ExitCodes
from agent.cli.utils import get_console
from agent.config import load_config_with_env
from agent.config.schema import AgentSettings

logger = logging.getLogger(__name__)


async def _test_provider_connectivity_async(
    provider: str, config: AgentSettings
) -> tuple[bool, str]:
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
        # Use model_copy() to create a deep copy and modify enabled providers
        test_config = config.model_copy(deep=True)
        test_config.providers.enabled = [provider]

        # Validate this provider's configuration
        try:
            errors = test_config.validate_enabled_providers()
            if errors:
                return False, "Not configured"
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


async def _test_all_providers(config: AgentSettings) -> list[tuple[str, str, bool, str]]:
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


def show_tool_configuration(console: Console | None = None) -> None:
    """Display tool configuration with nested config under each toolset.

    Args:
        console: Rich console instance for output
    """
    if console is None:
        console = get_console()

    try:
        from agent.config import load_config

        config = load_config()

        from pathlib import Path

        # Import here to avoid circular dependencies
        from agent.agent import Agent

        # Create agent instance to load toolsets
        agent = Agent(config)

        console.print()

        # Display each toolset with nested configuration
        for toolset in agent.toolsets:
            toolset_name = type(toolset).__name__
            tools = toolset.get_tools()

            # Toolset header
            console.print(f"● [bold]{toolset_name}[/bold] · {len(tools)} tools")

            # Nest configuration under specific toolsets
            if toolset_name == "FileSystemTools":
                # Determine workspace root and source
                if hasattr(config, "workspace_root") and config.workspace_root is not None:
                    workspace_root = config.workspace_root
                    workspace_source = "config"
                elif env_workspace := os.getenv("AGENT_WORKSPACE_ROOT"):
                    workspace_root = Path(env_workspace).expanduser().resolve()
                    workspace_source = "env"
                else:
                    workspace_root = Path.cwd().resolve()
                    workspace_source = "cwd"

                # Filesystem configuration
                writes_enabled = getattr(config, "filesystem_writes_enabled", False)
                write_status = (
                    "[green]Enabled[/green]" if writes_enabled else "[yellow]Disabled[/yellow]"
                )
                write_bullet = "[green]◉[/green]" if writes_enabled else "[red]◉[/red]"
                read_limit_mb = (
                    getattr(config, "filesystem_max_read_bytes", 10_485_760) // 1_048_576
                )
                write_limit_mb = (
                    getattr(config, "filesystem_max_write_bytes", 1_048_576) // 1_048_576
                )

                console.print(
                    f"└─ [cyan]◉[/cyan] Workspace: [cyan]{workspace_root}[/cyan] [dim]({workspace_source})[/dim]"
                )
                console.print(
                    f"└─ {write_bullet} Writes: {write_status} · Read: [dim]{read_limit_mb}MB[/dim] · Write: [dim]{write_limit_mb}MB[/dim]"
                )

            elif toolset_name == "ScriptToolset":
                # Skills configuration (only counts enabled skills)
                if hasattr(agent, "skill_docs") and agent.skill_docs.has_skills():
                    skill_count = agent.skill_docs.count()
                    console.print(
                        f"└─ [green]◉[/green] skills enabled [dim]({skill_count} skills · progressive disclosure)[/dim]"
                    )

            # Tool list (use • bullet for individual tools)
            for tool in tools:
                # Get docstring and count tokens
                from agent.utils.tokens import count_tokens

                docstring = tool.__doc__ or ""
                # Extract first line only (LLM-facing description)
                first_line = docstring.strip().split("\n")[0] if docstring.strip() else ""
                token_count = count_tokens(first_line) if first_line else 0

                console.print(f"  [dim]• {tool.__name__}[/dim] · [dim]{token_count} tokens[/dim]")

            # Add blank line after each toolset except the last
            if toolset != agent.toolsets[-1]:
                console.print()

    except Exception as e:
        console.print(f"[red]✗[/red] Error loading tool configuration: {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


def run_health_check(console: Console | None = None) -> None:
    """Run unified health check with configuration and connectivity.

    Note: Uses Unicode characters (◉, ○, ✓, ⚠) for visual display.
    These render correctly in modern terminals (PowerShell, cmd, bash interactive)
    but may cause UnicodeEncodeError when output is piped through non-interactive
    shells with cp1252 encoding. This is acceptable since the primary use case
    is interactive terminal display, not scripted/piped output.
    """
    if console is None:
        console = get_console()

    console.print()

    try:
        # Configuration validation
        config = load_config_with_env()
        errors = config.validate_enabled_providers()
        if errors:
            for error in errors:
                console.print(f" [red]✗[/red] {error}")
            raise typer.Exit(ExitCodes.CONFIG_ERROR)

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

                # Also check if chromadb is actually installed (only needed for local mode)
                if is_compatible:
                    is_cloud = bool(config.mem0_api_key and config.mem0_org_id)
                    if not is_cloud:  # Only check chromadb for local mode
                        try:
                            import chromadb  # noqa: F401
                        except ImportError:
                            mem0_available = False
                            unavailable_reason = "chromadb package not installed"

            except ImportError:
                unavailable_reason = "mem0ai package not installed"

            if not mem0_available:
                # Show actual backend (in_memory) with note about mem0
                console.print("  [cyan]◉[/cyan] Backend: [cyan]in_memory[/cyan]")
                console.print(
                    f"  [yellow]⚠[/yellow]  mem0 configured but unavailable: [yellow]{unavailable_reason}[/yellow]"
                )
                console.print("  [dim]Run 'agent config memory' to install dependencies[/dim]")
            else:
                # Show mem0 as backend with configuration (only when actually available and working)
                # This branch is ONLY reached when mem0 is both configured and functional
                console.print("  [cyan]◉[/cyan] Backend: [cyan]mem0[/cyan]")

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

                # Show embedding model being used (mem0 only - in_memory doesn't use embeddings)
                try:
                    from agent.memory.mem0_utils import extract_llm_config, get_embedding_model

                    llm_config = extract_llm_config(config)

                    # Get the embedding model name (without provider suffixes)
                    embedding_model = get_embedding_model(llm_config)

                    # Add provider context for display
                    if config.llm_provider == "github":
                        embedding_display = f"{embedding_model} [dim](via GitHub Models)[/dim]"
                    elif llm_config["provider"] == "anthropic":
                        embedding_display = f"{embedding_model} [dim](via Anthropic)[/dim]"
                    elif llm_config["provider"] == "azure_openai":
                        embedding_display = f"{embedding_model} [dim](Azure)[/dim]"
                    elif llm_config["provider"] == "gemini":
                        embedding_display = f"{embedding_model} [dim](Gemini)[/dim]"
                    else:
                        embedding_display = embedding_model

                    console.print(f"  [cyan]◉[/cyan] Embeddings: [dim]{embedding_display}[/dim]")
                except Exception as e:
                    # Don't fail health check if we can't determine embedding model
                    logger.debug(f"Failed to determine embedding model: {e}")

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

        # If it's a "No configuration found" or "No providers enabled" error, offer to run init
        if "No configuration found" in error_msg or "No providers enabled" in error_msg:
            # Only offer interactive setup if running in a TTY
            if sys.stdin.isatty():
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
