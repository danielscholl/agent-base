# Agent Base – Foundation Requirements Specification

## Document Information

**Purpose**: Define foundational requirements for a reliable, extensible agent platform that enables building specialized agents, multi-agent systems, and workflow orchestrations. This is infrastructure for agent builders, not a complete chatbot application.

**Audience**: Developers and architects building LLM-driven agent systems, multi-agent platforms, and workflow orchestrations

**Version**: 3.0 (Foundation Platform)
**Last Updated**: 2025-11-11

**Changelog**:
- v3.0 (2025-11-11): Restructured to separate foundation from vision; added discovered requirements
- v2.1 (2025-11-07): Base chatbot template
- v1.0: Initial specification

---

## Table of Contents

1. [Overview](#overview)
2. [Part 1: Foundation Requirements](#part-1-foundation-requirements)
3. [Part 2: Vision & Future Capabilities](#part-2-vision--future-capabilities)
4. [Part 3: Implementation Decisions](#part-3-implementation-decisions)

---

## Overview

### Purpose & Scope

**Agent Base** is foundational infrastructure for building LLM-powered agents. It provides:

- Reliable multi-provider LLM integration (OpenAI, Anthropic, Gemini, Azure, Local)
- Extensible tool integration pattern for adding capabilities
- Event-driven architecture for multi-agent coordination
- Session and memory persistence
- Observability and testing infrastructure

**What this IS**:
- Production-ready foundation for building specialized agents
- Reusable platform for multi-agent systems and workflows
- Reliable infrastructure with 85%+ test coverage

**What this is NOT**:
- A complete chatbot application with all end-user features
- Domain-specific agent (GitLab, Kubernetes, etc.)
- Final product for end users

### Key Principles

1. **Reliability First**: 85%+ test coverage, comprehensive error handling
2. **Extensibility**: Clean patterns for adding providers, tools, and capabilities
3. **Multi-Provider**: Avoid vendor lock-in, support diverse deployment needs
4. **Observability**: Production-grade monitoring and tracing
5. **Testability**: Free testing without API costs (MockChatClient, local models)
6. **Clean Architecture**: Dependency injection, event bus, no global state

---

## Part 1: Foundation Requirements

These requirements define the core infrastructure that specialized agents will build upon.

### Category: LLM Integration

#### FR-FOUND-1: Multi-Provider LLM Architecture

**Description**: Support multiple LLM providers to enable flexibility, cost optimization, offline operation, and compliance requirements.

**Requirements**:
- Support at minimum: OpenAI, Anthropic, Azure, and Local providers
- Unified configuration pattern across all providers
- Provider-specific validation on startup
- Graceful error messages for missing credentials
- Health check with connectivity testing
- Consistent AgentConfig interface regardless of provider

**Rationale**: Different agents/deployments need different providers:
- Development: Local Docker models (free)
- Production: OpenAI, Anthropic (quality)
- Enterprise: Azure (compliance)
- Google Cloud: Gemini (GCP integration)

**Implementation Status**: ✅ COMPLETE - 6 providers supported (see ADR-0003)

---

#### FR-FOUND-2: Natural Language Query Interface

**Description**: Accept natural language queries and provide coherent, context-aware responses using configured LLM provider.

**Requirements**:
- Accept free-form text queries in conversational language
- Interpret and respond according to user intent
- Support follow-up and clarification questions
- Maintain conversational context within session
- Use clear, professional tone
- Support both interactive and programmatic modes

**Example**:
```
User: "Explain how agents work."
Agent: "Agents are AI systems that can use tools and take actions..."

User: "Give me an example"
Agent: "For instance, a GitLab agent could review merge requests..."
```

**Implementation Status**: ✅ COMPLETE

---

#### FR-FOUND-3: Context Management Infrastructure

**Description**: Maintain conversation context and memory to enable coherent multi-turn conversations.

**Requirements**:
- Store and recall previous conversation turns
- Resolve pronouns and implicit references
- Support context reset (`/clear` command)
- Persist memory state with sessions
- Extensible memory backend (start with in-memory, support vector stores later)

**Architecture**:
- Use ContextProvider pattern (framework-native)
- Dual persistence: thread state + memory state
- Memory injected before LLM calls
- Both user and assistant messages stored

**Example**:
```
User: "Remember my name is Alice"
Agent: "Got it, Alice!"

User: "What's my name?"
Agent: "Your name is Alice."
```

**Implementation Status**: ✅ COMPLETE (see ADR-0013)

---

### Category: Agent Extensibility

#### FR-FOUND-4: Tool Integration Pattern

**Description**: Provide clean abstraction for adding capabilities through tools.

**Requirements**:
- Class-based toolset pattern (inherit from base)
- Automatic tool registration
- Type-safe tool parameters (Pydantic Field annotations)
- Structured tool responses (success/error format)
- Tool invocation tracing
- Tools receive configuration dependency injection

**Architecture**:
```python
class MyToolset(AgentToolset):
    async def my_tool(
        self,
        param: Annotated[str, Field(description="...")],
    ) -> dict:
        return self._create_success_response(result=data)
```

**Rationale**: Future agents add tools for domain-specific capabilities (GitLab API, K8s API, database queries, file operations, etc.)

**Implementation Status**: ✅ COMPLETE (see ADR-0006)

---

#### FR-FOUND-5: Event Bus for Component Coordination

**Description**: Enable loose coupling between components and support multi-agent coordination.

**Requirements**:
- Observer pattern event bus
- Components emit events without knowing subscribers
- Support multiple subscribers to same events
- Events for: tool start/complete, phase transitions, errors
- Enable external listeners (for multi-agent systems)

**Rationale**:
- Multi-agent systems need to coordinate through events
- Workflows need to observe agent progress
- Loose coupling enables testing and composition

**Example Use Cases**:
- Agent A completes task → Agent B receives event and starts
- Middleware emits tool events → Display renders tree
- Orchestrator observes multiple agent events

**Implementation Status**: ✅ COMPLETE (see ADR-0005)

---

#### FR-FOUND-6: Middleware Integration Pattern

**Description**: Support cross-cutting concerns through middleware.

**Requirements**:
- Middleware hooks before/after LLM calls
- Access to messages and tool calls
- Emit events for monitoring
- Multiple middleware can compose
- Middleware receives configuration

**Use Cases**:
- Logging and audit trails
- Performance monitoring
- Custom event emission
- Request/response transformation

**Implementation Status**: ✅ COMPLETE (see ADR-0012)

---

### Category: State Management

#### FR-FOUND-7: Session Persistence

**Description**: Save and restore conversation state across restarts.

**Requirements**:
- Auto-save on exit
- Resume last session (`--continue`)
- List available sessions
- Session metadata (name, created, message count, first message)
- Serialize thread state
- Serialize memory state
- Both saved together, restored together

**Storage Pattern**:
```
~/.agent/
├── sessions/
│   ├── index.json           # Metadata
│   └── session-name.json    # Thread state
└── memory/
    └── session-name.json    # Memory state
```

**Implementation Status**: ✅ COMPLETE (see ADR-0011)

---

#### FR-FOUND-8: Memory Architecture

**Description**: Extensible memory system using framework-native patterns.

**Requirements**:
- ContextProvider pattern (not middleware)
- Abstract MemoryManager interface
- Pluggable storage backends (InMemoryStore default)
- Memory persistence with sessions
- Future: support vector stores, semantic search, external services (mem0)

**Rationale**: Future agents might need:
- Semantic memory (vector embeddings)
- Long-term memory across sessions
- Shared memory across multiple agents
- External memory services

**Implementation Status**: ✅ COMPLETE with extensibility (see ADR-0013)

---

#### FR-FOUND-9: Configuration Management

**Description**: Clean, validated configuration system.

**Requirements**:
- Environment-based configuration (`.env`)
- Provider-specific validation
- Type-safe configuration class (Pydantic or dataclass)
- Validation on startup with clear error messages
- Support for config overrides (CLI flags)
- No hardcoded defaults in code (all in `.env.example`)

**Example**:
```python
settings = load_config()  # Loads from file + env merge
# Validation happens automatically during load
```

**Implementation Status**: ✅ COMPLETE

---

### Category: Operations & Reliability

#### TR-FOUND-1: Testing Strategy

**Description**: Comprehensive testing strategy that enables confident iteration.

**Requirements**:
- Minimum 85% code coverage
- Four test types: unit, integration, validation, LLM
- Clear separation: free tests vs paid tests (LLM API calls)
- MockChatClient for testing without API costs
- Test markers for selective execution
- Parallel test execution support
- Fast feedback loop (unit tests ~2-4s)

**Test Organization**:
- `tests/unit/` - Free, fast, isolated
- `tests/integration/` - Free, component interaction with mocks
- `tests/validation/` - Free, CLI subprocess tests
- `tests/integration/llm/` - Paid, real API calls (opt-in)

**Rationale**: Foundation code must be reliable for agent builders to trust it.

**Implementation Status**: ✅ COMPLETE (see ADR-0008)

---

#### TR-FOUND-2: Observability & Tracing

**Description**: Production-grade monitoring using OpenTelemetry.

**Requirements**:
- OpenTelemetry integration (industry standard)
- Trace LLM calls (latency, tokens, errors)
- Trace tool invocations
- Trace session operations
- Export to Azure Application Insights or local dashboard
- Opt-in (zero impact when disabled)
- Sensitive data filtering

**Rationale**:
- CRITICAL for debugging multi-agent systems
- Production monitoring
- Performance optimization
- Cost tracking

**Example**:
```bash
/telemetry start  # Start local Aspire Dashboard
export ENABLE_OTEL=true
agent -p "test"
# View traces at http://localhost:18888
```

**Implementation Status**: ✅ COMPLETE (see ADR-0014)

---

#### TR-FOUND-3: Health Check & Diagnostics

**Description**: Verify system configuration and provider connectivity.

**Requirements**:
- `--check` command to validate setup
- Test connectivity to all configured providers
- Display system information (Python, platform, data directory)
- Show Docker status and available models
- Provider status with credentials masking
- Clear error messages with resolution suggestions

**Example Output**:
```
System:
  ◉ Python 3.12.10
  ◉ Data: ~/.agent

LLM Providers:
✓ ◉ Local (ai/phi4) · http://localhost:12434
  ◉ OpenAI (gpt-5-mini) · ****R02TAA
```

**Implementation Status**: ✅ COMPLETE

---

#### TR-FOUND-4: Error Handling Patterns

**Description**: Consistent error handling with custom exception hierarchy.

**Requirements**:
- Custom exception hierarchy for different error types
- Structured error responses from tools
- Graceful degradation on failures
- Clear error messages with actionable guidance
- Error propagation patterns documented

**Implementation Status**: ✅ COMPLETE (see ADR-0004)

---

### Category: User Interface

#### UI-FOUND-1: Interactive Mode

**Description**: REPL-style interactive conversation mode.

**Requirements**:
- Prompt with status bar (path, git branch)
- Command history (up/down arrows, persistent across sessions)
- Keyboard shortcuts (ESC clear prompt, Ctrl+C interrupt, Ctrl+D exit)
- Interactive commands (`/help`, `/clear`, `/continue`, `/purge`)
- Shell command execution (`!command`)
- Session auto-save on exit

**Implementation Status**: ✅ COMPLETE

---

#### UI-FOUND-2: Single Query Mode

**Description**: Execute one prompt and exit (for scripting, automation).

**Requirements**:
- `-p "prompt"` flag for single query
- Clean output by default (no progress indicators)
- `--verbose` flag for detailed execution tree
- Exit code on completion
- Suitable for shell scripts and automation

**Example**:
```bash
agent -p "Say hello"        # Clean output
agent -p "Say hello" --verbose  # With execution tree
```

**Implementation Status**: ✅ COMPLETE

---

#### UI-FOUND-3: Display Mode Flexibility

**Description**: Different display modes for different use cases.

**Requirements**:
- **Minimal mode**: Completion summary with timing (default interactive)
- **Verbose mode**: Full execution tree with phases and tools
- **Quiet mode**: Response only, no metadata (default single-query)
- Event-driven display updates
- Real-time progress indicators

**Rationale**: Different contexts need different verbosity:
- Scripts need quiet
- Debugging needs verbose
- Interactive needs balance

**Implementation Status**: ✅ COMPLETE (see ADR-0010)

---

#### UI-FOUND-4: Session Management Commands

**Description**: Commands for managing conversation sessions.

**Requirements**:
- `/clear` - Reset conversation context
- `/continue` - Resume previous session with picker UI
- `/purge` - Delete all agent data with granular confirmations
- `/help` - Show available commands
- `exit` - Exit with auto-save
- Session listing with metadata

**Implementation Status**: ✅ COMPLETE

---

### Category: Security

#### SEC-FOUND-1: Credential Management

**Description**: Secure credential storage and validation.

**Requirements**:
- Environment variables for all credentials
- Never log or display full credentials (mask in output)
- Validate credentials on startup
- Clear error messages for missing credentials
- Support credential rotation (read from env on each startup)

**Supported Authentication Patterns**:
- API Keys (OpenAI, Anthropic, Gemini)
- Azure CLI authentication (Azure OpenAI, AI Foundry)
- GCP credentials (Gemini Vertex AI)
- No authentication (Local Docker models)

**Implementation Status**: ✅ COMPLETE

---

#### SEC-FOUND-2: Secure Communication

**Description**: All external communications use secure protocols.

**Requirements**:
- HTTPS/TLS for all LLM provider connections
- Framework handles secure communication
- No plaintext credentials in transit
- Certificate validation

**Implementation Status**: ✅ COMPLETE (framework-provided)

---

### Category: Technical Architecture

#### TR-FOUND-1: Async Architecture

**Description**: Non-blocking I/O for all external operations.

**Requirements**:
- Async/await throughout codebase
- Async LLM calls (chat, streaming)
- Async tool invocations
- Async context managers for resources
- Proper cleanup (close HTTP clients)

**Rationale**: Required for:
- Multi-agent parallel execution
- Workflow orchestration
- Responsive interactive mode

**Implementation Status**: ✅ COMPLETE

---

#### TR-FOUND-2: Modular Architecture

**Description**: Clean separation of concerns with dependency injection.

**Requirements**:
- No global state
- Dependency injection at construction time
- Event bus for loose coupling
- Pluggable components (toolsets, memory, providers)
- Type hints throughout

**Architecture**:
```
CLI (Typer)
  ↓
Agent (LLM orchestration, 6 providers)
  ├─→ Tools (extensible toolsets)
  ├─→ Memory (ContextProvider)
  └─→ Middleware (event emitters)
       ↓
     Event Bus
       ↓
     Display (Rich rendering)
```

**Implementation Status**: ✅ COMPLETE (see architecture.md)

---

#### TR-FOUND-3: Type Safety

**Description**: Type hints throughout for compile-time verification.

**Requirements**:
- Type hints on all public APIs
- Pydantic models for data validation
- MyPy type checking in CI
- No `Any` types without justification

**Implementation Status**: ✅ COMPLETE

---

#### TR-FOUND-4: Structured Tool Responses

**Description**: Consistent response format from all tools.

**Requirements**:
- Success: `{"success": true, "result": any, "message": str}`
- Error: `{"success": false, "error": str, "message": str}`
- Helper methods: `_create_success_response()`, `_create_error_response()`
- Test assertions: `assert_success_response()`, `assert_error_response()`

**Rationale**: Predictable format enables testing and LLM consumption.

**Implementation Status**: ✅ COMPLETE (see ADR-0007)

---

### Category: Data & Persistence

#### FR-FOUND-10: Session Serialization

**Description**: Serialize and deserialize conversation state.

**Requirements**:
- Save thread state (conversation history)
- Save memory state (context)
- JSON serialization
- Metadata tracking (created, updated, message count)
- Sanitized session names (prevent path traversal)

**Storage**:
```
~/.agent/
├── sessions/
│   ├── index.json
│   └── 2025-11-11-10-30-00.json
└── memory/
    └── 2025-11-11-10-30-00.json
```

**Implementation Status**: ✅ COMPLETE

---

## Part 2: Vision & Future Capabilities

These are application-level features that can be built on the foundation or added to specialized agents.

### Vision: Enhanced User Features

#### VISION-1: Advanced Session Management

**Future capabilities**:
- Search sessions by content or date
- Filter sessions by provider or tool usage
- Session tagging and categorization
- Bulk session operations
- Session analytics

**Foundation Provides**: Storage, metadata, session listing

---

#### VISION-2: Session Export

**Future capabilities**:
- Export to clean JSON (not internal serialization format)
- Export to Markdown (formatted conversation)
- Export to HTML (rich formatting)
- Selective export (date range, topic filter)

**Foundation Provides**: Raw session data access

---

#### VISION-3: Conversation Summarization

**Future capabilities**:
- `/summarize` command for ongoing conversation
- Automatic periodic summaries
- Summary on session resume
- Key points extraction

**Foundation Provides**: Memory access, LLM access, command pattern

**Note**: Can be implemented as tool or interactive command

---

#### VISION-4: Rich Data Visualization

**Future capabilities for specialized agents**:

**Domain-Specific Tables** (GitLab agent, K8s agent, etc.):
```
Open Merge Requests (8 total):

MR     Title                    Status      Age
─────────────────────────────────────────────────
!42    Fix authentication bug   ✅ Approved  3d
!18    Add logging feature      ⏳ Pending   5d
```

**Dashboard Cards** (monitoring agents):
```
┌─ Cluster Status ──────────────┐
│ Nodes: 3 (all ready)          │
│ Pods: 45 running, 2 pending   │
│ AddOns: NGINX ✓, Flux ✓       │
└───────────────────────────────┘
```

**Foundation Provides**: Rich library, display abstraction, tool pattern

**Note**: These are agent-specific outputs, not foundation features

---

#### VISION-5: Advanced LLM Configuration

**Future capabilities**:
- Temperature adjustment per agent or per request
- max_tokens configuration
- top_p, frequency_penalty, presence_penalty
- Provider-specific parameters
- Per-tool LLM parameter override

**Foundation Provides**: AgentConfig extension pattern

**Rationale**: Different agents need different LLM behaviors:
- Code agent: temperature=0.2 (consistent)
- Creative agent: temperature=0.9 (varied)
- Foundation uses sensible defaults

**Status**: Explicitly deferred - not needed for foundation

---

### Vision: Multi-Agent & Workflow Capabilities

#### VISION-6: Multi-Agent Orchestration

**Future capabilities**:
- Agent-to-agent communication via event bus
- Shared memory across agents
- Agent coordination patterns
- Workflow definitions
- Task delegation between agents

**Foundation Provides**: Event bus, memory architecture, async support

---

#### VISION-7: Workflow Orchestration

**Future capabilities**:
- Sequential workflow steps
- Parallel agent execution
- Conditional branching
- Error recovery in workflows
- Workflow state persistence

**Foundation Provides**: Async architecture, session management, event coordination

---

### Vision: Enterprise Features

#### VISION-8: Security Enhancements

**Future capabilities**:
- Encryption at rest for session files
- Audit logging
- Role-based access control
- Credential rotation automation
- Compliance reporting

**Foundation Provides**: Pluggable persistence, credential validation, observability hooks

**Note**: Many of these are deployment concerns (encrypted volumes, secret management)

---

#### VISION-9: Performance & Optimization

**Future capabilities**:
- Response caching
- Parallel tool execution
- Rate limit management across providers
- Token usage tracking and budgeting
- Provider failover/fallback

**Foundation Provides**: Multi-provider support, async architecture, observability

---

## Part 3: Implementation Decisions

This section documents how our implementation differs from or extends the original specification.

### Data Models (TR-3 Divergence)

**Original Spec**: Custom Message and SessionContext dataclasses

**Actual Implementation**: Use Microsoft Agent Framework's message models

**Rationale**:
- Framework provides well-tested message models
- Better integration with framework features
- Avoid reinventing serialization
- Simpler maintenance

**Status**: Intentional divergence, better approach

---

### Architecture Enhancements

**Beyond Original Spec**:

1. **Event-Driven Architecture** - Not required, but better for extensibility
2. **Display Mode System** - Not specified in detail, significantly better UX
3. **Provider Health Checks** - Not required, very valuable operationally
4. **Keyboard Shortcut System** - Not specified, better UX
5. **Extensible Command Pattern** - Interactive commands beyond what spec mentioned

**Rationale**: These emerged as we built production-quality foundation

---

### Scope Clarifications

**Out of Scope for Foundation** (Explicitly):

1. **Model Parameter Tuning** (temperature, top_p, etc.)
   - Agent-specific concern, not foundation
   - Sensible defaults sufficient for base

2. **Domain-Specific Tools** (GitLab, K8s, databases, etc.)
   - Built by specialized agents on top of foundation
   - Foundation provides AgentToolset pattern

3. **Advanced Data Formatting** (domain-specific tables, cards)
   - Agent-specific outputs, not foundation
   - Foundation provides Rich library and display patterns

4. **Encryption at Rest**
   - Deployment concern (encrypted volumes, secret managers)
   - Foundation provides pluggable persistence

5. **Information Synthesis Features** (FR-3, FR-4)
   - LLM native capabilities, not implementation concern
   - Any LLM provides these out of box

---

## Foundation Completeness Assessment

### ✅ Foundation Requirements: COMPLETE

All core infrastructure is production-ready:
- ✅ Multi-provider LLM (6 providers)
- ✅ Tool integration pattern
- ✅ Event bus & loose coupling
- ✅ Memory & context management
- ✅ Session persistence
- ✅ Testing strategy (407 tests, 85%+ coverage)
- ✅ Observability (OpenTelemetry)
- ✅ Health checks
- ✅ Configuration management
- ✅ Async architecture
- ✅ Error handling
- ✅ Interactive & programmatic modes
- ✅ Display flexibility
- ✅ Security (credential management)

### Next Phase: Build On Foundation

The foundation is ready for:

1. **Specialized Agents** - Build domain-specific agents (GitLab, K8s, database, code review)
2. **Multi-Agent Systems** - Coordinate multiple agents via event bus
3. **Workflow Orchestration** - Chain agents for complex tasks
4. **Custom Tools** - Add domain-specific capabilities via AgentToolset pattern
5. **Production Deployments** - Observability and reliability already built-in

---

## References

**Architecture Documents**:
- [architecture.md](./architecture.md) - Complete architectural overview
- [ADR-0003](../decisions/0003-multi-provider-llm-architecture.md) - Multi-provider strategy
- [ADR-0006](../decisions/0006-class-based-toolset-architecture.md) - Tool integration pattern
- [ADR-0008](../decisions/0008-testing-strategy-and-coverage-targets.md) - Testing strategy
- [ADR-0013](../decisions/0013-memory-architecture.md) - Memory architecture
- [ADR-0014](../decisions/0014-observability-integration.md) - Observability integration

**Contributing**:
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development guide
- [tests/README.md](../../tests/README.md) - Testing workflows

---

**End of Requirements Document**
