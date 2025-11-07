"""Event bus for loose coupling between agent components.

This module provides an event bus implementation using the observer pattern.
It allows middleware to emit events that display components can listen to,
without creating direct dependencies between them.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


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
    """

    type: EventType
    data: dict[str, Any]


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

    _instance = None

    def __new__(cls):
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
