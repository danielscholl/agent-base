---
status: accepted
contact: danielscholl
date: 2025-11-09
deciders: danielscholl
---

# Memory Architecture for Conversation Context

## Context and Problem Statement

The agent needs to remember information from earlier in the conversation to provide personalized, context-aware responses. While thread-based persistence exists for session save/resume, we need a memory system that provides context within a single conversation session and across sessions. How should we implement conversation memory that integrates cleanly with the Microsoft Agent Framework?

## Decision Drivers

- **Framework Integration**: Must work with Agent Framework's patterns
- **Context Continuity**: Agent should remember user preferences, facts, and prior conversation
- **Automatic Operation**: Memory should work transparently without explicit user commands
- **Extensibility**: Architecture should support future memory backends (vector stores, external services)
- **Performance**: Memory retrieval must be fast enough for real-time conversation
- **Persistence**: Memories should persist across session restarts

## Considered Options

1. **Middleware-based memory** - Use agent middleware to intercept and store messages
2. **ContextProvider-based memory** - Use Agent Framework's ContextProvider pattern
3. **External memory service** - Integrate mem0, LangChain, or similar from the start
4. **Thread-only persistence** - Rely solely on thread serialization for context

## Decision Outcome

Chosen option: **"ContextProvider-based memory with in-memory storage"**, because:

- **Framework Native**: ContextProvider is the Agent Framework's intended pattern for memory
- **Full Message Access**: ContextProvider.invoked() receives both request AND response messages
- **Context Injection**: ContextProvider.invoking() can inject memories before LLM calls
- **Clean Separation**: Memory logic separated from middleware concerns
- **Proven Pattern**: butler-agent successfully uses this approach
- **Simple Start**: In-memory storage with no external dependencies
- **Extensible**: Can add vector stores, semantic search, etc. later

### Implementation Pattern

**ContextProvider Lifecycle:**
```python
class MemoryContextProvider(ContextProvider):
    async def invoking(self, messages, **kwargs) -> Context:
        # BEFORE LLM call: Inject relevant memories
        memories = await memory_manager.get_all()
        return Context(instructions="Previous conversation: ...")

    async def invoked(self, request_messages, response_messages, **kwargs):
        # AFTER LLM call: Store both user and assistant messages
        await memory_manager.add([user_msg, assistant_msg])
```

**Storage Architecture:**
```
~/.agent/
├── sessions/           # Thread persistence (existing)
│   └── session-1.json
└── memory/             # Memory persistence (new)
    └── session-1-memory.json
```

**Memory Flow:**
1. User sends message → ContextProvider.invoking() retrieves past memories
2. Memories injected as context instructions to LLM
3. LLM responds with full conversation awareness
4. ContextProvider.invoked() stores user message + assistant response
5. On exit: Memory saved to JSON file
6. On resume: Memory loaded back into memory manager

### Why Not Middleware?

**Middleware limitations discovered:**
- Agent middleware only sees **input messages**, not LLM responses
- `context.messages` doesn't accumulate - only contains current request
- No clean way to capture assistant responses
- Middleware is for cross-cutting concerns (logging, metrics), not memory

**ContextProvider advantages:**
- Designed specifically for this use case
- Has both `invoking()` and `invoked()` hooks
- Receives complete request/response pair
- Proper abstraction for memory/context injection

## Consequences

### Positive

- **Automatic Memory**: No user configuration needed (enabled by default)
- **Seamless UX**: Agent naturally remembers conversation context
- **Session Persistence**: Memories survive restarts via `--continue`
- **Framework Aligned**: Uses official pattern from Agent Framework
- **Clean Code**: Memory logic isolated in dedicated module
- **Well Tested**: 109 tests, 97% coverage for memory components

### Neutral

- **In-Memory Only**: Simple but limits to single-machine use
- **No Semantic Search**: Currently keyword-based search
- **Memory Limits**: No automatic cleanup or summarization yet

### Negative

- **None for current scope** - All tradeoffs are acceptable for MVP

## Future Enhancements

**Possible improvements** (out of scope for initial implementation):

1. **Semantic Memory**: Vector embeddings for intelligent retrieval
2. **Memory Summarization**: Compress old conversations automatically
3. **External Backends**: Support for mem0, LangChain, Redis, PostgreSQL
4. **Memory Analytics**: Insights about conversation patterns
5. **Selective Memory**: Importance scoring, decay over time
6. **Shared Memory**: Multi-user or multi-agent memory sharing

## Implementation Details

**Core Components:**
- `MemoryManager` (ABC): Interface for all memory implementations
- `InMemoryStore`: Default implementation with keyword search
- `MemoryContextProvider`: Agent Framework integration
- `MemoryPersistence`: JSON serialization utilities

**Configuration:**
```bash
MEMORY_ENABLED=true     # Enabled by default
MEMORY_TYPE=in_memory   # Future: mem0, langchain, etc.
MEMORY_DIR=~/.agent/memory
```

**Integration Points:**
- `Agent.__init__()`: Creates memory manager if enabled
- `Agent._create_agent()`: Attaches MemoryContextProvider
- `ThreadPersistence`: Extended with memory save/load methods
- `CLI session.py`: Saves/loads memory on exit/resume

## References

- [Microsoft Agent Framework ContextProvider docs](https://github.com/microsoft/agent-framework)
- butler-agent implementation (ai-examples/butler-agent/src/agent/memory.py)
- [ADR-0011: Session Management Architecture](./0011-session-management-architecture.md)
- [ADR-0006: Class-based Toolset Architecture](./0006-class-based-toolset-architecture.md)

## Related Decisions

- ADR-0011: Session Management - Memory extends session persistence
- ADR-0006: Toolset Architecture - Memory follows same dependency injection pattern
- ADR-0008: Testing Strategy - Memory achieves 97% test coverage
