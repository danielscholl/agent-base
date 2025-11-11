---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Middleware Integration Strategy

## Context and Problem Statement

We need automatic event emission during agent execution to enable visualization and observability, but modifying individual tools to emit events would create tight coupling and violate separation of concerns. How can we transparently track execution without modifying tool implementations?

## Decision Drivers

- Tools should not know about display/visualization
- Event emission should be automatic, not manual
- Should work for both LLM calls and tool executions
- Must support nested tool calls (parent_id correlation)
- Should be opt-in via configuration, not always-on
- Must handle errors without breaking execution

## Considered Options

1. **Direct tool modification** - Add event emission to each tool
2. **Function-level middleware** - Use framework middleware to wrap tool calls
3. **Polling/inspection** - Periodically check agent state
4. **Manual logging** - Require developers to emit events

## Decision Outcome

Chosen option: **"Function-level middleware with context propagation"**, because:

- **Decoupled**: Tools remain pure, no visualization dependencies
- **Automatic**: Events emit transparently via middleware
- **Framework-native**: Uses agent_framework's built-in middleware support
- **Reusable**: Middleware functions work across all tools
- **Conditional**: Only emits when `should_show_visualization()` is True

### Implementation Details

**Middleware Architecture:**

**Agent-Level Middleware** (wraps entire agent run):
```python
async def agent_run_logging_middleware(context, next):
    # Emit LLMRequestEvent before call
    event = LLMRequestEvent(message_count=len(context.messages))
    get_event_emitter().emit(event)

    await next(context)

    # Emit LLMResponseEvent after call
    response_event = LLMResponseEvent(duration=duration)
    get_event_emitter().emit(response_event)
```

**Function-Level Middleware** (wraps each tool call):
```python
async def logging_function_middleware(context, next):
    # Emit ToolStartEvent
    event = ToolStartEvent(
        tool_name=context.function.name,
        arguments=sanitize_arguments(context.arguments),
        parent_id=get_current_tool_event_id()  # For nesting
    )
    set_current_tool_event_id(event.event_id)

    result = await next(context)

    # Emit ToolCompleteEvent
    complete_event = ToolCompleteEvent(...)
```

**Context Propagation:**
Uses `ExecutionContext` to control emission:
```python
# At CLI level
ctx = ExecutionContext(show_visualization=True)
set_execution_context(ctx)

# In middleware
if should_show_visualization():
    get_event_emitter().emit(event)
```

**Nested Tool Support:**
- Parent tool sets `set_current_tool_event_id(event_id)`
- Child tools read `get_current_tool_event_id()` for `parent_id`
- Enables hierarchical display: parent → child → grandchild

**Argument Sanitization:**
Removes sensitive data before emission:
```python
safe_args = {
    k: v for k, v in args.items()
    if k not in ["token", "api_key", "password", "secret"]
}
```

**Error Handling:**
Middleware emits `ToolErrorEvent` on exception, then re-raises:
```python
try:
    result = await next(context)
    emit(ToolCompleteEvent(...))
except Exception as e:
    emit(ToolErrorEvent(...))
    raise  # Don't swallow exceptions
```

### Consequences

**Positive:**
- Zero coupling between tools and display
- Automatic tracking of all executions
- Works with any tool without modification
- Supports arbitrary nesting depth
- Error events still emitted on failure
- Can be disabled globally via context

**Negative:**
- Adds execution overhead (minimal, ~1ms per tool)
- Middleware ordering matters (must be consistent)
- Context propagation uses ContextVar (needs understanding)

**Neutral:**
- Requires framework support for middleware
- Event emission is async (queue-based, non-blocking)

## Related Decisions

- [ADR-0005](0005-event-bus-pattern-for-loose-coupling.md) - Event bus enables middleware emission
- [ADR-0010](0010-display-output-format.md) - Display consumes middleware events
- [ADR-0006](0006-class-based-toolset-architecture.md) - Toolset architecture enables middleware
