"""CLI entry point for Agent."""

import asyncio
import subprocess
from pathlib import Path

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
    track_conversation,
)
from agent.config import AgentConfig
from agent.display import DisplayMode, set_execution_context
from agent.persistence import ThreadPersistence
from agent.utils.keybindings import ClearPromptHandler, KeybindingManager

app = typer.Typer(help="Agent - Conversational Assistant")
console = Console()


def _render_startup_banner(config: AgentConfig) -> None:
    """Render startup banner with branding.

    Args:
        config: Agent configuration
    """
    console.print()
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
    except Exception:
        pass

    # Right-justify the path and branch
    status = f"{cwd_display}{branch_display}"
    padding = max(0, console.width - len(status))

    return f"{' ' * padding}{status}"


@app.command()
def main(
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a single prompt and exit"),
    check: bool = typer.Option(False, "--check", help="Run health check for configuration"),
    config_flag: bool = typer.Option(False, "--config", help="Show current configuration"),
    version_flag: bool = typer.Option(False, "--version", help="Show version"),
    verbose: bool = typer.Option(
        False, "--verbose", help="Verbose output with detailed execution tree"
    ),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output mode"),
    resume: bool = typer.Option(False, "--continue", help="Resume last saved session"),
):
    """Agent - Generic chatbot agent with extensible tools.

    Examples:
        # Interactive mode
        agent

        # Run health check
        agent --check

        # Show configuration
        agent --config

        # Execute single prompt
        agent -p "Say hello to Alice"

        # Execute with verbose visualization
        agent -p "Say hello to Alice" --verbose

        # Resume previous session
        agent --continue

        # Show version
        agent --version
    """
    if version_flag:
        console.print(f"Agent version {__version__}")
        return

    if check:
        run_health_check()
        return

    if config_flag:
        show_configuration()
        return

    if prompt:
        # Single-prompt mode with optional visualization
        asyncio.run(run_single_prompt(prompt, verbose=verbose, quiet=quiet))
    else:
        # Interactive chat mode
        # Handle --continue flag: resume last session
        resume_session = None
        if resume:
            resume_session = get_last_session()
            if not resume_session:
                console.print("[yellow]No previous session found. Starting new session.[/yellow]\n")

        asyncio.run(run_chat_mode(quiet=quiet, verbose=verbose, resume_session=resume_session))


def run_health_check():
    """Run health check for dependencies and configuration."""
    console.print("\n[bold]Agent Health Check[/bold]\n")

    try:
        config = AgentConfig.from_env()
        config.validate()

        console.print("[green]✓[/green] Configuration valid")
        console.print(f"  Provider: {config.llm_provider}")
        console.print(f"  Model: {config.get_model_display_name()}")

        if config.agent_data_dir:
            console.print(f"  Data Dir: {config.agent_data_dir}")

        console.print("\n[green]✓ All checks passed![/green]\n")

    except ValueError as e:
        console.print(f"[red]✗[/red] Configuration error: {e}")
        console.print("\n[yellow]See .env.example for configuration template[/yellow]")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


def show_configuration():
    """Show current configuration."""
    console.print("\n[bold]Agent Configuration[/bold]\n")

    try:
        config = AgentConfig.from_env()

        console.print("[bold]LLM Provider:[/bold]")
        console.print(f" • Provider: {config.llm_provider}")
        console.print(f" • Model: {config.get_model_display_name()}")

        if config.llm_provider == "openai" and config.openai_api_key:
            masked_key = f"****{config.openai_api_key[-6:]}"
            console.print(f" • API Key: {masked_key}")
        elif config.llm_provider == "anthropic" and config.anthropic_api_key:
            masked_key = f"****{config.anthropic_api_key[-6:]}"
            console.print(f" • API Key: {masked_key}")
        elif config.llm_provider == "azure":
            console.print(f" • Endpoint: {config.azure_openai_endpoint}")
            if config.azure_openai_api_key:
                masked_key = f"****{config.azure_openai_api_key[-6:]}"
                console.print(f" • API Key: {masked_key}")
        elif config.llm_provider == "azure_ai_foundry":
            console.print(f" • Endpoint: {config.azure_project_endpoint}")

        console.print("\n[bold]Agent Settings:[/bold]")
        console.print(f" • Data Directory: {config.agent_data_dir}")
        if config.agent_session_dir:
            console.print(f" • Session Directory: {config.agent_session_dir}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(ExitCodes.GENERAL_ERROR)


async def run_single_prompt(prompt: str, verbose: bool = False, quiet: bool = False):
    """Run single prompt and display response.

    Args:
        prompt: User prompt to execute
        verbose: Show verbose execution tree
        quiet: Minimal output mode
    """
    try:
        config = AgentConfig.from_env()
        config.validate()

        agent = Agent(config=config)

        # Setup execution context for visualization
        ctx = create_execution_context(verbose, quiet, is_interactive=False)
        set_execution_context(ctx)

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

        # Display response after completion summary
        if response:
            console.print(f"\n{response}\n")
            console.print(f"[dim]{'─' * console.width}[/dim]")

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

        # Show startup banner
        if not quiet:
            _render_startup_banner(config)

        # Create agent
        agent = Agent(config=config)

        # Initialize persistence manager
        persistence = ThreadPersistence()

        # Create or resume conversation thread
        thread = None
        message_count = 0
        conversation_messages: list[dict] = []  # Track messages for providers without thread support

        if resume_session:
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
        history_file = config.agent_data_dir / ".agent_history"

        session: PromptSession = PromptSession(
            history=FileHistory(str(history_file)),
            key_bindings=key_bindings,
        )

        # Interactive loop
        while True:
            try:
                # Print status bar before prompt
                if not quiet:
                    status_text = _get_status_bar_text()
                    console.print(f"\n[dim]{status_text}[/dim]")
                    console.print(f"[dim]{'─' * console.width}[/dim]")

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

                if cmd in Commands.EXIT:
                    # Auto-save session before exit
                    await auto_save_session(
                        persistence, thread, message_count, quiet, conversation_messages, console
                    )
                    console.print("\n[dim]Goodbye![/dim]")
                    break

                if cmd in Commands.HELP:
                    show_help(console)
                    continue

                if cmd in Commands.CLEAR:
                    thread, message_count = await handle_clear_command(agent, console)
                    continue

                if cmd in Commands.CONTINUE:
                    result_thread, result_count = await handle_continue_command(
                        agent, persistence, session, console
                    )
                    if result_thread is not None:
                        thread = result_thread
                        message_count = result_count
                    continue

                if cmd in Commands.PURGE:
                    await handle_purge_command(persistence, session, console)
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
                    persistence, thread, message_count, quiet, conversation_messages, console
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


async def _execute_agent_query(agent, user_input, thread, quiet, verbose, console):
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

    # Execute with or without visualization
    if not quiet:
        display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
        try:
            return await execute_with_visualization(agent, user_input, thread, console, display_mode)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow] - Press Ctrl+C again to exit\n")
            raise
    else:
        try:
            return await execute_quiet_mode(agent, user_input, thread)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled[/yellow]\n")
            raise


if __name__ == "__main__":
    app()
