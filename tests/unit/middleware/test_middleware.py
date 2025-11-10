"""Unit tests for agent.middleware module."""

import asyncio
from unittest.mock import Mock

import pytest

from agent.middleware import (
    agent_observability_middleware,
    agent_run_logging_middleware,
    create_function_middleware,
    create_middleware,
    logging_function_middleware,
)


@pytest.mark.unit
@pytest.mark.middleware
class TestCreateMiddleware:
    """Tests for middleware factory functions."""

    def test_create_middleware_returns_list(self):
        """Test create_middleware returns list of middleware."""
        middleware = create_middleware()

        assert isinstance(middleware, list)
        assert len(middleware) == 3  # agent_run_logging, agent_observability, logging_function

    def test_create_middleware_has_expected_middleware(self):
        """Test create_middleware includes expected middleware functions."""
        middleware = create_middleware()

        # Check all middleware are present (framework auto-categorizes by signature)
        assert agent_run_logging_middleware in middleware
        assert agent_observability_middleware in middleware
        assert logging_function_middleware in middleware

    def test_create_function_middleware_returns_list(self):
        """Test create_function_middleware returns list (backward compatibility)."""
        function_mw = create_function_middleware()

        assert isinstance(function_mw, list)
        assert len(function_mw) == 1
        assert logging_function_middleware in function_mw


@pytest.mark.unit
@pytest.mark.middleware
class TestAgentRunLoggingMiddleware:
    """Tests for agent_run_logging_middleware."""

    @pytest.fixture(autouse=True)
    def reset_emitter(self):
        """Reset event emitter before each test."""
        from agent.display.events import get_event_emitter

        emitter = get_event_emitter()
        emitter.clear()
        emitter.enable()
        yield
        emitter.clear()

    @pytest.mark.asyncio
    async def test_middleware_calls_next(self):
        """Test middleware calls next in chain."""
        # Create mock context and next
        context = Mock()
        context.messages = []
        next_called = False

        async def mock_next(ctx):
            nonlocal next_called
            next_called = True

        # Execute middleware
        await agent_run_logging_middleware(context, mock_next)

        assert next_called is True

    @pytest.mark.asyncio
    async def test_middleware_emits_llm_request_event_when_visualization_enabled(self):
        """Test middleware emits LLM request event when visualization enabled."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.messages = ["msg1", "msg2", "msg3"]

        async def mock_next(ctx):
            pass

        # Execute middleware
        await agent_run_logging_middleware(context, mock_next)

        # Check event was emitted
        emitter = get_event_emitter()
        event = emitter.get_event_nowait()

        assert event is not None
        from agent.display.events import LLMRequestEvent

        assert isinstance(event, LLMRequestEvent)
        assert event.message_count == 3

    @pytest.mark.asyncio
    async def test_middleware_emits_llm_response_event_on_success(self):
        """Test middleware emits LLM response event on successful completion."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import LLMResponseEvent, get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.messages = []

        async def mock_next(ctx):
            await asyncio.sleep(0.01)  # Simulate some work

        # Execute middleware
        await agent_run_logging_middleware(context, mock_next)

        # Check events
        emitter = get_event_emitter()
        request_event = emitter.get_event_nowait()
        response_event = emitter.get_event_nowait()

        assert response_event is not None
        assert isinstance(response_event, LLMResponseEvent)
        assert response_event.duration > 0
        # Should use same event_id
        assert response_event.event_id == request_event.event_id

    @pytest.mark.asyncio
    async def test_middleware_does_not_emit_when_visualization_disabled(self):
        """Test middleware doesn't emit events when visualization disabled."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import get_event_emitter

        # Disable visualization
        ctx = ExecutionContext(show_visualization=False)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.messages = []

        async def mock_next(ctx):
            pass

        # Execute middleware
        await agent_run_logging_middleware(context, mock_next)

        # Check no events emitted
        emitter = get_event_emitter()
        event = emitter.get_event_nowait()

        assert event is None

    @pytest.mark.asyncio
    async def test_middleware_propagates_exceptions(self):
        """Test middleware propagates exceptions from next middleware."""
        context = Mock()
        context.messages = []

        async def mock_next_that_fails(ctx):
            raise ValueError("Test error")

        # Should raise the exception
        with pytest.raises(ValueError, match="Test error"):
            await agent_run_logging_middleware(context, mock_next_that_fails)


@pytest.mark.unit
@pytest.mark.middleware
class TestAgentObservabilityMiddleware:
    """Tests for agent_observability_middleware."""

    @pytest.mark.asyncio
    async def test_middleware_calls_next(self):
        """Test middleware calls next in chain."""
        context = Mock()
        next_called = False

        async def mock_next(ctx):
            nonlocal next_called
            next_called = True

        await agent_observability_middleware(context, mock_next)

        assert next_called is True

    @pytest.mark.asyncio
    async def test_middleware_logs_execution_time(self, caplog):
        """Test middleware logs execution duration."""
        import logging

        caplog.set_level(logging.INFO)

        context = Mock()

        async def mock_next(ctx):
            await asyncio.sleep(0.01)

        await agent_observability_middleware(context, mock_next)

        # Check log message
        assert any("Agent execution took" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_middleware_logs_even_on_exception(self, caplog):
        """Test middleware logs duration even if next raises exception."""
        import logging

        caplog.set_level(logging.INFO)

        context = Mock()

        async def mock_next_that_fails(ctx):
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        # Should raise but still log
        with pytest.raises(ValueError):
            await agent_observability_middleware(context, mock_next_that_fails)

        # Check log message still appeared
        assert any("Agent execution took" in record.message for record in caplog.records)


@pytest.mark.unit
@pytest.mark.middleware
class TestLoggingFunctionMiddleware:
    """Tests for logging_function_middleware."""

    @pytest.fixture(autouse=True)
    def reset_emitter(self):
        """Reset event emitter before each test."""
        from agent.display.events import get_event_emitter, set_current_tool_event_id

        emitter = get_event_emitter()
        emitter.clear()
        emitter.enable()
        set_current_tool_event_id(None)
        yield
        emitter.clear()
        set_current_tool_event_id(None)

    @pytest.mark.asyncio
    async def test_middleware_calls_next(self):
        """Test middleware calls next in chain."""
        # Create mock context
        context = Mock()
        context.function = Mock()
        context.function.name = "test_tool"
        context.arguments = {}

        next_called = False

        async def mock_next(ctx):
            nonlocal next_called
            next_called = True
            return "result"

        result = await logging_function_middleware(context, mock_next)

        assert next_called is True
        assert result == "result"

    @pytest.mark.asyncio
    async def test_middleware_emits_tool_start_event(self):
        """Test middleware emits ToolStartEvent when visualization enabled."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import ToolStartEvent, get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.function = Mock()
        context.function.name = "hello_world"
        context.arguments = {"name": "Alice"}

        async def mock_next(ctx):
            return "Hello, Alice!"

        await logging_function_middleware(context, mock_next)

        # Check event
        emitter = get_event_emitter()
        event = emitter.get_event_nowait()

        assert event is not None
        assert isinstance(event, ToolStartEvent)
        assert event.tool_name == "hello_world"
        assert event.arguments == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_middleware_emits_tool_complete_event(self):
        """Test middleware emits ToolCompleteEvent on success."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import ToolCompleteEvent, get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.function = Mock()
        context.function.name = "test_tool"
        context.arguments = {}

        async def mock_next(ctx):
            await asyncio.sleep(0.01)
            return {"message": "Success"}

        await logging_function_middleware(context, mock_next)

        # Check events
        emitter = get_event_emitter()
        start_event = emitter.get_event_nowait()
        complete_event = emitter.get_event_nowait()

        assert complete_event is not None
        assert isinstance(complete_event, ToolCompleteEvent)
        assert complete_event.tool_name == "test_tool"
        assert complete_event.result_summary == "Success"
        assert complete_event.duration > 0
        # Should use same event_id
        assert complete_event.event_id == start_event.event_id

    @pytest.mark.asyncio
    async def test_middleware_emits_tool_error_event_on_failure(self):
        """Test middleware emits ToolErrorEvent on exception."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import ToolErrorEvent, get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.function = Mock()
        context.function.name = "failing_tool"
        context.arguments = {}

        async def mock_next_that_fails(ctx):
            await asyncio.sleep(0.01)
            raise ValueError("Tool failed")

        # Should raise
        with pytest.raises(ValueError, match="Tool failed"):
            await logging_function_middleware(context, mock_next_that_fails)

        # Check events
        emitter = get_event_emitter()
        start_event = emitter.get_event_nowait()
        error_event = emitter.get_event_nowait()

        assert error_event is not None
        assert isinstance(error_event, ToolErrorEvent)
        assert error_event.tool_name == "failing_tool"
        assert "Tool failed" in error_event.error_message
        assert error_event.duration > 0
        # Should use same event_id
        assert error_event.event_id == start_event.event_id

    @pytest.mark.asyncio
    async def test_middleware_sanitizes_sensitive_arguments(self):
        """Test middleware removes sensitive data from arguments."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import ToolStartEvent, get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context with sensitive data
        context = Mock()
        context.function = Mock()
        context.function.name = "secure_tool"
        context.arguments = {
            "username": "alice",
            "password": "secret123",
            "api_key": "key123",
            "normal_arg": "value",
        }

        async def mock_next(ctx):
            return "result"

        await logging_function_middleware(context, mock_next)

        # Check event has sanitized arguments
        emitter = get_event_emitter()
        event = emitter.get_event_nowait()

        assert isinstance(event, ToolStartEvent)
        assert "username" in event.arguments
        assert "normal_arg" in event.arguments
        # Sensitive fields should be removed
        assert "password" not in event.arguments
        assert "api_key" not in event.arguments

    @pytest.mark.asyncio
    async def test_middleware_sets_and_clears_tool_context(self):
        """Test middleware sets and clears tool event context."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import get_current_tool_event_id

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Create mock context
        context = Mock()
        context.function = Mock()
        context.function.name = "test_tool"
        context.arguments = {}

        context_during_execution = None

        async def mock_next(ctx):
            nonlocal context_during_execution
            context_during_execution = get_current_tool_event_id()
            return "result"

        # Before execution, no context
        assert get_current_tool_event_id() is None

        await logging_function_middleware(context, mock_next)

        # During execution, context was set
        assert context_during_execution is not None

        # After execution, context cleared
        assert get_current_tool_event_id() is None

    @pytest.mark.asyncio
    async def test_middleware_supports_nested_tools(self):
        """Test middleware supports nested tool calls with parent_id."""
        from agent.display import ExecutionContext, set_execution_context
        from agent.display.events import ToolStartEvent, get_event_emitter

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        # Parent tool context
        parent_context = Mock()
        parent_context.function = Mock()
        parent_context.function.name = "parent_tool"
        parent_context.arguments = {}

        # Child tool context
        child_context = Mock()
        child_context.function = Mock()
        child_context.function.name = "child_tool"
        child_context.arguments = {}


        async def parent_next(ctx):
            # Call child tool during parent execution
            await logging_function_middleware(child_context, child_next)

        async def child_next(ctx):
            return "child result"

        # Execute parent tool (which calls child)
        await logging_function_middleware(parent_context, parent_next)

        # Check events
        emitter = get_event_emitter()
        parent_start = emitter.get_event_nowait()
        child_start = emitter.get_event_nowait()

        assert isinstance(parent_start, ToolStartEvent)
        assert parent_start.tool_name == "parent_tool"
        assert parent_start.parent_id is None

        assert isinstance(child_start, ToolStartEvent)
        assert child_start.tool_name == "child_tool"
        # Child should have parent_id set
        assert child_start.parent_id == parent_start.event_id
