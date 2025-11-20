"""Session management helpers for CLI."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from rich.console import Console

from agent.agent import Agent
from agent.config import AgentConfig
from agent.persistence import ThreadPersistence

logger = logging.getLogger(__name__)


def setup_session_logging(
    session_name: str | None = None, config: AgentConfig | None = None
) -> str:
    """Setup session-specific logging to file (not console).

    Follows copilot pattern: ~/.agent/logs/session-{name}.log
    Also creates trace log file if trace logging is enabled.

    Args:
        session_name: Session identifier (timestamp or custom name)
        config: Agent configuration (optional, will load if not provided)

    Returns:
        Path to log file as string

    Example:
        >>> setup_session_logging("2025-11-09-13-16-20")
        '/Users/user/.agent/logs/session-2025-11-09-13-16-20.log'
    """
    # Load config if not provided
    if config is None:
        config = AgentConfig.from_env()

    # Create logs directory
    log_dir = config.agent_data_dir or Path.home() / ".agent"
    log_dir = log_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate session name if not provided
    if session_name is None:
        session_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # Create log file path (follow copilot pattern: session-{name}.log)
    log_file = log_dir / f"session-{session_name}.log"

    # Configure logging
    # Support both AGENT_LOG_LEVEL and LOG_LEVEL (backward compatibility)
    log_level = os.getenv("AGENT_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO"
    log_level = log_level.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Clear any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Setup file handler (not stdout/stderr)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=str(log_file),
        filemode="a",  # Append mode
        force=True,  # Reconfigure if already configured
    )

    # Setup trace logging if log level is trace
    if log_level == "TRACE":
        from agent.middleware import set_trace_logger
        from agent.trace_logger import TraceLogger

        # Create trace log file path
        trace_log_file = log_dir / f"session-{session_name}-trace.log"

        # Create and set trace logger
        # Include messages only if ENABLE_SENSITIVE_DATA is set
        include_messages = config.enable_sensitive_data
        trace_logger = TraceLogger(trace_file=trace_log_file, include_messages=include_messages)
        set_trace_logger(trace_logger)

        logger.info(
            f"Trace logging enabled: {trace_log_file} "
            f"(include_messages={include_messages}, sensitive_data={config.enable_sensitive_data})"
        )

    return str(log_file)


async def auto_save_session(
    persistence: ThreadPersistence,
    thread: Any,
    message_count: int,
    quiet: bool,
    messages: list[dict] | None = None,
    console: Console | None = None,
    session_name: str | None = None,
    agent: Agent | None = None,
    log_dir: Path | None = None,
) -> None:
    """Auto-save session on exit if it has messages.

    Args:
        persistence: ThreadPersistence instance
        thread: Conversation thread (can be None for some providers)
        message_count: Number of messages in session
        quiet: Whether to suppress output
        messages: Optional list of tracked messages for providers without thread support
        console: Console for output (optional)
        session_name: Optional session name (if not provided, generates timestamp)
        agent: Optional Agent instance for memory saving
        log_dir: Optional log directory path (avoids path reconstruction)
    """
    import time

    save_start = time.perf_counter()

    # Skip save for empty sessions (optimization: no conversation = nothing to persist)
    if message_count == 0:
        logger.debug("[PERF] Skipping session save - no messages exchanged")
        return

    if message_count > 0:
        try:
            # Use provided session name or generate one with timestamp
            if session_name is None:
                timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                session_name = timestamp

            await persistence.save_thread(
                thread,
                session_name,
                description="Auto-saved session",
                messages=messages,
            )

            # Save memory state if agent has memory enabled and using in-memory backend
            # For semantic backends (mem0), memory is already persisted externally and
            # fetching all entries can introduce noticeable exit latency.
            if (
                agent
                and agent.memory_manager
                and getattr(agent.config, "memory_type", "in_memory") == "in_memory"
            ):
                try:
                    memory_result = await agent.memory_manager.get_all()
                    if memory_result.get("success") and memory_result["result"]:
                        memory_data = memory_result["result"]
                        await persistence.save_memory_state(session_name, memory_data)
                        if not quiet and console:
                            console.print(f"[dim]Saved {len(memory_data)} memories[/dim]")
                except Exception as e:
                    if not quiet and console:
                        console.print(f"[yellow]Warning: Failed to save memory: {e}[/yellow]")

            # Copy trace log file if it exists
            # Use provided log_dir or reconstruct from persistence storage dir
            if log_dir is None:
                log_dir = persistence.storage_dir.parent / "logs"
            trace_log_file = log_dir / f"session-{session_name}-trace.log"
            if trace_log_file.exists():
                try:
                    import shutil

                    # Copy trace log to session directory
                    session_trace_log = persistence.storage_dir / f"{session_name}-trace.log"
                    shutil.copy2(trace_log_file, session_trace_log)
                    logger.debug(f"Copied trace log to session directory: {session_trace_log}")
                except Exception as e:
                    logger.warning(f"Failed to copy trace log: {e}")

            # Save as last session for --continue
            _save_last_session(session_name)

            save_duration = (time.perf_counter() - save_start) * 1000
            logger.info(f"[PERF] Session save completed: {save_duration:.1f}ms")

            if not quiet and console:
                console.print(f"[dim]Session auto-saved as '{session_name}'[/dim]")
        except Exception as e:
            logger.warning(
                f"[PERF] Session save failed after {(time.perf_counter() - save_start)*1000:.1f}ms: {e}"
            )
            if not quiet and console:
                console.print(f"\n[yellow]Failed to auto-save session: {e}[/yellow]")


def track_conversation(messages: list[dict], user_input: str, response: Any) -> None:
    """Track conversation messages for persistence.

    Args:
        messages: List to append messages to
        user_input: User's input message
        response: Agent's response (str or object with .text attribute)
    """
    messages.append({"role": "user", "content": user_input})
    response_text = response.text if hasattr(response, "text") else str(response)
    messages.append({"role": "assistant", "content": response_text})


async def pick_session(
    persistence: ThreadPersistence,
    session: PromptSession,
    console: Console,
) -> tuple[str | None, Any | None, str | None]:
    """Interactive session picker.

    Args:
        persistence: ThreadPersistence instance
        session: PromptSession for user input
        console: Console for output

    Returns:
        Tuple of (session_name, thread, context_summary) or (None, None, None) if cancelled
    """
    sessions = persistence.list_sessions()
    if not sessions:
        console.print("\n[yellow]No saved sessions available[/yellow]\n")
        return None, None, None

    # Show session picker
    console.print("\n[bold]Available Sessions:[/bold]")
    for i, sess in enumerate(sessions, 1):
        created = sess.get("created_at", "")
        # Calculate time ago
        try:
            created_dt = datetime.fromisoformat(created)
            now = datetime.now()
            delta = now - created_dt
            if delta.days > 0:
                time_ago = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                time_ago = f"{delta.seconds // 3600}h ago"
            else:
                time_ago = f"{delta.seconds // 60}m ago"
        except Exception:
            time_ago = "unknown"

        # Get first message preview
        first_msg = sess.get("first_message", "")
        if len(first_msg) > 50:
            first_msg = first_msg[:47] + "..."

        console.print(f"  {i}. [cyan]{sess['name']}[/cyan] [dim]({time_ago})[/dim] \"{first_msg}\"")

    # Get user selection
    try:
        choice = await session.prompt_async(f"\nSelect session [1-{len(sessions)}]: ")
        choice_num = int(choice.strip())
        if 1 <= choice_num <= len(sessions):
            return sessions[choice_num - 1]["name"], None, None
        else:
            console.print("[red]Invalid selection[/red]\n")
            return None, None, None
    except (ValueError, EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled[/yellow]\n")
        return None, None, None


async def restore_session_context(
    agent: Agent,
    persistence: ThreadPersistence,
    session_name: str,
    console: Console,
    quiet: bool = False,
) -> tuple[Any | None, str | None, int]:
    """Restore a session's context.

    Args:
        agent: Agent instance
        persistence: ThreadPersistence instance
        session_name: Name of session to restore
        console: Console for output
        quiet: Whether to suppress output

    Returns:
        Tuple of (thread, context_summary, message_count)
    """
    try:
        # Show history unless in quiet mode
        thread, context_summary = await persistence.load_thread(
            agent, session_name, show_history=not quiet
        )

        # Load memory state silently if agent has memory enabled
        if agent.memory_manager:
            try:
                memory_data = await persistence.load_memory_state(session_name)
                if memory_data:
                    # Restore memories into the memory manager
                    result = await agent.memory_manager.add(memory_data)
                    if result.get("success"):
                        memory_count = len(memory_data)
                        logger.info(
                            f"Restored {memory_count} memories from session '{session_name}'"
                        )
                    else:
                        logger.warning(f"Failed to restore memories: {result.get('message')}")
            except Exception as e:
                logger.warning(f"Could not load memory state: {e}")

        # If we have a context summary, restore AI context silently
        # Skip this if memory is enabled - memory already provides full context
        message_count = 0
        if context_summary and not agent.memory_manager:
            # Only restore context summary if memory is NOT enabled
            if not quiet:
                with console.status("[bold blue]Restoring context...", spinner="dots"):
                    await agent.run(context_summary, thread=thread)
                    message_count = 1
            else:
                await agent.run(context_summary, thread=thread)
                message_count = 1

        # Don't show extra message - just continue seamlessly
        # The history display above provides enough context

        return thread, context_summary, message_count

    except FileNotFoundError:
        console.print(
            f"[yellow]Session '{session_name}' not found. Starting new session.[/yellow]\n"
        )
        return None, None, 0
    except Exception as e:
        console.print(f"[yellow]Failed to resume session: {e}. Starting new session.[/yellow]\n")
        return None, None, 0


def _save_last_session(session_name: str) -> None:
    """Save the last session name for --continue.

    Args:
        session_name: Name of the session to track
    """
    try:
        # Use .agent directory in home
        last_session_file = Path.home() / ".agent" / "last_session"
        last_session_file.parent.mkdir(parents=True, exist_ok=True)

        with open(last_session_file, "w") as f:
            f.write(session_name)

    except Exception as e:
        logger.warning(f"Failed to save last session marker: {e}")


def get_last_session() -> str | None:
    """Get the last session name for --continue.

    Returns:
        Last session name or None if not found
    """
    try:
        last_session_file = Path.home() / ".agent" / "last_session"
        if last_session_file.exists():
            with open(last_session_file) as f:
                return f.read().strip()
    except Exception as e:
        logger.warning(f"Failed to read last session marker: {e}")

    return None
