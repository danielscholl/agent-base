"""Unit tests for agent.events module."""

from agent.events import Event, EventBus, EventType, get_event_bus


class MockListener:
    """Mock event listener for testing."""

    def __init__(self):
        self.events_received = []

    def handle_event(self, event: Event) -> None:
        """Handle event by storing it."""
        self.events_received.append(event)


class TestEventBus:
    """Tests for EventBus class."""

    def setup_method(self):
        """Clear event bus before each test."""
        bus = EventBus()
        bus.clear()

    def test_event_bus_is_singleton(self):
        """Test EventBus returns same instance."""
        bus1 = EventBus()
        bus2 = EventBus()

        assert bus1 is bus2

    def test_get_event_bus_returns_singleton(self):
        """Test get_event_bus returns singleton instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2
        assert isinstance(bus1, EventBus)

    def test_subscribe_adds_listener(self):
        """Test subscribing a listener."""
        bus = EventBus()
        listener = MockListener()

        bus.subscribe(listener)

        # Emit event to verify listener is registered
        event = Event(EventType.TOOL_START, {"tool": "test"})
        bus.emit(event)

        assert len(listener.events_received) == 1
        assert listener.events_received[0] == event

    def test_subscribe_same_listener_twice_only_adds_once(self):
        """Test subscribing same listener twice only adds it once."""
        bus = EventBus()
        listener = MockListener()

        bus.subscribe(listener)
        bus.subscribe(listener)

        event = Event(EventType.TOOL_START, {"tool": "test"})
        bus.emit(event)

        # Should only receive event once
        assert len(listener.events_received) == 1

    def test_unsubscribe_removes_listener(self):
        """Test unsubscribing a listener."""
        bus = EventBus()
        listener = MockListener()

        bus.subscribe(listener)
        bus.unsubscribe(listener)

        event = Event(EventType.TOOL_START, {"tool": "test"})
        bus.emit(event)

        # Should not receive any events
        assert len(listener.events_received) == 0

    def test_unsubscribe_non_existent_listener_no_error(self):
        """Test unsubscribing a listener that wasn't subscribed doesn't error."""
        bus = EventBus()
        listener = MockListener()

        # Should not raise error
        bus.unsubscribe(listener)

    def test_emit_sends_event_to_all_listeners(self):
        """Test emit sends event to all subscribed listeners."""
        bus = EventBus()
        listener1 = MockListener()
        listener2 = MockListener()

        bus.subscribe(listener1)
        bus.subscribe(listener2)

        event = Event(EventType.LLM_REQUEST, {"prompt": "test"})
        bus.emit(event)

        assert len(listener1.events_received) == 1
        assert len(listener2.events_received) == 1
        assert listener1.events_received[0] == event
        assert listener2.events_received[0] == event

    def test_emit_with_no_listeners_no_error(self):
        """Test emitting event with no listeners doesn't error."""
        bus = EventBus()

        event = Event(EventType.AGENT_START, {})
        # Should not raise error
        bus.emit(event)

    def test_clear_removes_all_listeners(self):
        """Test clear removes all listeners."""
        bus = EventBus()
        listener1 = MockListener()
        listener2 = MockListener()

        bus.subscribe(listener1)
        bus.subscribe(listener2)
        bus.clear()

        event = Event(EventType.TOOL_COMPLETE, {})
        bus.emit(event)

        assert len(listener1.events_received) == 0
        assert len(listener2.events_received) == 0

    def test_event_types_defined(self):
        """Test all expected event types are defined."""
        expected_types = [
            "LLM_REQUEST",
            "LLM_RESPONSE",
            "TOOL_START",
            "TOOL_COMPLETE",
            "TOOL_ERROR",
            "AGENT_START",
            "AGENT_COMPLETE",
        ]

        for event_type in expected_types:
            assert hasattr(EventType, event_type)

    def test_event_dataclass_structure(self):
        """Test Event dataclass has expected structure."""
        event = Event(type=EventType.TOOL_START, data={"tool": "hello", "args": {"name": "World"}})

        assert event.type == EventType.TOOL_START
        assert event.data["tool"] == "hello"
        assert event.data["args"]["name"] == "World"

    def test_multiple_events_to_same_listener(self):
        """Test listener receives multiple events in order."""
        bus = EventBus()
        listener = MockListener()
        bus.subscribe(listener)

        event1 = Event(EventType.AGENT_START, {})
        event2 = Event(EventType.TOOL_START, {"tool": "test"})
        event3 = Event(EventType.TOOL_COMPLETE, {"result": "success"})

        bus.emit(event1)
        bus.emit(event2)
        bus.emit(event3)

        assert len(listener.events_received) == 3
        assert listener.events_received[0] == event1
        assert listener.events_received[1] == event2
        assert listener.events_received[2] == event3

    def test_listener_can_filter_events(self):
        """Test listener can filter events by type."""

        class FilteringListener:
            def __init__(self):
                self.tool_events = []

            def handle_event(self, event: Event) -> None:
                if event.type in [EventType.TOOL_START, EventType.TOOL_COMPLETE]:
                    self.tool_events.append(event)

        bus = EventBus()
        listener = FilteringListener()
        bus.subscribe(listener)

        bus.emit(Event(EventType.AGENT_START, {}))
        bus.emit(Event(EventType.TOOL_START, {"tool": "test"}))
        bus.emit(Event(EventType.LLM_REQUEST, {}))
        bus.emit(Event(EventType.TOOL_COMPLETE, {"result": "ok"}))

        # Should only have captured the two tool events
        assert len(listener.tool_events) == 2
        assert listener.tool_events[0].type == EventType.TOOL_START
        assert listener.tool_events[1].type == EventType.TOOL_COMPLETE
