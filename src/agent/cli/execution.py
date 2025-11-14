"""Single prompt execution and agent query handling.

This module handles:
- Single prompt mode (clean output for scripting)
- Agent query execution with visualization
- OpenTelemetry span wrapping
- Display mode handling (quiet, verbose, minimal)

Extracted from cli/app.py to improve maintainability.
"""

import logging
from typing import Any

from rich.console import Console

from agent.agent import Agent

logger = logging.getLogger(__name__)


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
    # TODO: Extract from cli/app.py lines 845-984
    raise NotImplementedError("Not yet extracted from cli/app.py")


async def _execute_agent_query(
    agent: Agent,
    user_input: str,
    thread: Any,
    quiet: bool,
    verbose: bool,
    console: Console,
) -> str:
    """Execute agent query with appropriate visualization.

    Handles:
    - Execution context setup
    - OpenTelemetry span wrapping (if enabled)
    - Display mode selection (quiet, verbose, minimal)
    - Keyboard interrupt handling

    Args:
        agent: Agent instance
        user_input: User's input
        thread: Conversation thread
        quiet: Quiet mode flag
        verbose: Verbose mode flag
        console: Console for output

    Returns:
        Agent response string

    Raises:
        KeyboardInterrupt: When user cancels operation
    """
    # TODO: Extract from cli/app.py lines 1342-1427
    raise NotImplementedError("Not yet extracted from cli/app.py")
