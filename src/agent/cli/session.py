"""Session management helpers for CLI."""

from datetime import datetime
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from rich.console import Console

from agent.agent import Agent
from agent.persistence import ThreadPersistence


async def auto_save_session(
    persistence: ThreadPersistence,
    thread: Any,
    message_count: int,
    quiet: bool,
    messages: list[dict] | None = None,
    console: Console | None = None,
) -> None:
    """Auto-save session on exit if it has messages.

    Args:
        persistence: ThreadPersistence instance
        thread: Conversation thread (can be None for some providers)
        message_count: Number of messages in session
        quiet: Whether to suppress output
        messages: Optional list of tracked messages for providers without thread support
        console: Console for output (optional)
    """
    if message_count > 0:
        try:
            # Generate auto-save name with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            session_name = timestamp

            await persistence.save_thread(
                thread,
                session_name,
                description="Auto-saved session",
                messages=messages,
            )

            # Save as last session for --continue
            _save_last_session(session_name)

            if not quiet and console:
                console.print(f"[dim]Session auto-saved as '{session_name}'[/dim]")
        except Exception as e:
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
        thread, context_summary = await persistence.load_thread(agent, session_name)

        # If we have a context summary, restore AI context silently
        message_count = 0
        if context_summary:
            if not quiet:
                with console.status("[bold blue]Restoring context...", spinner="dots"):
                    await agent.run(context_summary, thread=thread)
                    message_count = 1
            else:
                await agent.run(context_summary, thread=thread)
                message_count = 1

        # Show single clean status message after restore
        if not quiet:
            console.print("[green]✓ Ready[/green]\n")
            console.print(f"[dim]{'─' * console.width}[/dim]")

        return thread, context_summary, message_count

    except FileNotFoundError:
        console.print(f"[yellow]Session '{session_name}' not found. Starting new session.[/yellow]\n")
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
        import logging

        logging.warning(f"Failed to save last session marker: {e}")


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
        import logging

        logging.warning(f"Failed to read last session marker: {e}")

    return None
