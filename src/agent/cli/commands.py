"""Command handlers for CLI."""

import subprocess
import time
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
    console.print("  [cyan]/clear[/cyan]      - Clear screen and start new conversation")
    console.print("  [cyan]/continue[/cyan]   - Resume a previous session")
    console.print("  [cyan]/purge[/cyan]      - Delete all saved sessions")
    console.print("  [cyan]/telemetry[/cyan]  - Manage local observability dashboard")
    console.print("  [cyan]/help[/cyan]       - Show this help message")
    console.print("  [cyan]exit[/cyan]        - Exit interactive mode")
    console.print()
    console.print("[bold]Shell Commands:[/bold]")
    console.print("  [cyan]!<command>[/cyan]  - Execute shell command")
    console.print()
    console.print("[bold]Keyboard Shortcuts:[/bold]")
    console.print("  [cyan]ESC[/cyan]         - Clear current prompt")
    console.print("  [cyan]Ctrl+D[/cyan]      - Exit interactive mode")
    console.print("  [cyan]Ctrl+C[/cyan]      - Interrupt current operation")
    console.print()


async def handle_telemetry_command(user_input: str, console: Console) -> None:
    """Handle /telemetry command for managing telemetry dashboard.

    Args:
        user_input: Full user input (e.g., "/telemetry start")
        console: Console for output

    Commands:
        /telemetry start  - Start telemetry dashboard
        /telemetry stop   - Stop telemetry dashboard
        /telemetry status - Check if running
        /telemetry url    - Show dashboard URL and setup
    """
    parts = user_input.strip().split()
    action = parts[1].lower() if len(parts) > 1 else "help"

    CONTAINER_NAME = "aspire-dashboard"
    DASHBOARD_URL = "http://localhost:18888"
    OTLP_ENDPOINT = "http://localhost:4317"

    try:
        if action == "start":
            # Check if Docker is available
            try:
                subprocess.run(
                    ["docker", "--version"],
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                console.print("\n[red]Error: Docker is not installed or not running[/red]")
                console.print(
                    "[yellow]Install Docker from: https://docs.docker.com/get-docker/[/yellow]\n"
                )
                return

            # Check if already running
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if CONTAINER_NAME in result.stdout:
                console.print("\n[yellow]Telemetry dashboard is already running![/yellow]")
                console.print(f"[cyan]Dashboard:[/cyan] {DASHBOARD_URL}")
                console.print(f"[cyan]OTLP Endpoint:[/cyan] {OTLP_ENDPOINT}\n")
                return

            # Start telemetry dashboard
            console.print("\n[dim]Starting telemetry dashboard...[/dim]")
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-d",
                    "-p",
                    "18888:18888",
                    "-p",
                    "4317:18889",
                    "--name",
                    CONTAINER_NAME,
                    "-e",
                    "DOTNET_DASHBOARD_UNSECURED_ALLOW_ANONYMOUS=true",
                    "mcr.microsoft.com/dotnet/aspire-dashboard:latest",
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )

            # Wait for startup
            time.sleep(3)

            console.print("\n[green]✓ Telemetry dashboard started successfully![/green]\n")
            console.print(f"  Dashboard: {DASHBOARD_URL}\n")
            console.print("[bold]To enable telemetry:[/bold]")
            console.print("  export ENABLE_OTEL=true\n")

        elif action == "stop":
            # Stop the container
            result = subprocess.run(
                ["docker", "stop", CONTAINER_NAME],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                console.print("\n[green]✓ Telemetry dashboard stopped[/green]\n")
            else:
                console.print("\n[yellow]Telemetry dashboard was not running[/yellow]\n")

        elif action == "status":
            # Check if running
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if CONTAINER_NAME in result.stdout:
                # Get uptime
                uptime_result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        f"name={CONTAINER_NAME}",
                        "--format",
                        "{{.Status}}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                console.print("\n[green]✓ Telemetry dashboard is running[/green]")
                console.print(f"[dim]Status: {uptime_result.stdout.strip()}[/dim]")
                console.print(f"[cyan]Dashboard:[/cyan] {DASHBOARD_URL}")
                console.print(f"[cyan]OTLP Endpoint:[/cyan] {OTLP_ENDPOINT}\n")
            else:
                console.print("\n[yellow]Telemetry dashboard is not running[/yellow]")
                console.print("[dim]Start with: /telemetry start[/dim]\n")

        elif action == "url":
            console.print("\n[bold]Telemetry Dashboard:[/bold]")
            console.print(f"  {DASHBOARD_URL}\n")
            console.print("[bold]Enable telemetry:[/bold]")
            console.print("  export ENABLE_OTEL=true\n")

        else:
            # Show help
            console.print("\n[bold]Telemetry Commands:[/bold]")
            console.print("  [cyan]/telemetry start[/cyan]  - Start telemetry dashboard")
            console.print("  [cyan]/telemetry stop[/cyan]   - Stop telemetry dashboard")
            console.print("  [cyan]/telemetry status[/cyan] - Check if running")
            console.print("  [cyan]/telemetry url[/cyan]    - Show URLs and setup")
            console.print()

    except subprocess.TimeoutExpired:
        console.print("\n[red]Error: Docker command timed out[/red]\n")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]\n")
