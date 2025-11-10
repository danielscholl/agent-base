"""Unit tests for agent.display.events module."""

import asyncio

import pytest

from agent.display.events import (
    ExecutionEvent,
    LLMRequestEvent,
    LLMResponseEvent,
    ToolCompleteEvent,
    ToolErrorEvent,
    ToolStartEvent,
    get_current_tool_event_id,
    get_event_emitter,
    set_current_tool_event_id,
)


@pytest.mark.unit
@pytest.mark.display
class TestExecutionEvent:
    """Tests for ExecutionEvent base class."""

    def test_execution_event_has_event_id(self):
        """Test ExecutionEvent has unique event_id."""
        event1 = ExecutionEvent()
        event2 = ExecutionEvent()

        assert event1.event_id != event2.event_id
        assert isinstance(event1.event_id, str)
        assert len(event1.event_id) == 36  # UUID string length

    def test_execution_event_has_timestamp(self):
        """Test ExecutionEvent has timestamp."""
        event = ExecutionEvent()

        assert event.timestamp is not None

    def test_execution_event_parent_id_is_optional(self):
        """Test ExecutionEvent can have parent_id."""
        parent = ExecutionEvent()
        child = ExecutionEvent(parent_id=parent.event_id)

        assert child.parent_id == parent.event_id


@pytest.mark.unit
@pytest.mark.display
class TestLLMEvents:
    """Tests for LLM event types."""

    def test_llm_request_event_structure(self):
        """Test LLMRequestEvent has correct structure."""
        event = LLMRequestEvent(message_count=5)

        assert event.message_count == 5
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_llm_response_event_structure(self):
        """Test LLMResponseEvent has correct structure."""
        event = LLMResponseEvent(duration=1.23)

        assert event.duration == 1.23
        assert event.event_id is not None


@pytest.mark.unit
@pytest.mark.display
class TestToolEvents:
    """Tests for tool event types."""

    def test_tool_start_event_structure(self):
        """Test ToolStartEvent has correct structure."""
        event = ToolStartEvent(tool_name="hello_world", arguments={"name": "Alice"})

        assert event.tool_name == "hello_world"
        assert event.arguments == {"name": "Alice"}
        assert event.event_id is not None

    def test_tool_complete_event_structure(self):
        """Test ToolCompleteEvent has correct structure."""
        event = ToolCompleteEvent(
            tool_name="hello_world", result_summary="Greeted Alice", duration=0.5
        )

        assert event.tool_name == "hello_world"
        assert event.result_summary == "Greeted Alice"
        assert event.duration == 0.5

    def test_tool_error_event_structure(self):
        """Test ToolErrorEvent has correct structure."""
        event = ToolErrorEvent(
            tool_name="broken_tool", error_message="Something went wrong", duration=0.1
        )

        assert event.tool_name == "broken_tool"
        assert event.error_message == "Something went wrong"
        assert event.duration == 0.1


@pytest.mark.unit
@pytest.mark.display
class TestEventEmitter:
    """Tests for EventEmitter class."""

    @pytest.fixture(autouse=True)
    def reset_emitter(self):
        """Reset event emitter singleton before each test."""
        # Get emitter and clear it
        emitter = get_event_emitter()
        emitter.clear()
        emitter.enable()
        emitter.set_interactive_mode(False, False)
        yield
        # Clean up after test
        emitter.clear()

    def test_event_emitter_is_singleton(self):
        """Test get_event_emitter returns singleton instance."""
        emitter1 = get_event_emitter()
        emitter2 = get_event_emitter()

        assert emitter1 is emitter2

    def test_emit_adds_event_to_queue(self):
        """Test emitting an event adds it to the queue."""
        emitter = get_event_emitter()
        event = ToolStartEvent(tool_name="test")

        emitter.emit(event)

        retrieved = emitter.get_event_nowait()
        assert retrieved is not None
        assert retrieved.tool_name == "test"

    def test_get_event_nowait_returns_none_when_empty(self):
        """Test get_event_nowait returns None when queue is empty."""
        emitter = get_event_emitter()

        event = emitter.get_event_nowait()

        assert event is None

    @pytest.mark.asyncio
    @pytest.mark.timeout(2)
    async def test_get_event_waits_for_event(self):
        """Test get_event waits for an event to be available."""
        emitter = get_event_emitter()
        emitter.clear()  # Extra clear to ensure clean state
        event = ToolStartEvent(tool_name="async_test")

        # Emit event in background
        async def emit_later():
            await asyncio.sleep(0.01)
            emitter.emit(event)

        task = asyncio.create_task(emit_later())

        try:
            # This should block until event is emitted
            retrieved = await asyncio.wait_for(emitter.get_event(), timeout=1.0)

            assert retrieved.tool_name == "async_test"
        finally:
            # Ensure background task completes
            try:
                await asyncio.wait_for(task, timeout=0.5)
            except TimeoutError:
                task.cancel()

    def test_disable_prevents_emission(self):
        """Test disabling emitter prevents event emission."""
        emitter = get_event_emitter()
        emitter.disable()

        event = ToolStartEvent(tool_name="test")
        emitter.emit(event)

        retrieved = emitter.get_event_nowait()
        assert retrieved is None

    def test_enable_allows_emission(self):
        """Test enabling emitter allows event emission."""
        emitter = get_event_emitter()
        emitter.disable()
        emitter.enable()

        event = ToolStartEvent(tool_name="test")
        emitter.emit(event)

        retrieved = emitter.get_event_nowait()
        assert retrieved is not None

    def test_is_enabled_property(self):
        """Test is_enabled property reflects emitter state."""
        emitter = get_event_emitter()

        assert emitter.is_enabled is True

        emitter.disable()
        assert emitter.is_enabled is False

        emitter.enable()
        assert emitter.is_enabled is True

    def test_clear_removes_all_events(self):
        """Test clear removes all pending events from queue."""
        emitter = get_event_emitter()

        # Add multiple events
        emitter.emit(ToolStartEvent(tool_name="test1"))
        emitter.emit(ToolStartEvent(tool_name="test2"))
        emitter.emit(ToolStartEvent(tool_name="test3"))

        emitter.clear()

        # Queue should be empty
        assert emitter.get_event_nowait() is None

    def test_set_interactive_mode(self):
        """Test setting interactive mode flags."""
        emitter = get_event_emitter()

        emitter.set_interactive_mode(True, True)

        assert emitter.is_interactive_mode() is True
        assert emitter.should_show_visualization() is True

    def test_is_interactive_mode_requires_both_flags(self):
        """Test is_interactive_mode requires both flags to be True."""
        emitter = get_event_emitter()

        # Only interactive
        emitter.set_interactive_mode(True, False)
        assert emitter.is_interactive_mode() is False

        # Only visualization
        emitter.set_interactive_mode(False, True)
        assert emitter.is_interactive_mode() is False

        # Both
        emitter.set_interactive_mode(True, True)
        assert emitter.is_interactive_mode() is True

    def test_should_show_visualization_independent_of_interactive(self):
        """Test should_show_visualization works regardless of interactive mode."""
        emitter = get_event_emitter()

        # Visualization in CLI mode
        emitter.set_interactive_mode(False, True)
        assert emitter.should_show_visualization() is True

        # Visualization in interactive mode
        emitter.set_interactive_mode(True, True)
        assert emitter.should_show_visualization() is True

        # No visualization
        emitter.set_interactive_mode(True, False)
        assert emitter.should_show_visualization() is False


@pytest.mark.unit
@pytest.mark.display
class TestToolEventContext:
    """Tests for tool event context tracking."""

    def test_set_and_get_current_tool_event_id(self):
        """Test setting and getting current tool event ID."""
        event_id = "test-event-123"

        set_current_tool_event_id(event_id)
        retrieved = get_current_tool_event_id()

        assert retrieved == event_id

    def test_current_tool_event_id_defaults_to_none(self):
        """Test current tool event ID defaults to None."""
        set_current_tool_event_id(None)
        retrieved = get_current_tool_event_id()

        assert retrieved is None

    def test_current_tool_event_id_can_be_cleared(self):
        """Test current tool event ID can be cleared."""
        set_current_tool_event_id("test-123")
        set_current_tool_event_id(None)

        retrieved = get_current_tool_event_id()
        assert retrieved is None


@pytest.mark.unit
@pytest.mark.display
class TestEventCorrelation:
    """Tests for event correlation functionality."""

    def test_nested_tool_events_with_parent_id(self):
        """Test creating nested tool events with parent_id."""
        parent_event = ToolStartEvent(tool_name="parent_tool")
        child_event = ToolStartEvent(tool_name="child_tool", parent_id=parent_event.event_id)

        assert child_event.parent_id == parent_event.event_id
        assert child_event.event_id != parent_event.event_id

    def test_event_correlation_with_context_var(self):
        """Test event correlation using context variable."""
        parent_event = ToolStartEvent(tool_name="parent")

        # Set parent context
        set_current_tool_event_id(parent_event.event_id)

        # Create child event with context
        child_event = ToolStartEvent(tool_name="child", parent_id=get_current_tool_event_id())

        assert child_event.parent_id == parent_event.event_id

        # Clear context
        set_current_tool_event_id(None)
