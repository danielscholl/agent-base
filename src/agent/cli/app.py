"""CLI entry point for Agent."""

import asyncio
import logging
import os
import platform

import typer

from agent import __version__
from agent.cli.commands import (
    handle_memory_command,
    handle_telemetry_command,
)
from agent.cli.constants import ExitCodes
from agent.cli.execution import run_single_prompt
from agent.cli.health import run_health_check
from agent.cli.interactive import run_chat_mode
from agent.cli.session import get_last_session
from agent.cli.utils import get_console
from agent.config import AgentConfig

app = typer.Typer(help="Agent - Conversational Assistant")

# Use shared utility for Windows console encoding setup
console = get_console()

logger = logging.getLogger(__name__)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a single prompt and exit"),
    check: bool = typer.Option(False, "--check", help="Show configuration and connectivity status"),
    tools: bool = typer.Option(False, "--tools", help="Show tool configuration"),
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
        agent --tools                               # Show tool configuration
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
        run_health_check(console)
        return

    if tools:
        from agent.cli.health import show_tool_configuration

        show_tool_configuration(console)
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
        asyncio.run(run_single_prompt(prompt, verbose=verbose, quiet=quiet_mode, console=console))
    else:
        # Interactive chat mode
        # Handle --continue flag: resume last session
        resume_session = None
        if resume:
            resume_session = get_last_session()
            if not resume_session:
                console.print("[yellow]No previous session found. Starting new session.[/yellow]\n")

        asyncio.run(run_chat_mode(quiet=False, verbose=verbose, resume_session=resume_session))


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


# Skill command group
skill_app = typer.Typer(help="Manage agent skills (bundled and plugins)")
app.add_typer(skill_app, name="skill")


@skill_app.callback(invoke_without_command=True)
def skill_callback(ctx: typer.Context) -> None:
    """Skill command callback - shows help if no subcommand given."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


@skill_app.command("show")
def skill_show_command() -> None:
    """Show all bundled and installed plugin skills with status."""
    from agent.cli.skill_commands import show_skills

    show_skills()


@skill_app.command("install")
def skill_install_command(
    git_url: str = typer.Argument(None, help="Git repository URL (prompts if not provided)"),
    name: str = typer.Option(None, "--name", help="Override skill name"),
    branch: str = typer.Option("main", "--branch", help="Git branch to use"),
) -> None:
    """Install plugin skill(s) from a git repository.

    Supports single-skill and monorepo structures.

    Examples:
        agent skill install                                          # Interactive
        agent skill install https://github.com/user/my-skill.git     # Direct
        agent skill install https://github.com/user/my-skill.git --branch develop
    """
    from agent.cli.skill_commands import install_skill

    install_skill(git_url, name, branch)


@skill_app.command("manage")
def skill_manage_command() -> None:
    """Manage skills interactively (enable/disable/update/remove).

    Shows all installed skills and allows:
    - Toggle enable/disable
    - Update plugin skills
    - Remove plugin skills

    Example:
        agent skill manage
    """
    from agent.cli.skill_commands import manage_skills

    manage_skills()


if __name__ == "__main__":
    app()
