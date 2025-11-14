"""Integration tests for middleware and display system integration.

Tests verify that components work together correctly, focusing on
integration points rather than full end-to-end LLM execution.
"""

import asyncio

import pytest

# Module-level marker for all tests in this file
pytestmark = [pytest.mark.integration, pytest.mark.middleware]
from rich.console import Console

from agent.agent import Agent
from agent.config import AgentConfig
from agent.display import (
    DisplayMode,
    ExecutionContext,
    ExecutionTreeDisplay,
    get_event_emitter,
    set_execution_context,
)
from agent.display.events import (
    LLMRequestEvent,
    ToolCompleteEvent,
    ToolStartEvent,
)


@pytest.fixture
def agent_with_middleware(mock_config: AgentConfig, mock_chat_client) -> Agent:
    """Create agent with middleware enabled."""
    return Agent(config=mock_config, chat_client=mock_chat_client)


@pytest.mark.asyncio
async def test_event_emitter_integration():
    """Test that event emitter integrates properly with display context."""
    # Setup visualization context
    ctx = ExecutionContext(
        is_interactive=False,
        show_visualization=True,
        display_mode=DisplayMode.MINIMAL,
    )
    set_execution_context(ctx)

    # Clear event queue
    emitter = get_event_emitter()
    emitter.clear()

    # Manually emit test events to verify integration
    test_event = LLMRequestEvent(message_count=5)
    emitter.emit(test_event)

    # Verify event can be retrieved
    retrieved_event = emitter.get_event_nowait()
    assert retrieved_event is not None, "Should retrieve emitted event"
    assert isinstance(retrieved_event, LLMRequestEvent), "Should be LLMRequestEvent"
    assert retrieved_event.message_count == 5, "Should preserve event data"


@pytest.mark.asyncio
async def test_execution_context_propagation(agent_with_middleware: Agent):
    """Test that execution context is properly set and accessible."""
    # Set context with visualization enabled
    ctx = ExecutionContext(
        is_interactive=True,
        show_visualization=True,
        display_mode=DisplayMode.VERBOSE,
    )
    set_execution_context(ctx)

    # Verify context is accessible through emitter
    emitter = get_event_emitter()
    assert emitter.is_interactive_mode() is True, "Should be in interactive mode"
    assert emitter.should_show_visualization() is True, "Should show visualization"

    # Clear context
    set_execution_context(None)
    assert emitter.is_interactive_mode() is False, "Should not be in interactive mode"
    assert emitter.should_show_visualization() is False, "Should not show visualization"


@pytest.mark.asyncio
async def test_display_tree_integration():
    """Test that ExecutionTreeDisplay integrates with event emitter."""
    # Create display with test console
    import io

    # Use StringIO to avoid encoding issues on Windows
    null_stream = io.StringIO()
    console = Console(file=null_stream, force_terminal=False, legacy_windows=False)
    display = ExecutionTreeDisplay(
        console=console,
        display_mode=DisplayMode.MINIMAL,
        show_completion_summary=False,
    )

    # Setup context
    ctx = ExecutionContext(
        is_interactive=False,
        show_visualization=True,
        display_mode=DisplayMode.MINIMAL,
    )
    set_execution_context(ctx)

    # Start display
    await display.start()

    # Emit some test events
    emitter = get_event_emitter()
    emitter.emit(LLMRequestEvent(message_count=3))
    emitter.emit(ToolStartEvent(tool_name="test_tool", arguments={}))
    emitter.emit(ToolCompleteEvent(tool_name="test_tool", result_summary="Done", duration=0.5))

    # Give display time to process events
    await asyncio.sleep(0.3)

    # Stop display
    await display.stop()

    # Verify display started and stopped without errors
    assert display._running is False, "Display should be stopped"


@pytest.mark.asyncio
async def test_middleware_config_integration(agent_with_middleware: Agent):
    """Test that agent is created with middleware configuration."""
    # Verify agent has middleware
    assert hasattr(agent_with_middleware, "middleware"), "Agent should have middleware"
    assert isinstance(agent_with_middleware.middleware, list), "Middleware should be list"

    # Verify middleware contains expected functions
    # Framework auto-categorizes by signature, so we store as list
    assert len(agent_with_middleware.middleware) > 0, "Should have middleware functions"

    # Verify we have both agent and function level middleware
    # (agent-level takes AgentRunContext, function-level takes FunctionInvocationContext)
    middleware_names = [m.__name__ for m in agent_with_middleware.middleware]
    assert any("agent" in name for name in middleware_names), "Should have agent middleware"
    assert any("function" in name for name in middleware_names), "Should have function middleware"


@pytest.mark.asyncio
async def test_concurrent_display_contexts():
    """Test that multiple concurrent contexts can coexist."""
    # Create multiple contexts
    contexts = [
        ExecutionContext(
            is_interactive=True, show_visualization=True, display_mode=DisplayMode.VERBOSE
        ),
        ExecutionContext(
            is_interactive=False, show_visualization=True, display_mode=DisplayMode.MINIMAL
        ),
        ExecutionContext(
            is_interactive=False, show_visualization=False, display_mode=DisplayMode.MINIMAL
        ),
    ]

    # Set each context and verify it takes effect
    for ctx in contexts:
        set_execution_context(ctx)
        emitter = get_event_emitter()

        assert emitter.is_interactive_mode() == (
            ctx.is_interactive and ctx.show_visualization
        ), "Interactive mode should match context"
        assert (
            emitter.should_show_visualization() == ctx.show_visualization
        ), "Visualization should match context"
