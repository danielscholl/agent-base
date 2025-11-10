"""Event systems for agent execution transparency.

This module provides two event implementations:

1. **EventEmitter** (PRIMARY - from display.events):
   - Task-safe using asyncio.Queue
   - Used for runtime execution visualization
   - Preferred for new code

2. **EventBus** (LEGACY - maintained for backward compatibility):
   - Simple observer pattern
   - Used in tests and documentation
   - Consider using EventEmitter for new implementations

Recommended Usage:
    >>> from agent.events import get_event_emitter  # Primary API
    >>> emitter = get_event_emitter()
    >>> emitter.emit(LLMRequestEvent())

Legacy Usage (maintained for tests):
    >>> from agent.events import Event, EventType, get_event_bus
    >>> bus = get_event_bus()
    >>> bus.subscribe(my_listener)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Protocol
from uuid import uuid4


class EventType(Enum):
    """Event types for the event bus.

    These events represent key points in the agent execution lifecycle
    that components may want to observe.
    """

    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"


@dataclass
class Event:
    """Base event class.

    Events carry data about what happened in the system. Listeners receive
    events and can react to them without the event emitter needing to know
    about the listeners.

    Attributes:
        type: The type of event (from EventType enum)
        data: Dictionary containing event-specific data
        event_id: Unique identifier for event correlation
        parent_id: ID of parent event for hierarchical display (optional)
    """

    type: EventType
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: str | None = None


class EventListener(Protocol):
    """Protocol for event listeners.

    Any object implementing this protocol can be registered as a listener.
    The listener will receive all events emitted on the bus.
    """

    def handle_event(self, event: Event) -> None:
        """Handle an event.

        Args:
            event: The event to handle
        """
        ...


class EventBus:
    """Singleton event bus for loose coupling.

    The event bus allows components to communicate without direct dependencies.
    Middleware can emit events, and display components can listen to them.

    This implements the Singleton pattern - there's only one event bus instance
    per application.

    Example:
        >>> bus = EventBus()
        >>> # Register a listener
        >>> class MyListener:
        ...     def handle_event(self, event):
        ...         print(f"Received: {event.type}")
        >>> listener = MyListener()
        >>> bus.subscribe(listener)
        >>> # Emit an event
        >>> event = Event(EventType.TOOL_START, {"tool": "hello_world"})
        >>> bus.emit(event)
        Received: EventType.TOOL_START
    """

    _instance: ClassVar["EventBus | None"] = None
    _listeners: list[EventListener]

    def __new__(cls) -> "EventBus":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = []
        return cls._instance

    def subscribe(self, listener: EventListener) -> None:
        """Subscribe a listener to events.

        Args:
            listener: Object implementing EventListener protocol

        Example:
            >>> bus = EventBus()
            >>> bus.subscribe(my_display_component)
        """
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """Unsubscribe a listener from events.

        Args:
            listener: Previously subscribed listener

        Example:
            >>> bus = EventBus()
            >>> bus.unsubscribe(my_display_component)
        """
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(self, event: Event) -> None:
        """Emit an event to all listeners.

        All registered listeners will receive the event via their
        handle_event method.

        Args:
            event: Event to emit

        Example:
            >>> bus = EventBus()
            >>> event = Event(EventType.LLM_REQUEST, {"prompt": "Hello"})
            >>> bus.emit(event)
        """
        for listener in self._listeners:
            listener.handle_event(event)

    def clear(self) -> None:
        """Clear all listeners.

        This is primarily useful for testing to ensure a clean state
        between test runs.

        Example:
            >>> bus = EventBus()
            >>> bus.clear()  # Remove all listeners
        """
        self._listeners.clear()


def get_event_bus() -> EventBus:
    """Get the global event bus instance.

    Returns:
        The singleton EventBus instance

    Example:
        >>> bus = get_event_bus()
        >>> bus.subscribe(my_listener)
    """
    return EventBus()


def get_event_emitter() -> EventBus:
    """Alias for get_event_bus() for consistency with display module naming.

    This provides compatibility with the butler-agent pattern where
    get_event_emitter() is used by middleware and display components.

    Returns:
        The singleton EventBus instance

    Example:
        >>> emitter = get_event_emitter()
        >>> emitter.emit(event)
    """
    return get_event_bus()


# ============================================================================
# Re-exports from display.events (Primary API)
# ============================================================================
# These re-exports provide convenient access to the task-safe EventEmitter
# implementation which is the recommended approach for new code.

try:
    from agent.display.events import (
        EventEmitter,
        ExecutionEvent,
        LLMRequestEvent,
        LLMResponseEvent,
        ToolCompleteEvent,
        ToolErrorEvent,
        ToolStartEvent,
        get_current_tool_event_id,
        set_current_tool_event_id,
    )
    from agent.display.events import (
        get_event_emitter as get_display_event_emitter,
    )

    __all__ = [
        # Legacy EventBus API (backward compatibility)
        "Event",
        "EventType",
        "EventListener",
        "EventBus",
        "get_event_bus",
        "get_event_emitter",
        # Primary EventEmitter API (recommended)
        "EventEmitter",
        "ExecutionEvent",
        "LLMRequestEvent",
        "LLMResponseEvent",
        "ToolStartEvent",
        "ToolCompleteEvent",
        "ToolErrorEvent",
        "get_display_event_emitter",
        "get_current_tool_event_id",
        "set_current_tool_event_id",
    ]
except ImportError:
    # Handle circular import during initialization
    __all__ = [
        "Event",
        "EventType",
        "EventListener",
        "EventBus",
        "get_event_bus",
        "get_event_emitter",
    ]
