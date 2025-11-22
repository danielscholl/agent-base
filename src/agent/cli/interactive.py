"""Interactive chat mode for Agent CLI.

This module handles:
- Interactive chat loop with prompt_toolkit
- Session management and restoration
- Keybinding support
- Command handling (/help, /clear, /continue, /telemetry, etc.)
- Lazy agent initialization
- Exit cleanup and session auto-save
- Status bar with git branch display
- Startup banner

Extracted from cli/app.py to improve maintainability.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.prompt import Confirm

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
    restore_session_context,
    setup_session_logging,
    track_conversation,
)
from agent.cli.utils import (
    get_console,
    hide_connection_string_if_otel_disabled,
    set_model_span_attributes,
)
from agent.config import load_config_with_env
from agent.config.schema import AgentSettings
from agent.display import DisplayMode, set_execution_context
from agent.persistence import ThreadPersistence
from agent.utils.keybindings import ClearPromptHandler, KeybindingManager

logger = logging.getLogger(__name__)

# Cache git branch lookup to avoid spawning a subprocess every prompt
_BRANCH_CACHE_CWD: Path | None = None
_BRANCH_CACHE_VALUE: str = ""


async def _execute_interactive_query(
    agent: Agent,
    user_input: str,
    thread: ThreadPersistence,
    quiet: bool,
    verbose: bool,
    console: Console,
) -> str | None:
    """Execute query in interactive mode with appropriate visualization.

    Args:
        agent: Configured agent instance
        user_input: User input to process
        thread: Thread persistence instance
        quiet: Whether to use quiet mode
        verbose: Whether to show detailed execution tree
        console: Console for output

    Returns:
        Response string from agent execution
    """
    if not quiet:
        display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
        try:
            return await execute_with_visualization(
                agent, user_input, thread, console, display_mode
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow] - Press Ctrl+C again to exit\n")
            raise
    else:
        try:
            return await execute_quiet_mode(agent, user_input, thread)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]\n")
            raise


def _render_startup_banner(config: AgentSettings, console: Console) -> None:
    """Render startup banner with branding.

    Args:
        config: Agent configuration
        console: Rich console for output
    """
    console.print("[bold cyan]Agent[/bold cyan] - Conversational Assistant")
    # Disable both markup and highlighting to prevent Rich from coloring numbers
    console.print(
        f"Version {__version__} • {config.get_model_display_name()}",
        style="dim",
        markup=False,
        highlight=False,
    )


def _get_status_bar_text(console: Console) -> str:
    """Get status bar text without printing.

    Args:
        console: Rich console for width calculation

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


async def _execute_agent_query(
    agent: Agent,
    user_input: str,
    thread: Any,
    quiet: bool,
    verbose: bool,
    console: Console,
) -> str | None:
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
            set_model_span_attributes(span, config)

            # Execute with shared execution logic
            return await _execute_interactive_query(
                agent, user_input, thread, quiet, verbose, console
            )
    else:
        # Execute without observability wrapper
        return await _execute_interactive_query(agent, user_input, thread, quiet, verbose, console)


async def run_chat_mode(
    quiet: bool = False,
    verbose: bool = False,
    resume_session: str | None = None,
    console: Console | None = None,
) -> None:
    """Run interactive chat mode.

    Features:
    - Lazy agent initialization (fast startup)
    - Session persistence and restoration
    - Keyboard shortcuts (Ctrl+Alt+L to clear prompt)
    - Command handling (/help, /clear, /continue, /exit, etc.)
    - Git branch status bar
    - Auto-save on exit

    Args:
        quiet: Minimal output mode
        verbose: Verbose output mode with detailed execution tree
        resume_session: Session name to resume (from --continue flag)
        console: Rich console for output (creates default if None)

    Raises:
        typer.Exit: On configuration errors or execution failures
    """
    if console is None:
        console = get_console()

    try:
        import time

        perf_start = time.perf_counter()

        # Load configuration
        config = load_config_with_env()
        errors = config.validate_enabled_providers()
        if errors:
            for error in errors:
                console.print(f"[red]Error:[/red] {error}")
            raise typer.Exit(ExitCodes.CONFIG_ERROR)
        logger.info(
            f"[PERF] Interactive mode - config loaded: {(time.perf_counter() - perf_start)*1000:.1f}ms"
        )

        # Hide Azure connection string if telemetry disabled (prevents 1-3s exit lag)
        saved_connection_string = hide_connection_string_if_otel_disabled(config)

        # Setup observability with auto-detection
        # Rules:
        # 1. If telemetry explicitly enabled in config, always respect it
        # 2. If not explicit, auto-detect endpoint availability
        # 3. If endpoint reachable, enable telemetry automatically
        should_enable_otel = config.enable_otel

        if not config.enable_otel_explicit:
            # User didn't explicitly enable telemetry, check if endpoint is available
            from agent.observability import check_telemetry_endpoint

            if check_telemetry_endpoint(config.otlp_endpoint):
                should_enable_otel = True
                logger.info(
                    f"Telemetry endpoint detected at {config.otlp_endpoint}, enabling observability"
                )

        if should_enable_otel:
            from agent_framework.observability import setup_observability

            setup_observability(
                enable_sensitive_data=config.enable_sensitive_data,
                otlp_endpoint=config.otlp_endpoint,
                applicationinsights_connection_string=config.applicationinsights_connection_string,
            )

        # Generate session name for this session (used for both logging and saving)
        session_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        # Setup session-specific logging (follows copilot pattern: ~/.agent/logs/session-{name}.log)
        # Logs go to file, not console, to keep output clean
        setup_session_logging(session_name, config)

        # Set session ID for telemetry correlation
        os.environ["SESSION_ID"] = session_name

        # Show startup banner
        if not quiet:
            _render_startup_banner(config, console)

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
            agent = Agent(settings=config)
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
                    status_text = _get_status_bar_text(console)
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
                        agent = Agent(settings=config)
                        logger.info(
                            f"[PERF] Agent lazy init for /clear: {(time.perf_counter() - init_start)*1000:.1f}ms"
                        )
                    thread, message_count = await handle_clear_command(agent, console)
                    continue
                elif cmd in Commands.CONTINUE:
                    # Create agent if needed (lazy init)
                    if agent is None:
                        init_start = time.perf_counter()
                        agent = Agent(settings=config)
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
                            agent = Agent(settings=config)
                    else:
                        agent = Agent(settings=config)
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
            except Exception as e:
                # Handle provider API errors and other exceptions
                from agent.cli.error_handler import format_error
                from agent.exceptions import AgentError

                if isinstance(e, AgentError):
                    # Our custom errors - format nicely
                    error_message = format_error(e)
                    console.print(f"\n{error_message}\n")
                else:
                    # Unknown errors - show generic message
                    console.print(f"\n[red]Unexpected error:[/red] {e}\n")
                    logger.exception("Unexpected error in interactive mode")

                # Continue loop - don't crash
                continue

    except ValueError as e:
        error_msg = str(e)
        console.print(f"[red]Configuration error:[/red] {error_msg}\n")

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
