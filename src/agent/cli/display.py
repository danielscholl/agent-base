"""Display helpers for CLI."""

import asyncio
from typing import Any

from rich.console import Console

from agent.agent import Agent
from agent.display import DisplayMode, ExecutionContext, ExecutionTreeDisplay


def create_execution_context(verbose: bool, quiet: bool, is_interactive: bool) -> ExecutionContext:
    """Create execution context for visualization.

    Args:
        verbose: Enable verbose output mode
        quiet: Enable quiet output mode
        is_interactive: Whether in interactive mode

    Returns:
        Configured ExecutionContext
    """
    display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
    return ExecutionContext(
        is_interactive=is_interactive,
        show_visualization=not quiet,
        display_mode=display_mode,
    )


async def execute_with_visualization(
    agent: Agent,
    prompt: str,
    thread: Any | None,
    console: Console,
    display_mode: DisplayMode,
) -> str:
    """Execute agent with display visualization (cancellable with Ctrl+C or ESC).

    Args:
        agent: Agent instance
        prompt: User prompt
        thread: Optional conversation thread
        console: Console for output
        display_mode: Display mode (MINIMAL or VERBOSE)

    Returns:
        Agent response

    Raises:
        KeyboardInterrupt: If user interrupts execution (Ctrl+C)
        asyncio.CancelledError: If task is cancelled (ESC or Ctrl+C)
    """
    execution_display = ExecutionTreeDisplay(
        console=console,
        display_mode=display_mode,
        show_completion_summary=True,
    )

    await execution_display.start()

    try:
        # Run agent as a cancellable task (allows interruption)
        task = asyncio.create_task(agent.run(prompt, thread=thread))

        # Wait for completion (can be cancelled by signal handler)
        response = await task

        # Stop display (shows completion summary)
        await execution_display.stop()

        return response

    except (KeyboardInterrupt, asyncio.CancelledError):
        # User interrupted - stop display cleanly
        await execution_display.stop()
        # Re-raise as KeyboardInterrupt for consistent handling
        raise KeyboardInterrupt()


async def execute_quiet_mode(agent: Agent, prompt: str, thread: Any | None) -> str:
    """Execute agent in quiet mode (no visualization).

    Args:
        agent: Agent instance
        prompt: User prompt
        thread: Optional conversation thread

    Returns:
        Agent response
    """
    return await agent.run(prompt, thread=thread)
