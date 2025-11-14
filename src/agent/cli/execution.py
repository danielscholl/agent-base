"""Single prompt execution for Agent CLI.

This module handles:
- Single prompt mode (clean output for scripting)
- Agent creation and configuration
- OpenTelemetry span wrapping
- Display mode handling (quiet, verbose, minimal)
- Performance tracking

Extracted from cli/app.py to improve maintainability.
"""

import logging
import os
import sys
from datetime import datetime

import typer
from rich.console import Console
from rich.prompt import Confirm

from agent.agent import Agent
from agent.cli.constants import ExitCodes
from agent.cli.display import (
    create_execution_context,
    execute_quiet_mode,
    execute_with_visualization,
)
from agent.cli.session import setup_session_logging
from agent.cli.utils import (
    get_console,
    hide_connection_string_if_otel_disabled,
    set_model_span_attributes,
)
from agent.config import AgentConfig
from agent.display import DisplayMode, set_execution_context

logger = logging.getLogger(__name__)


async def _execute_query(
    agent: Agent, prompt: str, quiet: bool, verbose: bool, console: Console
) -> str | None:
    """Execute query with appropriate visualization mode.

    Args:
        agent: Configured agent instance
        prompt: User prompt to process
        quiet: Whether to use quiet mode (no visualization)
        verbose: Whether to show detailed execution tree
        console: Console for output

    Returns:
        Response string from agent execution
    """
    if not quiet:
        display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
        try:
            return await execute_with_visualization(agent, prompt, None, console, display_mode)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]\n")
            raise typer.Exit(ExitCodes.INTERRUPTED)
    else:
        return await execute_quiet_mode(agent, prompt, None)


async def run_single_prompt(
    prompt: str,
    verbose: bool = False,
    quiet: bool = False,
    console: Console | None = None,
) -> None:
    """Run single prompt and display response.

    Args:
        prompt: User prompt to execute
        verbose: Show verbose execution tree
        quiet: Minimal output mode (clean for scripting)
        console: Rich console for output (creates default if None)

    Raises:
        typer.Exit: On configuration errors or execution failures
    """
    if console is None:
        console = get_console()

    try:
        import time

        perf_start = time.perf_counter()

        config = AgentConfig.from_combined()
        config.validate()
        logger.info(f"[PERF] Config loaded: {(time.perf_counter() - perf_start)*1000:.1f}ms")

        # Hide Azure connection string if telemetry disabled (prevents 1-3s exit lag)
        saved_connection_string = hide_connection_string_if_otel_disabled(config)

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
                set_model_span_attributes(span, config)

                # Execute with shared execution logic
                response = await _execute_query(agent, prompt, quiet, verbose, console)
        else:
            # Execute without observability wrapper
            response = await _execute_query(agent, prompt, quiet, verbose, console)

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
