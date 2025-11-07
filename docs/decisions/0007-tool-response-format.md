---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
consulted:
informed:
---

# Title: Tool Response Format

## Context and Problem Statement

We need a consistent response format for all tools that makes it easy for the agent to handle both successful operations and errors. The format should be predictable, easy to parse, and provide enough context for error handling.

## Decision Drivers

- **Consistency**: All tools use same format
- **Error Handling**: Clear success/failure indication
- **Debuggability**: Helpful error messages
- **Simplicity**: Easy to create and parse
- **Type Safety**: Structured data

## Considered Options

1. **Dict with success/error fields**
2. **Exceptions for errors**
3. **Result type (Success | Error)**

## Decision Outcome

Chosen option: **"Dict with success/error fields"**

Simple dictionary format with `success` boolean field. Success responses include `result` and optional `message`. Error responses include `error` code and `message`.

### Format

**Success:**
```python
{
    "success": True,
    "result": <any type>,
    "message": "Optional message"
}
```

**Error:**
```python
{
    "success": False,
    "error": "machine_readable_code",
    "message": "Human-friendly message"
}
```

### Consequences

**Good:**
- Simple to implement
- Easy to parse and handle
- Consistent across all tools
- Supports any result type
- Helper methods reduce boilerplate

**Neutral:**
- Need to check `success` field
- Not as type-safe as Result type

**Bad:**
- Slightly more verbose than exceptions
- Need discipline to use consistently

## Related Decisions

- ADR-0006: Class-based Toolset Architecture (provides helper methods)
- ADR-0004: Custom Exception Hierarchy (for internal errors)
