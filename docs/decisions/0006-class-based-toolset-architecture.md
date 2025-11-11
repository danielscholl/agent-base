---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Title: Class-based Toolset Architecture

## Context and Problem Statement

We need to decide how to structure tool registration and dependency management for the agent. Common approaches include function-based tools with global state, class-based toolsets with dependency injection, or plugin systems with dynamic loading. The choice affects testability, maintainability, and extensibility.

## Decision Drivers

- **Testability**: Must be easy to mock dependencies
- **Type Safety**: Compile-time verification preferred
- **Extensibility**: Easy to add new tools
- **No Global State**: Avoid initialization order issues
- **Simplicity**: Not over-engineered

## Considered Options

1. **Class-based toolsets with dependency injection**
2. **Function-based tools with global state**
3. **Plugin system with dynamic loading**

## Decision Outcome

Chosen option: **"Class-based toolsets with dependency injection"**

This approach provides the best balance of testability, type safety, and extensibility. Dependencies are explicitly passed through constructors, making testing straightforward and avoiding global state issues.

### Architecture

```python
# Base class defines contract
class AgentToolset(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config

    @abstractmethod
    def get_tools(self) -> list[Callable]:
        pass

# Concrete implementation
class HelloTools(AgentToolset):
    def get_tools(self):
        return [self.hello_world]

    async def hello_world(self, name: str) -> dict:
        return self._create_success_response(f"Hello, {name}!")

# Usage with dependency injection
config = AgentConfig.from_env()
tools = HelloTools(config)  # Config injected
agent = Agent(config=config, toolsets=[tools])
```

### Key Design Decisions

**1. Abstract Base Class**
- Use ABC to define contract
- Subclasses must implement `get_tools()`
- Provides helper methods for responses

**2. Constructor Injection**
- Each toolset receives AgentConfig
- No global state
- Easy to mock for testing

**3. Structured Responses**
- All tools return dict with `success` field
- Helper methods for consistent format
- Makes error handling predictable

**4. Async Support**
- Tools are async by default
- Supports I/O-bound operations
- Future-proof for parallel execution

### Consequences

**Good:**
- Easy to test with mocked dependencies
- Type-safe initialization via constructors
- Clear dependency ownership
- No global state issues
- Simple to add new toolsets
- Supports multiple toolset instances

**Neutral:**
- Requires more initial setup than functions
- Need to understand ABC pattern

**Bad:**
- More boilerplate than function-based approach
- Slightly more complex than simple functions

## Pros and Cons of the Options

### Option 1: Class-based toolsets with dependency injection

**Pros:**
- Testable with mocked dependencies
- Type-safe initialization via constructors
- Clear dependency ownership
- No global state
- Supports multiple configurations
- Easy to add shared toolset logic

**Cons:**
- More boilerplate code
- Need to understand OOP patterns
- Slightly more complex setup

### Option 2: Function-based tools with global state

**Example:**
```python
_config: AgentConfig | None = None

def initialize_tools(config: AgentConfig):
    global _config
    _config = config

def hello_world(name: str) -> str:
    if not _config:
        raise RuntimeError("Tools not initialized")
    return f"Hello, {name}!"
```

**Pros:**
- Less boilerplate code
- Simple to implement initially
- Familiar pattern

**Cons:**
- Difficult to test (global state)
- No type safety for initialization
- Order-dependent initialization
- Cannot have multiple configurations
- Runtime errors instead of compile-time

### Option 3: Plugin system with dynamic loading

**Example:**
```python
# Load tools from entry points
for entry_point in pkg_resources.iter_entry_points('agent.tools'):
    tool_class = entry_point.load()
    tools.append(tool_class(config))
```

**Pros:**
- Very extensible
- No code changes to add plugins
- Encourages third-party tools

**Cons:**
- More complex implementation
- Runtime errors vs compile-time
- Harder to debug
- Over-engineered for current needs
- Requires packaging knowledge

## Implementation Details

### Base Class Structure

```python
class AgentToolset(ABC):
    """Base class for Agent toolsets."""

    def __init__(self, config: AgentConfig):
        self.config = config

    @abstractmethod
    def get_tools(self) -> list[Callable]:
        """Return list of tool functions."""
        pass

    def _create_success_response(self, result, message=""):
        return {"success": True, "result": result, "message": message}

    def _create_error_response(self, error, message):
        return {"success": False, "error": error, "message": message}
```

### Tool Response Format

**Success Response:**
```python
{
    "success": True,
    "result": <any type>,
    "message": "Optional success message"
}
```

**Error Response:**
```python
{
    "success": False,
    "error": "machine_readable_code",
    "message": "Human-friendly error message"
}
```

### Creating a New Toolset

```python
class MyTools(AgentToolset):
    def get_tools(self):
        return [self.tool1, self.tool2]

    async def tool1(self, arg: str) -> dict:
        """Tool documentation for LLM."""
        try:
            result = self._do_work(arg)
            return self._create_success_response(result)
        except Exception as e:
            return self._create_error_response(
                error="execution_failed",
                message=str(e)
            )
```

### Testing Pattern

```python
def test_tool_with_mocked_config():
    # Create mock config
    config = AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key"
    )

    # Inject into toolset
    tools = MyTools(config)

    # Test tool directly
    result = await tools.tool1("test")
    assert result["success"] is True
```

## Comparison with Global State Approach

### Global State (Avoided)

```python
# ❌ Problems:
# - Hard to test
# - No type safety
# - Order-dependent
_manager = None

def initialize_tools(config):
    global _manager
    _manager = Manager(config)

def my_tool():
    if not _manager:  # Runtime check
        raise RuntimeError("Not initialized")
    return _manager.do_work()
```

### Class-based (Chosen)

```python
# ✅ Benefits:
# - Easy to test
# - Type-safe
# - Self-contained
class MyTools(AgentToolset):
    def __init__(self, config: AgentConfig):  # Type-safe
        super().__init__(config)
        self.manager = Manager(config)  # No global

    def get_tools(self):
        return [self.my_tool]

    async def my_tool(self):
        return self.manager.do_work()  # No runtime check
```

## Future Extensions

**Toolset Composition:**
```python
class CompositeTools(AgentToolset):
    def __init__(self, config):
        super().__init__(config)
        self.hello_tools = HelloTools(config)
        self.search_tools = SearchTools(config)

    def get_tools(self):
        return (
            self.hello_tools.get_tools() +
            self.search_tools.get_tools()
        )
```

**Toolset Lifecycle Hooks:**
```python
class AgentToolset(ABC):
    async def initialize(self):
        """Called before first use."""
        pass

    async def cleanup(self):
        """Called on shutdown."""
        pass
```

**Tool Metadata:**
```python
def get_tools(self):
    return [
        ToolMeta(
            func=self.hello_world,
            name="hello_world",
            description="Say hello",
            category="greeting"
        )
    ]
```

## Performance Considerations

**Current:**
- Negligible overhead (one-time instantiation)
- Tool calls are direct method calls
- No reflection or dynamic dispatch

**If needed:**
- Can add tool caching
- Can implement lazy loading
- Can add connection pooling in toolsets

## References

- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)
- [Abstract Base Classes - Python Docs](https://docs.python.org/3/library/abc.html)
- [Google Python Style Guide - Classes](https://google.github.io/styleguide/pyguide.html#s3.8-classes)

## Related Decisions

- ADR-0003: Configuration Management Strategy (AgentConfig structure)
- ADR-0007: Tool Response Format (response structure)
- ADR-0008: Testing Strategy and Coverage Targets (testing with mocks)
