"""Command handlers for CLI."""

from typing import Any

from prompt_toolkit import PromptSession
from rich.console import Console

from agent.agent import Agent
from agent.cli.session import pick_session, restore_session_context
from agent.persistence import ThreadPersistence
from agent.utils.terminal import TIMEOUT_EXIT_CODE, clear_screen, execute_shell_command


async def handle_shell_command(command: str, console: Console) -> None:
    """Execute and display shell command output.

    Args:
        command: Shell command to execute
        console: Console for output
    """
    if not command:
        console.print(
            "\n[yellow]No command specified. Type !<command> to execute shell commands.[/yellow]\n"
        )
        return

    # Show what we're executing
    console.print(f"\n[dim]$ {command}[/dim]")

    # Execute the command
    exit_code, stdout, stderr = execute_shell_command(command)

    # Display output
    if stdout:
        console.print(stdout, end="")
    if stderr:
        console.print(f"[red]{stderr}[/red]", end="")

    # Display exit code
    if exit_code == 0:
        console.print(f"\n[dim][green]Exit code: {exit_code}[/green][/dim]")
    elif exit_code == TIMEOUT_EXIT_CODE:
        console.print(f"\n[dim][yellow]Exit code: {exit_code} (timeout)[/yellow][/dim]")
    else:
        console.print(f"\n[dim][red]Exit code: {exit_code}[/red][/dim]")

    console.print()


async def handle_clear_command(agent: Agent, console: Console) -> tuple[Any, int]:
    """Handle /clear command.

    Args:
        agent: Agent instance
        console: Console for output

    Returns:
        Tuple of (new_thread, message_count)
    """
    if not clear_screen():
        console.print("[yellow]Warning: Failed to clear the screen.[/yellow]")

    # Reset conversation context
    thread = agent.get_new_thread()
    message_count = 0

    return thread, message_count


async def handle_continue_command(
    agent: Agent,
    persistence: ThreadPersistence,
    session: PromptSession,
    console: Console,
) -> tuple[Any | None, int]:
    """Handle /continue command.

    Args:
        agent: Agent instance
        persistence: ThreadPersistence instance
        session: PromptSession for user input
        console: Console for output

    Returns:
        Tuple of (thread, message_count)
    """
    session_name, _, _ = await pick_session(persistence, session, console)

    if session_name:
        thread, _, message_count = await restore_session_context(
            agent, persistence, session_name, console
        )
        return thread, message_count

    return None, 0


async def handle_purge_command(
    persistence: ThreadPersistence,
    session: PromptSession,
    console: Console,
) -> None:
    """Handle /purge command.

    Args:
        persistence: ThreadPersistence instance
        session: PromptSession for user input
        console: Console for output
    """
    sessions = persistence.list_sessions()
    if not sessions:
        console.print("\n[yellow]No sessions to purge[/yellow]\n")
        return

    # Confirm deletion
    console.print(f"\n[yellow]⚠ This will delete ALL {len(sessions)} saved sessions.[/yellow]")

    try:
        confirm = await session.prompt_async("Continue? (y/n): ")
        if confirm.strip().lower() == "y":
            deleted = 0
            for sess in sessions:
                try:
                    persistence.delete_session(sess["name"])
                    deleted += 1
                except Exception as e:
                    console.print(f"[yellow]Failed to delete {sess['name']}: {e}[/yellow]")

            console.print(f"\n[green]✓ Deleted {deleted} sessions[/green]\n")
        else:
            console.print("\n[yellow]Cancelled[/yellow]\n")
    except (EOFError, KeyboardInterrupt):
        console.print("\n[yellow]Cancelled[/yellow]\n")


def show_help(console: Console) -> None:
    """Show help message in interactive mode.

    Args:
        console: Console for output
    """
    console.print("\n[bold]Available Commands:[/bold]")
    console.print("  [cyan]/clear[/cyan]     - Clear screen and start new conversation")
    console.print("  [cyan]/continue[/cyan]  - Resume a previous session")
    console.print("  [cyan]/purge[/cyan]     - Delete all saved sessions")
    console.print("  [cyan]/help[/cyan]      - Show this help message")
    console.print("  [cyan]exit[/cyan]       - Exit interactive mode")
    console.print()
    console.print("[bold]Shell Commands:[/bold]")
    console.print("  [cyan]!<command>[/cyan] - Execute shell command")
    console.print()
    console.print("[bold]Keyboard Shortcuts:[/bold]")
    console.print("  [cyan]ESC[/cyan]        - Clear current prompt")
    console.print("  [cyan]Ctrl+D[/cyan]     - Exit interactive mode")
    console.print("  [cyan]Ctrl+C[/cyan]     - Interrupt current operation")
    console.print()
