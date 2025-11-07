---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
consulted:
informed:
---

# Title: Custom Exception Hierarchy Design

## Context and Problem Statement

We need to define a clear exception hierarchy for the agent system that provides meaningful error handling while avoiding overly complex or granular exception types. The hierarchy should make it easy to catch specific errors when needed while also supporting catch-all error handling.

## Decision Drivers

- **Clarity**: Exceptions should clearly indicate what went wrong
- **Hierarchy**: Logical grouping of related errors
- **Catchability**: Support both specific and broad error handling
- **Extensibility**: Easy to add new exception types
- **Standard Python practices**: Follow Python exception conventions

## Considered Options

1. **Single base with domain-specific exceptions**
2. **Flat exception structure with no hierarchy**
3. **Multiple base classes for different domains**

## Decision Outcome

Chosen option: **"Single base with domain-specific exceptions"**

This provides a clean hierarchy with one base `AgentError` and domain-specific exceptions for configuration, tools, and APIs. The tree structure makes relationships clear while avoiding over-engineering.

### Exception Hierarchy

```
AgentError (base)
├── ConfigurationError
├── ToolError
│   ├── ToolNotFoundError
│   └── ToolExecutionError
└── APIError
    └── ResourceNotFoundError
```

### Usage Patterns

**Specific error handling:**
```python
from agent.utils.errors import ToolNotFoundError, ConfigurationError

try:
    config = AgentConfig.from_env()
    config.validate()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Handle missing API keys, invalid providers, etc.
```

**Catch-all error handling:**
```python
from agent.utils.errors import AgentError

try:
    agent = Agent(config)
    result = await agent.run(prompt)
except AgentError as e:
    print(f"Agent error: {e}")
    # Handle any agent-related error
```

**Tool execution with multiple exception types:**
```python
from agent.utils.errors import ToolNotFoundError, ToolExecutionError

try:
    result = await tools.execute("search", query="test")
except ToolNotFoundError:
    print("Tool not registered")
except ToolExecutionError as e:
    print(f"Tool failed: {e}")
```

### Consequences

**Good:**
- Clear hierarchy makes relationships obvious
- Single base exception simplifies catch-all handling
- Domain-specific exceptions provide meaningful error messages
- Easy to extend with new exception types
- Follows Python conventions (inherit from Exception)

**Neutral:**
- Not as granular as could be (trade-off for simplicity)
- May need additional exceptions as features grow

**Bad:**
- Slightly more boilerplate than using standard exceptions
- Developers must learn custom exception types

## Pros and Cons of the Options

### Option 1: Single base with domain-specific exceptions

**Pros:**
- Clear hierarchy shows error relationships
- Single base `AgentError` for catch-all handling
- Domain-specific exceptions (Config, Tool, API) are intuitive
- Easy to add new exceptions at appropriate level
- Standard Python inheritance pattern

**Cons:**
- More exceptions to maintain than flat structure
- Requires documentation for proper usage

### Option 2: Flat exception structure with no hierarchy

**Pros:**
- Simplest to implement
- No hierarchy to understand
- Very straightforward

**Cons:**
- No logical grouping of related errors
- Cannot catch "all tool errors" or "all API errors"
- Harder to extend consistently
- Less meaningful structure

### Option 3: Multiple base classes for different domains

**Pros:**
- Clear domain separation
- Could catch all errors from one domain
- Very explicit about error origins

**Cons:**
- Cannot catch all agent errors easily
- More complex hierarchy
- Multiple inheritance possible (confusing)
- Over-engineered for current needs

## Implementation Details

### Base Exception

```python
class AgentError(Exception):
    """Base exception for all Agent errors."""
    pass
```

All custom exceptions inherit from `AgentError`, which inherits from Python's `Exception`.

### Configuration Errors

```python
class ConfigurationError(AgentError):
    """Configuration validation or loading errors."""
    pass
```

Used when:
- Missing required environment variables
- Invalid provider configuration
- Configuration validation fails

### Tool Errors

```python
class ToolError(AgentError):
    """Base exception for tool-related errors."""
    pass

class ToolNotFoundError(ToolError):
    """Tool not found in registry."""
    pass

class ToolExecutionError(ToolError):
    """Tool execution failed."""
    pass
```

Used when:
- Tool isn't registered (`ToolNotFoundError`)
- Tool execution fails (`ToolExecutionError`)
- Future: Tool timeout, Tool permission denied, etc.

### API Errors

```python
class APIError(AgentError):
    """API integration errors."""
    pass

class ResourceNotFoundError(APIError):
    """Resource not found in external system."""
    pass
```

Used when:
- External API calls fail
- Resources don't exist (404)
- Future: API rate limits, authentication failures, etc.

## Future Extensions

As the agent system grows, we can add exceptions at the appropriate level:

**Tool-related:**
- `ToolTimeoutError(ToolError)` - Tool took too long
- `ToolPermissionError(ToolError)` - Tool lacks permissions

**API-related:**
- `APIRateLimitError(APIError)` - Rate limit exceeded
- `APIAuthenticationError(APIError)` - Auth failed

**Configuration-related:**
- `ConfigurationValidationError(ConfigurationError)` - Invalid values
- `ConfigurationMissingError(ConfigurationError)` - Missing required config

## Testing Strategy

Each exception should be tested for:
1. Correct inheritance chain
2. Proper error message handling
3. Exception can be caught at appropriate levels

```python
def test_tool_not_found_is_tool_error():
    """Test ToolNotFoundError inherits from ToolError."""
    assert issubclass(ToolNotFoundError, ToolError)

def test_tool_not_found_is_agent_error():
    """Test ToolNotFoundError inherits from AgentError."""
    assert issubclass(ToolNotFoundError, AgentError)

def test_can_catch_all_tool_errors():
    """Test catching ToolError catches specific tool exceptions."""
    try:
        raise ToolNotFoundError("test tool")
    except ToolError as e:
        assert "test tool" in str(e)
```

## References

- [PEP 8 - Programming Recommendations](https://peps.python.org/pep-0008/#programming-recommendations)
- [Python Exception Hierarchy](https://docs.python.org/3/library/exceptions.html#exception-hierarchy)
- [Effective Python - Item 20: Prefer Exceptions to Returning None](https://effectivepython.com/)

## Related Decisions

- ADR-0003: Configuration Management Strategy (uses ConfigurationError)
- ADR-0006: Class-based Toolset Architecture (uses ToolError hierarchy)
- Future ADR: API Integration Patterns (will use APIError hierarchy)
