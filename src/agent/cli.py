"""CLI entry point for Agent."""

import asyncio

import typer
from rich.console import Console

from agent.agent import Agent
from agent.config import AgentConfig

app = typer.Typer(help="Agent - AI-powered conversational assistant with extensible tools")
console = Console()


@app.command()
def main(
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a single prompt and exit"),
    check: bool = typer.Option(False, "--check", help="Run health check for configuration"),
    config_flag: bool = typer.Option(False, "--config", help="Show current configuration"),
    version: bool = typer.Option(False, "--version", help="Show version"),
):
    """Agent - Generic chatbot agent with extensible tools.

    Examples:
        # Run health check
        agent --check

        # Show configuration
        agent --config

        # Execute single prompt
        agent -p "Say hello to Alice"

        # Show version
        agent --version
    """
    if version:
        from agent import __version__

        console.print(f"Agent version {__version__}")
        return

    if check:
        run_health_check()
        return

    if config_flag:
        show_configuration()
        return

    if prompt:
        # Single-prompt mode
        asyncio.run(run_single_prompt(prompt))
    else:
        console.print("[yellow]Interactive mode not implemented yet[/yellow]")
        console.print("\nUse: agent -p 'your prompt here'")
        console.print("Or: agent --help for more options")


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
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]✗[/red] Unexpected error: {e}")
        raise typer.Exit(1)


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
        elif config.llm_provider == "azure_ai_foundry":
            console.print(f" • Endpoint: {config.azure_project_endpoint}")

        console.print("\n[bold]Agent Settings:[/bold]")
        console.print(f" • Data Directory: {config.agent_data_dir}")
        if config.agent_session_dir:
            console.print(f" • Session Directory: {config.agent_session_dir}")

        console.print()

    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(1)


async def run_single_prompt(prompt: str):
    """Run single prompt and display response.

    Args:
        prompt: User prompt to execute
    """
    try:
        config = AgentConfig.from_env()
        config.validate()

        console.print(f"\n[bold]User:[/bold] {prompt}\n")
        console.print("[bold]Agent:[/bold] ", end="")

        agent = Agent(config=config)

        async for chunk in agent.run_stream(prompt):
            console.print(chunk, end="")

        console.print("\n")

    except ValueError as e:
        console.print(f"\n[red]Configuration error:[/red] {e}")
        console.print("[yellow]Run 'agent --check' to diagnose issues[/yellow]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
