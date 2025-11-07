---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
consulted:
informed:
---

# Title: Event Bus Pattern for Loose Coupling

## Context and Problem Statement

We need to enable communication between middleware and display components without creating tight coupling. Middleware needs to emit events about agent execution (tool calls, LLM requests, etc.) that display components can visualize, but we don't want middleware to depend on display code. This would make testing difficult and create circular dependencies.

## Decision Drivers

- **Loose Coupling**: Middleware shouldn't depend on display
- **Testability**: Must be able to test middleware without display
- **Extensibility**: Easy to add new event types
- **Simplicity**: Not over-engineered for current needs
- **Type Safety**: Leverage Python's type system

## Considered Options

1. **Event bus with observer pattern**
2. **Direct coupling with callback registration**
3. **Pub/sub library (e.g., PyPubSub)**

## Decision Outcome

Chosen option: **"Event bus with observer pattern"**

A lightweight, custom event bus implementation provides exactly what we need without external dependencies. The singleton pattern ensures one central bus, and the observer pattern enables loose coupling.

### Architecture

```python
# Middleware emits events (doesn't know about display)
bus = get_event_bus()
event = Event(EventType.TOOL_START, {"tool": "hello_world"})
bus.emit(event)

# Display subscribes to events (doesn't know about middleware)
class DisplayComponent:
    def handle_event(self, event: Event):
        if event.type == EventType.TOOL_START:
            print(f"Tool started: {event.data['tool']}")

display = DisplayComponent()
bus.subscribe(display)
```

### Components

**EventType Enum:**
- Defines all possible event types
- Central location for event taxonomy
- Type-safe event creation

**Event Dataclass:**
- Carries event type and data
- Immutable by default
- Clear structure

**EventListener Protocol:**
- Defines listener interface
- Enables duck typing
- No base class required

**EventBus Singleton:**
- Central message broker
- Observer pattern implementation
- Thread-safe (single-threaded for now)

### Consequences

**Good:**
- Complete decoupling between middleware and display
- Easy to test middleware in isolation (no display needed)
- Easy to test display in isolation (emit mock events)
- No external dependencies
- Type-safe with Protocol
- Simple to understand and maintain

**Neutral:**
- Singleton pattern (acceptable for this use case)
- Synchronous event delivery (async not needed yet)

**Bad:**
- Custom implementation instead of library (but very simple)
- No event persistence or replay (not needed for MVP)

## Pros and Cons of the Options

### Option 1: Event bus with observer pattern

**Pros:**
- Perfect decoupling - components don't know about each other
- Easy to test - can mock events or listeners
- Lightweight - no external dependencies
- Type-safe with Protocol
- Simple to extend with new event types
- Follows GoF observer pattern

**Cons:**
- Custom implementation to maintain
- No advanced features (filtering, priority, async)
- Singleton pattern (some consider anti-pattern)

### Option 2: Direct coupling with callback registration

**Pros:**
- Simple to implement
- Direct communication
- No intermediary

**Cons:**
- Tight coupling - middleware depends on display
- Hard to test independently
- No type safety for callbacks
- Difficult to add multiple listeners
- Circular dependency risk

### Option 3: Pub/sub library (e.g., PyPubSub)

**Pros:**
- Feature-rich (filtering, priority, etc.)
- Well-tested
- Handles edge cases

**Cons:**
- External dependency
- Over-engineered for our needs
- Learning curve
- May not support typing well
- Adds weight to project

## Implementation Details

### Event Type Enum

```python
class EventType(Enum):
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
```

**Adding new event types:**
Simply add to enum. No other changes needed.

### Event Structure

```python
@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
```

**Event data conventions:**
- Keep data simple and serializable
- Include only what listeners need
- Document expected keys in event docstrings

### Listener Protocol

```python
class EventListener(Protocol):
    def handle_event(self, event: Event) -> None: ...
```

**Benefits:**
- Duck typing - any object with `handle_event` works
- No base class inheritance required
- Type checker validates signature

### Singleton Pattern

```python
class EventBus:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = []
        return cls._instance
```

**Why singleton:**
- One central bus for all events
- Simplifies access (`get_event_bus()`)
- No need to pass bus around
- Acceptable for this use case

**Note:** If multi-instance needed later, can add factory pattern.

## Usage Patterns

### Middleware Emitting Events

```python
from agent.events import Event, EventType, get_event_bus

def run_tool(tool_name: str, **kwargs):
    bus = get_event_bus()

    # Notify tool start
    bus.emit(Event(EventType.TOOL_START, {
        "tool": tool_name,
        "args": kwargs
    }))

    try:
        result = execute_tool(tool_name, **kwargs)
        bus.emit(Event(EventType.TOOL_COMPLETE, {
            "tool": tool_name,
            "result": result
        }))
    except Exception as e:
        bus.emit(Event(EventType.TOOL_ERROR, {
            "tool": tool_name,
            "error": str(e)
        }))
```

### Display Listening to Events

```python
from agent.events import Event, EventType, get_event_bus

class ExecutionTreeDisplay:
    def __init__(self):
        self.current_tools = []
        bus = get_event_bus()
        bus.subscribe(self)

    def handle_event(self, event: Event):
        if event.type == EventType.TOOL_START:
            self.show_tool_start(event.data["tool"])
        elif event.type == EventType.TOOL_COMPLETE:
            self.show_tool_complete(event.data["tool"])
```

### Testing with Events

```python
# Test middleware without display
def test_middleware_emits_events():
    bus = EventBus()
    bus.clear()  # Start clean

    listener = MockListener()
    bus.subscribe(listener)

    run_middleware_function()

    assert len(listener.events_received) == 2
    assert listener.events_received[0].type == EventType.TOOL_START
```

## Future Extensions

If needed, can add:

**Event Filtering:**
```python
def subscribe(self, listener, filter_types: set[EventType] = None):
    # Only emit certain event types to listener
```

**Priority Handling:**
```python
def subscribe(self, listener, priority: int = 0):
    # Higher priority listeners receive events first
```

**Async Events:**
```python
async def emit_async(self, event: Event):
    # Async event emission for I/O-bound listeners
```

**Event History:**
```python
def get_history(self, event_type: EventType = None):
    # Retrieve past events for replay or debugging
```

## Testing Strategy

Tests cover:
1. Singleton behavior
2. Subscribe/unsubscribe
3. Event emission to multiple listeners
4. Event filtering by listeners
5. Clear functionality
6. Edge cases (no listeners, duplicate subscribe)

All 13 tests passing with 100% coverage.

## Performance Considerations

**Current implementation:**
- Synchronous, single-threaded
- O(n) event delivery (n = number of listeners)
- No significant overhead for expected listener count (<10)

**If performance becomes issue:**
- Use weak references for listeners
- Add async support for I/O-bound listeners
- Implement event batching

## References

- [Observer Pattern - Gang of Four](https://en.wikipedia.org/wiki/Observer_pattern)
- [Python Protocol - PEP 544](https://peps.python.org/pep-0544/)
- [Singleton Pattern](https://en.wikipedia.org/wiki/Singleton_pattern)

## Related Decisions

- ADR-0010: Display Output Format (uses events from this bus)
- Future ADR: Middleware Architecture (will emit events on this bus)
- Future ADR: Observability (may extend events for metrics)
