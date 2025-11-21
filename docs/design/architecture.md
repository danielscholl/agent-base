# Architecture

Architectural patterns and design decisions for agent-base.

## Overview

Agent-base uses a class-based architecture with dependency injection to avoid global state and tight coupling. The design prioritizes testability, type safety, and extensibility while maintaining test coverage above 85%.

## Design Principles

1. **Testability** - All dependencies injected via constructors, enabling easy mocking without real LLM calls
2. **Type Safety** - Type hints throughout for compile-time verification
3. **Loose Coupling** - Event bus for component communication without direct dependencies
4. **No Global State** - Class-based design with explicit dependency ownership
5. **High Coverage** - 85%+ test coverage enforced, with clear separation between free and paid tests

## Key Patterns

### Dependency Injection

**Rationale:** Enables testing without real LLM calls or external services.

All components receive dependencies through constructors. Toolsets receive `AgentConfig`, Agent accepts `chat_client` for testing, memory manager is injected into Agent.

**What it enables:**
- Test with `MockChatClient` instead of real LLM providers
- Run full test suite without API costs
- Multiple configurations simultaneously
- No initialization order requirements

See ADR-0006 for detailed rationale on class-based design.

### Event-Driven Architecture

**Rationale:** Middleware and display components should not know about each other.

Observer pattern via event bus. Middleware emits events (`TOOL_START`, `TOOL_COMPLETE`), display subscribes and renders. Neither component imports the other.

**What it enables:**
- Test middleware without display
- Swap display implementations
- Add monitoring without changing middleware
- Multiple subscribers to same events

See ADR-0005 for detailed analysis of alternatives.

### Structured Responses

**Rationale:** Consistent format enables predictable error handling and testing.

All tools return:
```python
{"success": bool, "result": any, "message": str}  # Success
{"success": bool, "error": str, "message": str}   # Error
```

**What it enables:**
- Uniform error handling in tests (`assert_success_response`)
- Predictable LLM consumption
- Easy validation helpers

See ADR-0007 for response format specification.

### ContextProvider Pattern

**Rationale:** Memory needs both request and response messages to store complete conversations.

Microsoft Agent Framework's ContextProvider receives both pre-LLM messages (`invoking`) and post-LLM messages (`invoked`). Middleware only sees one direction.

**Why ContextProvider instead of middleware:**
- Receives both request AND response messages
- Can inject context before LLM call
- Framework's intended pattern for memory/context
- Proven pattern from production implementations

See ADR-0013 for memory architecture decisions.

## Component Overview

```
┌──────────────────────────────────────────────────────┐
│                    CLI (Typer)                       │
│  Interactive shell, session management, shortcuts    │
└─────────────────────┬────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                     Agent                            │
│  LLM orchestration (6 providers), tool registration │
└──┬──────────────┬──────────────┬────────────────────┘
   │              │              │
   ▼              ▼              ▼
┌──────┐   ┌──────────┐   ┌──────────────┐
│Tools │   │  Memory  │   │  Middleware  │
│      │   │(Context  │   │(emit events) │
│      │   │Provider) │   │              │
└──┬───┘   └──────────┘   └──────┬───────┘
   │                             │
   │       ┌──────────┐          │
   └──────►│  Skills  │          │
           │(Context  │          │
           │Provider) │          │
           └──────────┘          │
                                 ▼
                          ┌──────────────┐
                          │  Event Bus   │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │   Display    │
                          │ (Rich/Tree)  │
                          └──────────────┘
```

### Major Components

**CLI** (`cli/`) - Interactive interface with Typer, prompt_toolkit, session management

**Agent** (`agent.py`) - Core orchestration, multi-provider LLM support (6 providers), dependency injection

**Toolsets** (`tools/`) - Class-based tool implementations inheriting from `AgentToolset`

**Skills** (`skills/`) - Progressive disclosure system for optional capabilities, ContextProvider-based documentation injection

**Providers** (`providers/`) - Custom LLM provider implementations (Gemini custom client)

**Memory** (`memory/`) - ContextProvider-based conversation storage with in-memory backend

**Event Bus** (`events.py`) - Observer pattern for loose coupling between middleware and display

**Display** (`display/`) - Rich-based execution visualization, tree hierarchy, multiple modes

**Persistence** (`persistence.py`) - Session and memory state serialization

See `src/agent/` for implementation details.

## Anti-Patterns Avoided

**Global State** - All state managed through class instances with explicit dependencies. No module-level variables holding configuration or managers.

**Runtime Initialization** - Dependencies injected at construction time, not lazily initialized with runtime checks. No `if not _manager: raise RuntimeError`.

**Tight Coupling** - Event bus enables component independence. Display doesn't import middleware, middleware doesn't import display.

**Direct LLM Calls in Tests** - Dependency injection allows `MockChatClient` in all tests except explicit LLM integration tests (marked with `@pytest.mark.llm`).

See ADR-0006 for detailed examples of avoided patterns.

## Testing Approach

### Test Organization

Tests separated by type with clear cost implications:

- **Unit** - Isolated component tests (free, fast)
- **Integration** - Component interaction with `MockChatClient` (free, moderate)
- **Validation** - CLI subprocess tests (free, moderate)
- **LLM** - Real API calls (costs money, opt-in via marker)

Only LLM tests make API calls. All others run in CI for free.

### Architecture Enables Testing

**Dependency injection:**
```python
# Production: real LLM client
agent = Agent(config)

# Testing: mock client
agent = Agent(config, chat_client=MockChatClient(response="test"))
```

**Event bus for display testing:**
```python
# Test middleware without display
bus = EventBus()
listener = MockListener()
bus.subscribe(listener)
run_middleware()
assert listener.received_event(EventType.TOOL_START)
```

**Structured responses for validation:**
```python
result = await tool.my_function("input")
assert_success_response(result)  # Validates format
```

See `tests/README.md` for comprehensive testing guide.

## Configuration Architecture

Multi-provider support via `AgentConfig`:

- **JSON-based configuration** - Primary config at `~/.agent/settings.json`
- **Environment overrides** - Environment variables can override JSON settings
- **Validation** - Provider-specific validation on startup
- **Memory settings** - Enable/disable, type selection, history limits
- **Centralized defaults** - All defaults in `config/defaults.py`

**Supported providers:**
- Local (Docker Desktop models, free, offline)
- OpenAI (direct API)
- Anthropic (direct API)
- Gemini (Google Gemini API or Vertex AI)
- Azure OpenAI (Azure-hosted)
- Azure AI Foundry (managed platform)

Provider selection changes chat client implementation but Agent interface remains identical.

See ADR-0003 for multi-provider architecture strategy.

## Provider Architecture

### Design Decision

Support multiple LLM providers with three implementation patterns.

**Rationale:**
- Enable user flexibility (cost, features, compliance, offline)
- Avoid vendor lock-in to any single provider
- Leverage Microsoft Agent Framework's multi-provider support
- Support free local development alongside cloud providers
- Meet diverse user needs (students, enterprises, privacy-conscious)

**Implementation patterns:**

1. **Framework clients** - OpenAI, Anthropic, Azure
   - Use official `agent-framework-{provider}` packages
   - Zero custom client code needed
   - Example: `OpenAIChatClient`, `AnthropicChatClient`

2. **Custom clients** - Gemini
   - Extend `BaseChatClient` for providers without framework package
   - Implement message conversion and API integration
   - Example: `GeminiChatClient` using `google-genai` SDK

3. **Client reuse** - Local
   - Reuse existing framework client with different endpoint
   - Example: `OpenAIChatClient` pointed at Docker Model Runner
   - Works with any OpenAI-compatible API

**Provider capabilities:**
- **Local**: Free, offline, privacy (qwen3, phi4, llama3.2 via Docker)
- **OpenAI**: Latest models, highest quality (GPT-4o, o1)
- **Anthropic**: Long context windows, constitutional AI (Claude)
- **Gemini**: Multimodal inputs, Google Cloud integration, 2M token context
- **Azure OpenAI**: Enterprise compliance, government clouds, data residency
- **Azure AI Foundry**: Managed platform, model catalog, unified deployment

**Decision tree for new providers:**
```
Does framework package exist?
├─ YES: Use framework client (OpenAI, Anthropic)
└─ NO: Is API OpenAI-compatible?
   ├─ YES: Reuse OpenAIChatClient (Local)
   └─ NO: Create custom client (Gemini)
```

See ADR-0003 for complete provider strategy and decision tree.
See ADR-0015 for Gemini custom client implementation.
See ADR-0016 for Local Docker Model Runner integration.

## Memory Architecture

### Design Decision

Use Microsoft Agent Framework's ContextProvider pattern rather than middleware.

**Rationale:**
- ContextProvider receives both request and response messages
- `invoking()` can inject context before LLM call
- `invoked()` can store complete conversation turn
- Framework's intended pattern for memory management

**Components:**
- `MemoryManager` - Abstract interface for extensibility
- `InMemoryStore` - Default implementation with search
- `MemoryContextProvider` - Framework integration
- `MemoryPersistence` - Save/load with sessions

**Future extensibility:**
- Swap `InMemoryStore` for external services (mem0, langchain)
- Memory manager interface remains stable
- Agent code unchanged

See ADR-0013 for detailed memory architecture analysis.

## Skills Architecture

### What are Skills?

Skills are a **packaging and distribution mechanism** for optional agent capabilities. They provide a way to add specialized functionality without modifying core code or bloating context for all users.

**Key insight:** Not every agent needs every capability. Skills let users install only what they need, with documentation loaded only when relevant.

### Tool Types Comparison

| Type | Loading | Enable/Disable | Documentation | Location |
|------|---------|----------------|---------------|----------|
| **Core Tools** | Hardcoded in agent.py | Always on | Docstrings only (always in context) | `src/agent/tools/` |
| **Bundled Skills** | Auto-discovered | Yes | SKILL.md (progressive) + docstrings (always) | `src/agent/_bundled_skills/` |
| **Plugin Skills** | Installed from git | Yes | SKILL.md (progressive) + docstrings (always) | `~/.agent/skills/` |

**Example:**
- Core tool: `read_file()` - 32 token docstring, always in context
- Skill tool: `greet_in_language()` - 23 token docstring (always) + share of 448 token SKILL.md (progressive)

### Skill Contents

Skills can contain **two types of capabilities**:

**1. Toolsets (Python classes)**
- LLM-callable methods inheriting from `AgentToolset`
- Example: `HelloExtended` with `greet_in_language()`, `greet_multiple()`
- Tool docstrings: **Always in context when skill enabled** (not progressive)
- Available in both bundled and plugin skills

**2. Scripts (Standalone executables)**
- PEP 723 Python files with inline dependencies
- Executed via `script_run` wrapper tool
- Example: `advanced_greeting.py` in hello-extended
- Scripts themselves: **Never in LLM context** (only script_run is)
- Available in both bundled and plugin skills

### What is Progressive?

**Progressive (loaded only when triggers match):**
- ✓ SKILL.md documentation (triggers, examples, detailed usage)
- Example: hello-extended SKILL.md = 448 tokens (progressive)

**NOT Progressive (always in context if skill enabled):**
- ✗ Tool method docstrings
- ✗ Script_run wrapper documentation
- Example: `greet_in_language()` docstring = 23 tokens (always)

### Three-Tier Progressive Disclosure

SKILL.md documentation uses three tiers based on relevance:

**Tier 1: Breadcrumb (~10 tokens)** - Skill enabled but triggers don't match
```
[3 skills available]
```
LLM knows skills exist without wasting context.

**Tier 2: Registry (~15 tokens/skill)** - User asks "What can you do?"
```
## Available Skills
- **hello-extended**: Multi-language greetings
- **web**: Search and fetch web content
```
Brief menu of available capabilities.

**Tier 3: Full Docs (~400-1000 tokens)** - Triggers match user query
```xml
<skill-hello-extended>
  <triggers>...</triggers>
  <tools>...</tools>
  <examples>...</examples>
  <lang-map>...</lang-map>
</skill-hello-extended>
```
Complete documentation with usage details.

### Token Cost Examples

**Scenario: hello-extended skill enabled (3 total skills installed)**

**Query: "What is 2+2?"** - No triggers match
```
System Prompt:                    1000 tokens
Tool docstrings (always):          302 tokens  ← hello-extended tools
Skills context (Tier 1):            10 tokens  ← [3 skills available]
Other context:                     200 tokens
Total:                            1512 tokens
```

**Query: "Say hello in French"** - hello-extended triggers match
```
System Prompt:                    1000 tokens
Tool docstrings (always):          302 tokens  ← hello-extended tools
Skills context (Tier 3):           448 tokens  ← hello-extended SKILL.md
Other context:                     200 tokens
Total:                            1950 tokens
```

**Impact:** Progressive disclosure saves 438 tokens (448 - 10) on irrelevant queries while keeping tool methods available.

### Trigger Matching

`SkillContextProvider` analyzes each user message using triggers defined in SKILL.md:

1. **Keywords** - "hello", "greet", "bonjour"
2. **Verbs** - "calculate", "compute"
3. **Patterns** - Regex like `\d+\s*[+\-*/]\s*\d+` for "what is 5+3?"
4. **Skill name** - "use the weather skill"

Matching uses word boundaries and operates on single messages (not conversation history) for speed and predictability.

### Bundled vs Plugin Skills

**Bundled Skills:**
- Shipped with agent in `src/agent/_bundled_skills/`
- Auto-discovered on startup
- Maintained by core team
- Example: `hello-extended`

**Plugin Skills:**
- Installed from git via `agent skill install <url>`
- Stored in `~/.agent/skills/`
- Community-contributed
- Examples: `web`, `kalshi-markets`, `osdu`

**Both types:**
- Use SKILL.md manifest with YAML frontmatter
- Can include toolsets and/or scripts
- Can be enabled/disabled
- Use progressive disclosure for documentation

### Architecture Benefits

- **Users:** Install only needed capabilities, no performance penalty for unused skills
- **Developers:** Add capabilities without core PRs, test in isolation, distribute as git repos
- **System:** Small context window, isolated dependencies, clear core/extension separation

### Implementation

**SkillContextProvider** (like MemoryContextProvider):
- Receives incoming message via `invoking()`
- Matches triggers to decide which tier
- Returns `Context(instructions=relevant_docs)` to inject

**Two metadata systems:**
- `SkillRegistry` - Persistent install metadata (where, when, enabled status)
- `SkillDocumentationIndex` - Runtime documentation (triggers, instructions)

See ADR-0019 for detailed progressive disclosure decisions and token measurements.

## Session Management

Sessions persist both thread state (conversation history) and memory state (long-term context).

**Design decision:** Separate but coordinated persistence.

**Rationale:**
- Thread persistence from framework (serializes conversation)
- Memory persistence custom (serializes memory store)
- Saved together, restored together
- Future: share memory across threads

**Implementation:**
- `ThreadPersistence.save_thread()` - Conversation history
- `ThreadPersistence.save_memory_state()` - Memory store
- Both serialized to session directory
- Metadata tracks both files

## CLI Architecture

**Design decision:** Typer for commands, prompt_toolkit for interactive shell, Rich for display.

**Rationale:**
- Typer provides argument parsing and help
- prompt_toolkit enables advanced input (history, shortcuts)
- Rich provides formatted output without manual terminal codes
- All three integrate cleanly

**Interactive commands:** Internal commands (`/clear`, `/continue`) handled before LLM

**Shell commands:** Prefix `!` executes system commands without exiting

**Keyboard shortcuts:** Extensible handler system via `utils/keybindings/`

See ADR-0009 for CLI framework selection.

## Display Architecture

**Design decision:** Event-driven updates via Rich Live display.

**Rationale:**
- Middleware emits events, doesn't render
- Display subscribes to events, updates live
- Swap display modes without changing middleware
- Test middleware without display

**Display modes:**
- Default: Completion summary with timing
- Verbose: Full execution tree
- Quiet: Response only

Tree rendering uses Rich's tree structure, updated incrementally as events arrive.

See ADR-0010 for display format decisions.

## Observability Architecture

### Design Decision

Optional OpenTelemetry integration for production monitoring.

**Rationale:**
- Production visibility into agent behavior and performance
- Trace LLM calls, tool invocations, and execution flow
- Industry-standard telemetry (OpenTelemetry)
- Zero impact when disabled (opt-in only)
- Supports both cloud (Azure) and local (Aspire Dashboard) exporters

**Implementation:**
- Microsoft Agent Framework provides built-in OpenTelemetry instrumentation
- Automatic span creation for agent operations and LLM calls
- Export to Azure Application Insights or local Aspire Dashboard
- Configurable via `ENABLE_OTEL` environment variable
- Sensitive data filtering via `ENABLE_SENSITIVE_DATA` flag

**Telemetry dashboard:**
```bash
# Start local Aspire Dashboard (Docker-based)
/telemetry start

# Enable telemetry
export ENABLE_OTEL=true

# View traces at http://localhost:18888
agent -p "test prompt"
```

**What gets traced:**
- Agent initialization and configuration
- LLM API calls (request/response, tokens, latency)
- Tool invocations and results
- Session management operations
- Error conditions and exceptions

**Privacy controls:**
- Prompt/response content excluded by default
- `ENABLE_SENSITIVE_DATA=true` includes full content for debugging
- Azure Application Insights for cloud monitoring
- Local-only option with Aspire Dashboard

See ADR-0014 for observability integration decisions.

## Design Decisions

Detailed rationale in Architecture Decision Records:

**Core Architecture:**
- [ADR-0001](../decisions/0001-module-and-package-naming-conventions.md) - Naming conventions
- [ADR-0003](../decisions/0003-multi-provider-llm-architecture.md) - Multi-provider strategy
- [ADR-0004](../decisions/0004-custom-exception-hierarchy-design.md) - Exception hierarchy
- [ADR-0006](../decisions/0006-class-based-toolset-architecture.md) - Class-based toolsets
- [ADR-0007](../decisions/0007-tool-response-format.md) - Structured responses

**Component Integration:**
- [ADR-0005](../decisions/0005-event-bus-pattern-for-loose-coupling.md) - Event bus pattern
- [ADR-0012](../decisions/0012-middleware-integration-strategy.md) - Middleware approach
- [ADR-0013](../decisions/0013-memory-architecture.md) - Memory with ContextProvider
- [ADR-0019](../decisions/0019-skill-progressive-discovery.md) - Skills progressive disclosure

**User Interface:**
- [ADR-0009](../decisions/0009-cli-framework-selection.md) - CLI framework choice
- [ADR-0010](../decisions/0010-display-output-format.md) - Display format
- [ADR-0011](../decisions/0011-session-management-architecture.md) - Session persistence

**Operations:**
- [ADR-0008](../decisions/0008-testing-strategy-and-coverage-targets.md) - Testing strategy
- [ADR-0014](../decisions/0014-observability-integration.md) - Observability integration

**Provider Implementations:**
- [ADR-0015](../decisions/0015-gemini-provider-integration.md) - Gemini custom client
- [ADR-0016](../decisions/0016-local-provider-integration.md) - Local Docker integration

## See Also

- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Tool development guide
- [tests/README.md](../../tests/README.md) - Testing strategy and workflows
- [docs/decisions/](../decisions/) - Detailed architecture decision records
- [docs/design/requirements.md](requirements.md) - Base requirements specification
- [docs/design/skills.md](skills.md) - Skills architecture and implementation guide
