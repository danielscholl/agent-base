"""Unit tests for agent.display.tree module."""

import asyncio

import pytest
from rich.console import Console

from agent.display.context import DisplayMode
from agent.display.events import (
    LLMRequestEvent,
    LLMResponseEvent,
    ToolCompleteEvent,
    ToolErrorEvent,
    ToolStartEvent,
    get_event_emitter,
)
from agent.display.tree import ExecutionPhase, ExecutionTreeDisplay, TreeNode


@pytest.mark.unit
@pytest.mark.display
class TestTreeNode:
    """Tests for TreeNode class."""

    def test_tree_node_initialization(self):
        """Test TreeNode initializes with correct defaults."""
        node = TreeNode(event_id="test-123", label="Test Node")

        assert node.event_id == "test-123"
        assert node.label == "Test Node"
        assert node.status == "in_progress"
        assert node.children == []
        assert node.metadata == {}
        assert node.start_time is not None
        assert node.end_time is None

    def test_tree_node_add_child(self):
        """Test adding child nodes."""
        parent = TreeNode("parent-1", "Parent")
        child1 = TreeNode("child-1", "Child 1")
        child2 = TreeNode("child-2", "Child 2")

        parent.add_child(child1)
        parent.add_child(child2)

        assert len(parent.children) == 2
        assert parent.children[0] == child1
        assert parent.children[1] == child2

    def test_tree_node_complete(self):
        """Test marking node as completed."""
        node = TreeNode("test-1", "Test")

        node.complete(summary="Success", duration=1.5)

        assert node.status == "completed"
        assert node.end_time is not None
        assert node.metadata["summary"] == "Success"
        assert node.metadata["duration"] == 1.5

    def test_tree_node_mark_error(self):
        """Test marking node as error."""
        node = TreeNode("test-1", "Test")

        node.mark_error(error_message="Failed", duration=0.5)

        assert node.status == "error"
        assert node.end_time is not None
        assert node.metadata["error"] == "Failed"
        assert node.metadata["duration"] == 0.5


@pytest.mark.unit
@pytest.mark.display
class TestExecutionPhase:
    """Tests for ExecutionPhase class."""

    def test_execution_phase_initialization(self):
        """Test ExecutionPhase initializes correctly."""
        phase = ExecutionPhase(phase_number=1)

        assert phase.phase_number == 1
        assert phase.llm_node is None
        assert phase.tool_nodes == []
        assert phase.status == "in_progress"
        assert phase.start_time is not None
        assert phase.end_time is None

    def test_execution_phase_add_llm_node(self):
        """Test adding LLM node to phase."""
        phase = ExecutionPhase(1)
        node = TreeNode("llm-1", "Thinking")

        phase.add_llm_node(node)

        assert phase.llm_node == node

    def test_execution_phase_add_tool_nodes(self):
        """Test adding tool nodes to phase."""
        phase = ExecutionPhase(1)
        tool1 = TreeNode("tool-1", "Tool 1")
        tool2 = TreeNode("tool-2", "Tool 2")

        phase.add_tool_node(tool1)
        phase.add_tool_node(tool2)

        assert len(phase.tool_nodes) == 2
        assert phase.tool_nodes[0] == tool1
        assert phase.tool_nodes[1] == tool2

    def test_execution_phase_complete(self):
        """Test marking phase as completed."""
        phase = ExecutionPhase(1)

        phase.complete()

        assert phase.status == "completed"
        assert phase.end_time is not None

    def test_execution_phase_duration(self):
        """Test phase duration calculation."""
        import time

        phase = ExecutionPhase(1)

        # Duration should be >= 0 even if not completed
        duration = phase.duration
        assert duration >= 0

        # Small sleep to ensure measurable duration
        time.sleep(0.001)
        phase.complete()
        assert phase.duration >= 0

    def test_execution_phase_has_nodes(self):
        """Test has_nodes property."""
        phase = ExecutionPhase(1)

        # Initially no nodes
        assert phase.has_nodes is False

        # Add LLM node
        phase.add_llm_node(TreeNode("llm-1", "Thinking"))
        assert phase.has_nodes is True

        # New phase with tool node
        phase2 = ExecutionPhase(2)
        phase2.add_tool_node(TreeNode("tool-1", "Tool"))
        assert phase2.has_nodes is True


@pytest.mark.unit
@pytest.mark.display
class TestExecutionTreeDisplay:
    """Tests for ExecutionTreeDisplay class."""

    @pytest.fixture(autouse=True)
    async def reset_emitter(self):
        """Reset event emitter before each test."""
        emitter = get_event_emitter()
        emitter.clear()
        emitter.enable()

        yield

        # Cleanup after test
        emitter.clear()

        # Cancel any tasks created during test
        for task in asyncio.all_tasks():
            if not task.done() and task != asyncio.current_task():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    # Expected when cancelling tasks
                    pass

    def test_execution_tree_display_initialization(self):
        """Test ExecutionTreeDisplay initializes correctly."""
        display = ExecutionTreeDisplay()

        assert display.console is not None
        assert display.display_mode == DisplayMode.MINIMAL
        assert display.show_completion_summary is True
        assert display._running is False
        assert display._phases == []

    def test_execution_tree_display_with_custom_console(self):
        """Test creating display with custom console."""
        custom_console = Console()
        display = ExecutionTreeDisplay(console=custom_console)

        assert display.console is custom_console

    def test_execution_tree_display_with_verbose_mode(self):
        """Test creating display with VERBOSE mode."""
        display = ExecutionTreeDisplay(display_mode=DisplayMode.VERBOSE)

        assert display.display_mode == DisplayMode.VERBOSE

    @pytest.mark.asyncio
    async def test_handle_llm_request_event(self):
        """Test handling LLM request event creates phase."""
        display = ExecutionTreeDisplay()
        event = LLMRequestEvent(message_count=3)

        await display._handle_event(event)

        assert len(display._phases) == 1
        assert display._current_phase is not None
        assert display._current_phase.phase_number == 1
        assert display._current_phase.llm_node is not None
        assert display._current_phase.llm_node.metadata["message_count"] == 3

    @pytest.mark.asyncio
    async def test_handle_llm_response_event(self):
        """Test handling LLM response event completes node."""
        display = ExecutionTreeDisplay()

        # Create request first
        request_event = LLMRequestEvent(message_count=2)
        await display._handle_event(request_event)

        # Then response
        response_event = LLMResponseEvent(event_id=request_event.event_id, duration=1.5)
        await display._handle_event(response_event)

        # Check node was completed
        node = display._node_map[request_event.event_id]
        assert node.status == "completed"
        assert node.metadata["duration"] == 1.5

    @pytest.mark.asyncio
    async def test_handle_tool_start_event(self):
        """Test handling tool start event creates tool node."""
        display = ExecutionTreeDisplay()

        # Create phase first
        llm_event = LLMRequestEvent(message_count=1)
        await display._handle_event(llm_event)

        # Create tool event
        tool_event = ToolStartEvent(tool_name="hello_world", arguments={"name": "Alice"})
        await display._handle_event(tool_event)

        # Check tool node was added to phase
        assert len(display._current_phase.tool_nodes) == 1
        tool_node = display._current_phase.tool_nodes[0]
        assert "hello_world" in tool_node.label
        assert "Alice" in tool_node.label

    @pytest.mark.asyncio
    async def test_handle_tool_complete_event(self):
        """Test handling tool complete event."""
        display = ExecutionTreeDisplay()

        # Create phase and tool
        llm_event = LLMRequestEvent(message_count=1)
        await display._handle_event(llm_event)

        tool_start = ToolStartEvent(tool_name="test_tool")
        await display._handle_event(tool_start)

        # Complete tool
        tool_complete = ToolCompleteEvent(
            event_id=tool_start.event_id,
            tool_name="test_tool",
            result_summary="Success",
            duration=0.5,
        )
        await display._handle_event(tool_complete)

        # Check node was completed
        node = display._node_map[tool_start.event_id]
        assert node.status == "completed"
        assert node.metadata["summary"] == "Success"
        assert node.metadata["duration"] == 0.5

    @pytest.mark.asyncio
    async def test_handle_tool_error_event(self):
        """Test handling tool error event."""
        display = ExecutionTreeDisplay()

        # Create phase and tool
        llm_event = LLMRequestEvent(message_count=1)
        await display._handle_event(llm_event)

        tool_start = ToolStartEvent(tool_name="failing_tool")
        await display._handle_event(tool_start)

        # Error on tool
        tool_error = ToolErrorEvent(
            event_id=tool_start.event_id,
            tool_name="failing_tool",
            error_message="Tool failed",
            duration=0.2,
        )
        await display._handle_event(tool_error)

        # Check node has error
        node = display._node_map[tool_start.event_id]
        assert node.status == "error"
        assert node.metadata["error"] == "Tool failed"
        assert node.metadata["duration"] == 0.2

    @pytest.mark.asyncio
    async def test_handle_nested_tool_events(self):
        """Test handling nested tool calls with parent_id."""
        display = ExecutionTreeDisplay()

        # Create phase
        llm_event = LLMRequestEvent(message_count=1)
        await display._handle_event(llm_event)

        # Parent tool
        parent_tool = ToolStartEvent(tool_name="parent_tool")
        await display._handle_event(parent_tool)

        # Child tool with parent_id
        child_tool = ToolStartEvent(tool_name="child_tool", parent_id=parent_tool.event_id)
        await display._handle_event(child_tool)

        # Check child is nested under parent
        parent_node = display._node_map[parent_tool.event_id]
        assert len(parent_node.children) == 1
        assert parent_node.children[0].event_id == child_tool.event_id

    @pytest.mark.asyncio
    async def test_multiple_phases_created(self):
        """Test multiple LLM requests create multiple phases."""
        display = ExecutionTreeDisplay()

        # First phase
        llm1 = LLMRequestEvent(message_count=1)
        await display._handle_event(llm1)

        # Complete first phase by starting second
        llm2 = LLMRequestEvent(message_count=2)
        await display._handle_event(llm2)

        # Check two phases exist
        assert len(display._phases) == 2
        assert display._phases[0].status == "completed"
        assert display._phases[1].status == "in_progress"
        assert display._current_phase == display._phases[1]

    @pytest.mark.asyncio
    async def test_start_initializes_display(self):
        """Test start() initializes display state."""
        display = ExecutionTreeDisplay()

        try:
            await display.start()

            assert display._running is True
            assert display._live is not None
            assert display._task is not None
            assert display._phases == []
        finally:
            # Ensure cleanup even if assertions fail
            await display.stop()

    @pytest.mark.asyncio
    async def test_stop_cleans_up_display(self):
        """Test stop() cleans up display resources."""
        display = ExecutionTreeDisplay()

        try:
            await display.start()
            await display.stop()

            assert display._running is False
            # Task should be cancelled
            assert display._task is not None
        finally:
            # Extra safety: ensure stopped even if test fails
            if display._running:
                await display.stop()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test using display as async context manager."""
        display = ExecutionTreeDisplay()

        async with display:
            assert display._running is True

        assert display._running is False

    @pytest.mark.asyncio
    async def test_process_events_from_emitter(self):
        """Test event processing from emitter queue."""
        from agent.display.context import ExecutionContext, set_execution_context

        # Enable visualization
        ctx = ExecutionContext(show_visualization=True)
        set_execution_context(ctx)

        display = ExecutionTreeDisplay()

        try:
            await display.start()

            # Emit events
            emitter = get_event_emitter()
            llm_event = LLMRequestEvent(message_count=5)
            emitter.emit(llm_event)

            # Give time for event processing
            await asyncio.sleep(0.2)

            # Check event was processed
            assert len(display._phases) == 1
            assert display._current_phase is not None
        finally:
            # Ensure cleanup even if assertions fail
            await display.stop()

    @pytest.mark.asyncio
    async def test_display_with_minimal_mode(self):
        """Test display behavior in MINIMAL mode."""
        display = ExecutionTreeDisplay(display_mode=DisplayMode.MINIMAL)

        assert display.display_mode == DisplayMode.MINIMAL

        # Render should work without errors
        renderable = display._render_phases()
        assert renderable is not None

    @pytest.mark.asyncio
    async def test_display_with_verbose_mode(self):
        """Test display behavior in VERBOSE mode."""
        display = ExecutionTreeDisplay(display_mode=DisplayMode.VERBOSE)

        assert display.display_mode == DisplayMode.VERBOSE

        # Render should work without errors
        renderable = display._render_phases()
        assert renderable is not None
