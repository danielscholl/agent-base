# Tool Architecture

This document describes the architectural patterns used in the agent-template project for building tool-enabled AI agents.

## Overview

The agent-template implements a class-based toolset architecture with dependency injection, avoiding common pitfalls like global state and tight coupling. The architecture enables:

- Easy testing with mocked dependencies
- Type-safe tool initialization
- Loose coupling between components
- High test coverage (85%+ target)
- Modular, extensible design

## Core Components

### 1. Agent Class

The `Agent` class is the central component that integrates:
- Multi-provider LLM support (OpenAI, Anthropic, Azure AI Foundry)
- Tool registration and management
- Microsoft Agent Framework integration

```python
from agent import Agent, AgentConfig

config = AgentConfig.from_env()
agent = Agent(config)
response = await agent.run("Your prompt here")
```

**Key Features:**
- Dependency injection for testing
- Support for multiple toolsets
- Async execution support

### 2. Configuration System

`AgentConfig` provides centralized configuration management:

```python
config = AgentConfig.from_env()  # Load from environment
config.validate()                 # Validate provider settings
```

**Multi-Provider Support:**
- OpenAI: `LLM_PROVIDER=openai`
- Anthropic: `LLM_PROVIDER=anthropic`
- Azure AI Foundry: `LLM_PROVIDER=azure_ai_foundry`

### 3. Toolset Architecture

Tools are organized into toolsets that inherit from `AgentToolset`:

```python
class HelloTools(AgentToolset):
    def __init__(self, config: AgentConfig):
        super().__init__(config)

    def get_tools(self):
        return [self.hello_world, self.greet_user]

    async def hello_world(self, name: str = "World") -> dict:
        return self._create_success_response(f"Hello, {name}!")
```

**Benefits:**
- No global state
- Easy to test with mocked config
- Clear dependency ownership
- Structured responses

### 4. Event Bus

Loose coupling between middleware and display via observer pattern:

```python
from agent.events import get_event_bus, Event, EventType

bus = get_event_bus()
bus.subscribe(display_component)

# Emit events
bus.emit(Event(EventType.TOOL_START, {"tool": "hello_world"}))
```

### 5. Exception Hierarchy

Domain-specific exceptions for clear error handling:

```
AgentError (base)
├── ConfigurationError
├── ToolError
│   ├── ToolNotFoundError
│   └── ToolExecutionError
└── APIError
    └── ResourceNotFoundError
```

## Architectural Patterns

### Dependency Injection

**Why:** Enables testing without real LLM calls or external services.

```python
# Production
config = AgentConfig.from_env()
agent = Agent(config)

# Testing
from tests.mocks import MockChatClient
mock_client = MockChatClient(response="Test")
agent = Agent(config=config, chat_client=mock_client)
```

### Structured Responses

All tools return consistent response format:

```python
# Success
{
    "success": True,
    "result": <any type>,
    "message": "Optional message"
}

# Error
{
    "success": False,
    "error": "machine_readable_code",
    "message": "Human-friendly message"
}
```

### Event-Driven Architecture

Middleware emits events, display subscribes:

```python
# Middleware (emits)
bus.emit(Event(EventType.TOOL_START, {"tool": name}))

# Display (subscribes)
class DisplayComponent:
    def handle_event(self, event: Event):
        if event.type == EventType.TOOL_START:
            self.show_tool_start(event.data["tool"])
```

## Anti-Patterns Avoided

### 1. Global State

❌ **Bad:**
```python
_manager = None

def initialize_tools(config):
    global _manager
    _manager = Manager(config)
```

✅ **Good:**
```python
class MyTools(AgentToolset):
    def __init__(self, config: AgentConfig):
        self.manager = Manager(config)
```

### 2. Runtime Initialization

❌ **Bad:**
```python
def my_tool():
    if not _manager:
        raise RuntimeError("Not initialized")
```

✅ **Good:**
```python
class MyTools(AgentToolset):
    async def my_tool(self):
        return self.manager.do_work()  # Always available
```

### 3. Tight Coupling

❌ **Bad:**
```python
from agent.display import show_tool_start

def run_tool():
    show_tool_start("tool_name")  # Direct dependency
```

✅ **Good:**
```python
from agent.events import get_event_bus, Event

def run_tool():
    bus = get_event_bus()
    bus.emit(Event(EventType.TOOL_START, {"tool": "name"}))
```

## Testing Strategy

### Unit Tests

Test components in isolation with mocked dependencies:

```python
def test_hello_tools(mock_config):
    tools = HelloTools(mock_config)
    result = await tools.hello_world("Test")
    assert result["success"] is True
```

**Coverage Target:** 100% for business logic

### Integration Tests

Test full stack with mock chat client:

```python
@pytest.mark.asyncio
async def test_full_stack():
    config = AgentConfig(llm_provider="openai", openai_api_key="test")
    mock_client = MockChatClient(response="Test response")
    agent = Agent(config=config, chat_client=mock_client)

    response = await agent.run("Test prompt")
    assert response == "Test response"
```

**Coverage Target:** 85%+ overall

### Test Organization

```
tests/
├── unit/              # Isolated component tests
│   ├── test_config.py
│   ├── test_events.py
│   ├── test_hello_tools.py
│   └── test_agent.py
├── integration/       # Full stack tests
│   └── test_hello_integration.py
├── mocks/            # Test mocks
│   └── mock_client.py
└── conftest.py       # Shared fixtures
```

## Creating New Tools

### Step 1: Create Toolset Class

```python
from agent.tools.toolset import AgentToolset

class MyTools(AgentToolset):
    def get_tools(self):
        return [self.my_tool]

    async def my_tool(self, arg: str) -> dict:
        \"\"\"Tool documentation for LLM.

        Args:
            arg: Argument description

        Returns:
            Structured response with success field
        \"\"\"
        try:
            result = self._do_work(arg)
            return self._create_success_response(result)
        except Exception as e:
            return self._create_error_response(
                error="execution_failed",
                message=str(e)
            )
```

### Step 2: Register with Agent

```python
from agent import Agent
from mytools import MyTools

agent = Agent(
    config=config,
    toolsets=[HelloTools(config), MyTools(config)]
)
```

### Step 3: Write Tests

```python
@pytest.mark.asyncio
async def test_my_tool():
    config = AgentConfig(llm_provider="openai", openai_api_key="test")
    tools = MyTools(config)

    result = await tools.my_tool("test")
    assert result["success"] is True
```

## CLI Architecture

Simple CLI with typer and rich:

```python
agent --check          # Health check
agent --config         # Show configuration
agent -p "prompt"      # Single prompt mode
agent --version        # Show version
```

## Future Enhancements

### Phase 2: Display System
- Execution visualization with Rich
- Progress bars and spinners
- Tree-based execution hierarchy
- Status bar with model info

### Phase 3: Session Management
- Session persistence
- Context restoration
- Session switching
- Metadata tracking

### Phase 4: Advanced Tools
- API integration tools
- Data processing tools
- Web scraping tools
- File system tools

## References

See Architecture Decision Records (ADRs) in `docs/decisions/`:

- ADR-0001: Module and Package Naming Conventions
- ADR-0002: Repository Infrastructure and DevOps Setup
- ADR-0003: Configuration Management Strategy
- ADR-0004: Custom Exception Hierarchy Design
- ADR-0005: Event Bus Pattern for Loose Coupling
- ADR-0006: Class-based Toolset Architecture
- ADR-0007: Tool Response Format
- ADR-0008: Testing Strategy and Coverage Targets

## Summary

The agent-template architecture prioritizes:

1. **Testability:** Dependency injection enables easy mocking
2. **Type Safety:** Clear type hints throughout
3. **Loose Coupling:** Event bus for component communication
4. **No Global State:** Class-based toolsets with constructors
5. **High Coverage:** 85%+ test coverage target
6. **Extensibility:** Easy to add new tools and providers

This foundation enables confident development of custom tools and integrations while maintaining code quality and avoiding technical debt.
