# Feature: Agent Memory Support (In-Memory Storage)

## Feature Description

Add in-memory storage capability to the agent-template project to maintain conversation context across multiple interactions. This feature leverages the Microsoft Agent Framework's built-in `ChatMessageStore` mechanism to provide persistent memory within agent sessions, allowing the agent to remember user preferences, recall previous conversations, and provide personalized experiences.

Unlike simple thread-based context (which already exists), this feature adds explicit memory management capabilities through:
- In-memory storage with keyword search and filtering
- Memory persistence alongside session data
- ContextProvider integration for automatic memory injection and storage
- Seamless session resume with full conversation context

## User Story

**As a** developer building conversational AI applications
**I want to** have structured in-memory storage for agent conversations
**So that** I can maintain rich context across sessions, implement memory-aware features, and provide personalized user experiences without requiring external database dependencies.

## Problem Statement

The current agent-template implementation provides basic thread management through `ThreadPersistence`, which serializes conversation threads for later resumption. However, it lacks:

1. **Automatic Context Injection**: No mechanism to automatically provide conversation history to the LLM
2. **Memory Lifecycle Management**: No clear separation between session state and memory state
3. **Cross-Turn Memory**: Agent doesn't remember information from earlier in the conversation
4. **Memory Persistence**: No way to save and restore conversation context across sessions
5. **Memory Search**: No ability to search across past conversations or retrieve relevant context

The Agent Framework provides `ContextProvider` as the pattern for memory and context management, which we haven't yet implemented.

## Solution Statement

Implement a layered memory architecture that:

1. **Uses Agent Framework's ContextProvider Pattern**: Leverages the framework's intended pattern for memory and context management
2. **Integrates with Existing Persistence**: Extend `ThreadPersistence` to save/load memory state alongside thread data
3. **Provides Memory Manager Abstraction**: Create a `MemoryManager` ABC for future extensibility (could add external memory services later)
4. **Automatic Context Injection**: ContextProvider automatically injects memories before LLM calls and stores responses after
5. **Supports Multiple Memory Types**: Enable different memory strategies (in-memory, external services like mem0, langchain)

This approach uses the Agent Framework's official pattern for memory (discovered from butler-agent implementation) while maintaining compatibility with existing architecture.

## Related Documentation

### Requirements
- [docs/design/requirements.md](../design/requirements.md) - Section FR-2: Conversational Context Management (existing thread-based context)
- [docs/design/requirements.md](../design/requirements.md) - Section UI-3: Session Management (existing session persistence)

### Architecture Decisions
- [docs/decisions/0006-class-based-toolset-architecture.md](../decisions/0006-class-based-toolset-architecture.md) - Dependency injection pattern for toolsets
- [docs/decisions/0008-testing-strategy-and-coverage-targets.md](../decisions/0008-testing-strategy-and-coverage-targets.md) - Testing approach and coverage requirements
- [docs/decisions/0011-session-management-architecture.md](../decisions/0011-session-management-architecture.md) - Existing session persistence patterns
- [docs/decisions/0005-event-bus-pattern-for-loose-coupling.md](../decisions/0005-event-bus-pattern-for-loose-coupling.md) - Event emission for memory operations

## Codebase Analysis Findings

### Architecture Patterns
- **Dependency Injection**: All components receive dependencies via constructor (no global state)
- **ABC-Based Design**: Use abstract base classes for extensibility (see `AgentToolset`)
- **Structured Responses**: All operations return `{"success": bool, "result": any, "message": str}` format
- **Event-Driven**: Middleware emits events via event bus for monitoring
- **Async-First**: All I/O operations use `async/await`

### Naming Conventions
- Modules: `snake_case` (e.g., `memory_manager.py`)
- Classes: `PascalCase` (e.g., `MemoryManager`, `InMemoryStore`)
- Functions: `snake_case` (e.g., `save_memory_state`, `restore_memory`)
- Private: Leading underscore (e.g., `_sanitize_memory_key`)

### Similar Implementations
- **ThreadPersistence** (`src/agent/persistence.py`):
  - Pattern for save/load with fallback serialization
  - Security: Uses `_sanitize_conversation_name()` to prevent path traversal
  - Metadata tracking in `index.json`
  - Context summary generation for failed deserialization

- **AgentToolset Pattern** (`src/agent/tools/toolset.py`):
  - ABC with `__init__(config)` for dependency injection
  - Helper methods `_create_success_response()` and `_create_error_response()`
  - `get_tools()` returns list of callable tool functions

### Integration Patterns
1. **Agent Initialization**: Add `memory_manager` parameter to `Agent.__init__()`
2. **Configuration**: Add memory fields to `AgentConfig` dataclass
3. **ContextProvider**: Create `MemoryContextProvider` for automatic context injection/storage
4. **Persistence**: Extend `ThreadPersistence` with memory save/load methods
5. **CLI Integration**: Restore memory state during session resume

### Agent Framework ContextProvider Pattern

From the Microsoft Agent Framework documentation and butler-agent implementation:

**ContextProvider Pattern**:
```python
from agent_framework import ContextProvider, Context, ChatMessage

class MemoryContextProvider(ContextProvider):
    async def invoking(self, messages, **kwargs) -> Context:
        # Called BEFORE LLM - inject memory as context
        memories = await self.memory_manager.get_all()
        return Context(instructions="Previous conversation: ...")

    async def invoked(self, request_messages, response_messages, **kwargs):
        # Called AFTER LLM - store both user and assistant messages
        await self.memory_manager.add([user_msg, assistant_msg])
```

**Why ContextProvider (not middleware)?**
- ContextProvider receives both request AND response messages
- `invoking()` can inject context before LLM call
- `invoked()` sees complete conversation turn
- Framework's intended pattern for memory/context management
- Proven pattern from butler-agent production use

## Archon Project

**Project ID**: `6c17acbf-22cb-453b-8d21-0c738e251744`

Tasks will be created in Archon during implementation phase via `/implement`.

## Relevant Files

### Existing Files to Modify

- **src/agent/agent.py**: Add memory_manager parameter and initialization
  - Add `memory_manager: MemoryManager | None` to `__init__()`
  - Create default memory manager if `config.memory_enabled`
  - Pass memory manager to middleware

- **src/agent/config.py**: Add memory configuration fields
  - Add `memory_enabled: bool = False`
  - Add `memory_type: str = "in_memory"`
  - Add `memory_dir: Path | None = None` (defaults to `agent_data_dir / "memory"`)

- **src/agent/persistence.py**: Extend with memory persistence
  - Add `save_memory_state(session_name, memory_data)` method
  - Add `load_memory_state(session_name)` method
  - Update metadata to track memory state

- **src/agent/memory/context_provider.py**: Add memory context provider
  - Create `MemoryContextProvider(ContextProvider)` for automatic memory management
  - Implements `invoking()` to inject memories before LLM calls
  - Implements `invoked()` to store messages after LLM responds

- **src/agent/cli/session.py**: Integrate memory restoration
  - Update `restore_session_context()` to restore memory
  - Update `auto_save_session()` to save memory state

### New Files to Create

- **src/agent/memory/__init__.py**: Package initialization
  - Export `MemoryManager`, `InMemoryStore`, `MemoryContextProvider`, `create_memory_manager`

- **src/agent/memory/manager.py**: Abstract memory manager
  - `MemoryManager` ABC with core operations
  - `add(messages)`, `search(query)`, `get_all()`, `clear()`, `get_recent()`

- **src/agent/memory/store.py**: In-memory implementation
  - `InMemoryStore(MemoryManager)` - implements the MemoryManager interface
  - Stores messages with metadata (timestamp, role, content)
  - Supports keyword search and filtering

- **src/agent/memory/persistence.py**: Memory serialization
  - `MemoryPersistence` class for save/load operations
  - JSON serialization with versioning
  - Compatible with existing session persistence

- **src/agent/memory/context_provider.py**: Framework integration
  - `MemoryContextProvider(ContextProvider)` - Agent Framework integration
  - Automatically injects memories before LLM calls
  - Stores user and assistant messages after each turn

### New Test Files

- **tests/unit/memory/test_memory_manager.py**: Memory manager unit tests
- **tests/unit/memory/test_memory_store.py**: In-memory store unit tests
- **tests/unit/memory/test_memory_persistence.py**: Memory persistence tests
- **tests/integration/test_memory_integration.py**: Full memory workflow tests
- **tests/fixtures/memory.py**: Memory-related test fixtures

## Implementation Plan

### Phase 1: Foundation (Core Memory Infrastructure)

**Objective**: Build the foundational memory components with proper abstractions and no external dependencies.

1. Create memory module structure
2. Implement `MemoryManager` ABC with core operations
3. Implement `InMemoryStore` with structured storage
4. Add memory configuration to `AgentConfig`
5. Write unit tests for core components

**Deliverables**:
- `src/agent/memory/` module with manager and store
- Configuration fields in `AgentConfig`
- 100% test coverage for memory components

### Phase 2: Agent Integration

**Objective**: Integrate memory manager with the Agent class and middleware system.

1. Add `memory_manager` parameter to `Agent.__init__()`
2. Create memory initialization logic in Agent
3. Implement `memory_middleware` for automatic updates
4. Add memory event types to event system
5. Write integration tests

**Deliverables**:
- Memory-aware Agent class
- Middleware for memory updates
- Integration tests with mocked LLM

### Phase 3: Persistence and CLI Integration

**Objective**: Extend session persistence to include memory state and integrate with CLI.

1. Extend `ThreadPersistence` with memory save/load
2. Create `MemoryPersistence` helper class
3. Update CLI session management to restore memory
4. Update metadata tracking for memory state
5. Write persistence tests

**Deliverables**:
- Memory persistence alongside sessions
- CLI integration for memory restoration
- End-to-end persistence tests

### Phase 4: Optional Memory Tools

**Objective**: Provide explicit memory operation tools for agent use.

1. Create `MemoryTools(AgentToolset)` class
2. Implement memory manipulation tools
3. Add to default toolsets when memory enabled
4. Write tool tests
5. Add example usage to documentation

**Deliverables**:
- Memory toolset with 4-5 tools
- Tool tests with mocked config
- Usage examples

## Step by Step Tasks

### Task 1: Create Memory Module Structure
- **Description**: Set up the memory module package with proper initialization
- **Files to create**:
  - `src/agent/memory/__init__.py`
  - `src/agent/memory/manager.py` (empty ABC skeleton)
  - `src/agent/memory/store.py` (empty class)
  - `src/agent/memory/persistence.py` (empty class)
- **Archon task**: Will be created during implementation

### Task 2: Implement MemoryManager ABC
- **Description**: Create abstract base class defining memory operations interface
- **Files to modify**:
  - `src/agent/memory/manager.py`
- **Key methods**: `add()`, `search()`, `get_all()`, `clear()`, `get_recent()`
- **Pattern**: Follow `AgentToolset` ABC pattern with helper methods
- **Archon task**: Will be created during implementation

### Task 3: Implement InMemoryStore
- **Description**: Create in-memory message store with structured storage
- **Files to modify**:
  - `src/agent/memory/store.py`
- **Features**:
  - Extends Agent Framework's `ChatMessageStore` if applicable
  - Stores messages with metadata (timestamp, type, user_id)
  - Implements search across message history
  - Supports filtering by date range, message type, keywords
- **Archon task**: Will be created during implementation

### Task 4: Add Memory Configuration
- **Description**: Add memory-related fields to AgentConfig
- **Files to modify**:
  - `src/agent/config.py`
- **New fields**:
  ```python
  memory_enabled: bool = False
  memory_type: str = "in_memory"  # Future: "mem0", "langchain", etc.
  memory_dir: Path | None = None
  ```
- **Update**: `from_env()` to load memory settings from environment
- **Archon task**: Will be created during implementation

### Task 5: Write Core Memory Tests
- **Description**: Create comprehensive unit tests for memory components
- **Files to create**:
  - `tests/unit/memory/__init__.py`
  - `tests/unit/memory/test_memory_manager.py`
  - `tests/unit/memory/test_memory_store.py`
  - `tests/fixtures/memory.py`
- **Coverage**: 100% for business logic
- **Patterns**: Use pytest markers `@pytest.mark.unit` and `@pytest.mark.memory`
- **Archon task**: Will be created during implementation

### Task 6: Integrate Memory with Agent Class
- **Description**: Add memory manager initialization to Agent
- **Files to modify**:
  - `src/agent/agent.py`
- **Changes**:
  - Add `memory_manager` parameter to `__init__()`
  - Create default memory manager if `config.memory_enabled`
  - Store as instance variable for middleware access
- **Pattern**: Follow existing dependency injection pattern
- **Archon task**: Will be created during implementation

### Task 7: Implement Memory Middleware
- **Description**: Create middleware for automatic memory updates
- **Files to modify**:
  - `src/agent/middleware.py`
- **Functionality**:
  - Before LLM call: Retrieve relevant memories (future enhancement)
  - After LLM call: Store interaction in memory
  - Emit memory events for monitoring
- **Pattern**: Follow `agent_run_logging_middleware` pattern
- **Archon task**: Will be created during implementation

### Task 8: Add Memory Event Types
- **Description**: Add memory-specific event types to event system
- **Files to modify**:
  - `src/agent/events.py` or create `src/agent/memory/events.py`
- **New event types**:
  - `MEMORY_SAVE`: When memory is stored
  - `MEMORY_LOAD`: When memory is retrieved
  - `MEMORY_SEARCH`: When memory is searched
- **Archon task**: Will be created during implementation

### Task 9: Write Agent Integration Tests
- **Description**: Test full agent with memory functionality
- **Files to create**:
  - `tests/integration/test_memory_integration.py`
- **Test scenarios**:
  - Agent with memory enabled vs disabled
  - Memory persistence across multiple runs
  - Memory retrieval and context injection
- **Pattern**: Use `MockChatClient` for LLM mocking
- **Archon task**: Will be created during implementation

### Task 10: Implement MemoryPersistence
- **Description**: Create helper for memory serialization
- **Files to modify**:
  - `src/agent/memory/persistence.py`
- **Functionality**:
  - Serialize memory state to JSON
  - Deserialize memory state from JSON
  - Handle versioning for future compatibility
- **Pattern**: Follow `ThreadPersistence` save/load pattern
- **Archon task**: Will be created during implementation

### Task 11: Extend ThreadPersistence with Memory
- **Description**: Add memory save/load to existing persistence
- **Files to modify**:
  - `src/agent/persistence.py`
- **New methods**:
  - `save_memory_state(session_name, memory_data) -> Path`
  - `load_memory_state(session_name) -> dict | None`
- **Update**: Metadata to track memory file location
- **Archon task**: Will be created during implementation

### Task 12: Integrate Memory in CLI Session Management
- **Description**: Update CLI to restore memory during session resume
- **Files to modify**:
  - `src/agent/cli/session.py`
- **Functions to update**:
  - `restore_session_context()`: Load memory after thread
  - `auto_save_session()`: Save memory before exit
- **Archon task**: Will be created during implementation

### Task 13: Write Memory Persistence Tests
- **Description**: Test memory serialization and persistence
- **Files to create**:
  - `tests/unit/memory/test_memory_persistence.py`
  - `tests/integration/test_memory_persistence_integration.py`
- **Test scenarios**:
  - Save and load memory state
  - Memory persistence with sessions
  - Error handling for corrupt memory files
- **Archon task**: Will be created during implementation

### Task 14: Create MemoryTools Toolset (Optional)
- **Description**: Implement explicit memory operation tools
- **Files to create**:
  - `src/agent/memory/toolset.py`
- **Tools to implement**:
  - `remember_fact(fact: str, category: str = "general")`: Store a fact
  - `recall_memory(query: str, limit: int = 5)`: Search memories
  - `forget_memory(memory_id: str)`: Remove a memory
  - `list_memories(category: str = None)`: List all memories
- **Pattern**: Inherit from `AgentToolset`, use structured responses
- **Archon task**: Will be created during implementation

### Task 15: Write Memory Tools Tests
- **Description**: Test memory toolset functionality
- **Files to create**:
  - `tests/unit/memory/test_memory_toolset.py`
- **Test scenarios**:
  - Each tool with valid inputs
  - Error handling for invalid inputs
  - Tool integration with memory manager
- **Pattern**: Follow `test_hello_tools.py` structure
- **Archon task**: Will be created during implementation

### Task 16: Update Documentation
- **Description**: Add memory documentation and examples
- **Files to create/modify**:
  - `docs/design/memory-architecture.md` (new)
  - `docs/design/usage.md` (add memory section)
  - `.env.example` (add memory settings)
- **Content**:
  - Architecture overview
  - Configuration examples
  - Usage patterns
  - API reference
- **Archon task**: Will be created during implementation

### Task 17: Create ADR for Memory Architecture
- **Description**: Document the memory design decision
- **Files to create**:
  - `docs/decisions/0013-memory-architecture.md`
- **Sections**:
  - Context and problem statement
  - Decision outcome (in-memory with extensibility)
  - Alternatives considered (external services)
  - Consequences
- **Pattern**: Follow existing ADR template
- **Archon task**: Will be created during implementation

## Testing Strategy

### Unit Tests (Target: 100% coverage for memory components)

**Test Organization**:
```
tests/unit/memory/
├── __init__.py
├── test_memory_manager.py      # ABC and factory tests
├── test_memory_store.py         # In-memory storage tests
├── test_memory_persistence.py   # Serialization tests
└── test_memory_toolset.py       # Memory tools tests
```

**Key Test Cases**:

1. **MemoryManager Tests**:
   - Test ABC contract enforcement
   - Test helper methods for responses
   - Test initialization with config

2. **InMemoryStore Tests**:
   - Add messages with metadata
   - Search messages by keyword, date, type
   - Get recent messages with limit
   - Clear all memories
   - Filter by category/tags
   - Handle edge cases (empty store, invalid queries)

3. **MemoryPersistence Tests**:
   - Serialize/deserialize memory state
   - Handle JSON encoding errors
   - Version compatibility
   - File path sanitization

4. **MemoryTools Tests**:
   - Each tool with valid inputs
   - Structured response format
   - Error handling
   - Integration with memory manager

**Fixtures** (`tests/fixtures/memory.py`):
```python
@pytest.fixture
def mock_memory_config():
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test",
        memory_enabled=True,
        memory_type="in_memory"
    )

@pytest.fixture
def memory_manager(mock_memory_config):
    return InMemoryStore(mock_memory_config)

@pytest.fixture
def sample_messages():
    return [
        {"role": "user", "content": "My name is Alice"},
        {"role": "assistant", "content": "Nice to meet you, Alice!"}
    ]
```

### Integration Tests (Target: Full workflow coverage)

**Test Organization**:
```
tests/integration/
├── test_memory_integration.py          # Agent + memory workflow
└── test_memory_persistence_integration.py  # Session + memory persistence
```

**Key Test Cases**:

1. **Agent Memory Integration**:
   - Create agent with memory enabled
   - Run multiple interactions
   - Verify memory storage after each interaction
   - Search memories and verify results
   - Test with memory disabled (no errors)

2. **Session Persistence Integration**:
   - Save session with memory
   - Load session and verify memory restoration
   - Update memory and save again
   - Test memory migration (old sessions without memory)

3. **CLI Integration**:
   - Full session lifecycle with memory
   - Auto-save with memory
   - Session resume with memory restoration
   - Multiple sessions with independent memory

**Example Integration Test**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_with_memory_workflow(mock_config):
    """Test full agent workflow with memory enabled."""
    mock_config.memory_enabled = True
    mock_client = MockChatClient(response="Hello!")
    agent = Agent(config=mock_config, chat_client=mock_client)

    # First interaction
    thread = agent.get_new_thread()
    response1 = await agent.run("My name is Alice", thread=thread)

    # Verify memory stored
    memories = await agent.memory_manager.search("Alice")
    assert memories["success"] is True
    assert len(memories["result"]) > 0

    # Second interaction
    response2 = await agent.run("What's my name?", thread=thread)

    # Verify context maintained
    assert "Alice" in response2.lower() or memories found
```

### Edge Cases

1. **Memory Limits**:
   - Test behavior when memory storage reaches limit (if implemented)
   - Test memory cleanup strategies

2. **Concurrent Access**:
   - Multiple agents with same memory store
   - Thread safety for memory operations

3. **Corrupted Data**:
   - Handle corrupted memory files gracefully
   - Fallback to empty memory on load failure

4. **Migration**:
   - Old sessions without memory metadata
   - Version upgrades

5. **Memory Disabled**:
   - Agent works normally without memory
   - No errors when memory_enabled=False

## Acceptance Criteria

- [x] Memory module created with proper package structure
- [x] `MemoryManager` ABC implemented with complete interface
- [x] `InMemoryStore` implementation with search and filtering
- [x] Memory configuration fields added to `AgentConfig`
- [x] Agent class accepts and initializes memory manager
- [x] Memory ContextProvider created and integrated (better than middleware!)
- [ ] Memory events added to event system (optional - skipped)
- [x] `ThreadPersistence` extended with memory save/load
- [x] CLI session management restores memory
- [ ] Memory toolset implemented (optional) - skipped, not needed
- [x] All unit tests pass with 97% coverage for memory code
- [x] All integration tests pass with memory workflows
- [x] Documentation updated (docs/design/usage.md, ADR-0013)
- [x] `.env.example` updated with memory settings (enabled by default)
- [x] No regressions in existing functionality (308 tests passing)
- [x] Memory can be disabled via configuration
- [x] Memory persists across session restarts
- [x] Seamless UX for session resume

## Validation Commands

```bash
# Run all tests with coverage
uv run pytest --cov=src/agent --cov-fail-under=85 -v

# Run only memory unit tests
uv run pytest tests/unit/memory/ -v

# Run memory integration tests
uv run pytest tests/integration/ -k memory -v

# Run with memory markers
uv run pytest -m memory -v

# Type checking
uv run mypy src/agent/memory/

# Code quality
uv run black src/agent/memory/ tests/unit/memory/ tests/integration/test_memory*.py
uv run ruff check src/agent/memory/ tests/unit/memory/

# Manual testing: Enable memory and run agent
export MEMORY_ENABLED=true
uv run agent
# >> My name is Alice
# >> What's my name?  # Should remember "Alice"
```

## Notes

### Implementation Priorities

1. **Phase 1 is critical**: Must have solid abstractions before integration
2. **Keep it simple**: Start with in-memory, add external services later
3. **Backwards compatible**: Memory disabled by default, no breaking changes
4. **Test thoroughly**: Memory bugs are hard to debug, high test coverage essential

### Future Enhancements (Out of Scope for This Feature)

1. **External Memory Services**:
   - Mem0 integration for semantic memory
   - LangChain memory components
   - Redis for distributed memory
   - PostgreSQL for persistent memory

2. **Advanced Memory Features**:
   - Memory summarization (compress old conversations)
   - Memory importance scoring (prioritize retrieval)
   - Memory decay (forget old irrelevant information)
   - Semantic search (vector embeddings)
   - Memory categories (facts, preferences, tasks)

3. **Memory Management Tools**:
   - Memory export/import
   - Memory analytics dashboard
   - Memory debugging tools

4. **Performance Optimizations**:
   - Memory indexing for fast search
   - Lazy loading for large memory stores
   - Memory pagination

### Key Architectural Decisions

1. **Why In-Memory First?**
   - Simplest to implement
   - No external dependencies
   - Framework provides built-in support
   - Can be extended to external services later

2. **Why Extend ChatMessageStore?**
   - Framework abstraction designed for this
   - Consistent with Agent Framework patterns
   - Provides thread integration out of the box

3. **Why Separate Memory from ThreadPersistence?**
   - Single responsibility principle
   - Memory might be used independently
   - Easier testing and maintenance
   - Future: Share memory across threads

4. **Why Optional Memory Tools?**
   - Explicit memory ops useful for debugging
   - Some use cases need programmatic memory control
   - LLM can decide when to use memory tools
   - Follows existing toolset pattern

### Patterns Discovered from Codebase

1. **Config-First Design**: All features controlled via `AgentConfig`
2. **Dependency Injection**: Pass dependencies via constructor
3. **ABC for Extensibility**: Use ABC for components that may have multiple implementations
4. **Structured Responses**: Consistent response format for all operations
5. **Event Emission**: Emit events for monitoring and debugging
6. **Fallback Serialization**: Handle framework serialization failures gracefully
7. **Path Sanitization**: Always sanitize user-provided paths
8. **Metadata Tracking**: Track component state in index files

## Execution

This spec can be implemented using: `/implement docs/specs/agent-memory-support.md`

**Estimated Effort**: 3-5 days
- Phase 1: 1-2 days (core memory components)
- Phase 2: 1 day (agent integration)
- Phase 3: 1 day (persistence and CLI)
- Phase 4: 0.5 day (optional tools)
- Testing & Documentation: Throughout + 0.5 day final pass
