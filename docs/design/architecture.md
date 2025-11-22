# Architecture

Architectural patterns and design decisions for agent-base.

## Overview

Agent-base uses a class-based architecture with dependency injection to avoid global state and tight coupling. The design prioritizes testability, type safety, and extensibility while maintaining test coverage above 85%.

## Design Principles

The architecture is guided by five core principles that ensure maintainability, reliability, and ease of testing. These principles work together to create a robust framework that can evolve without accumulating technical debt.

| Principle | Description | Benefits |
|-----------|-------------|----------|
| **Testability** | All dependencies injected via constructors | Easy mocking without real LLM calls, fast test execution |
| **Type Safety** | Type hints throughout the codebase | Compile-time verification, better IDE support |
| **Loose Coupling** | Event bus for component communication | No direct dependencies between components |
| **No Global State** | Class-based design with explicit ownership | Clear dependency chains, no initialization order issues |
| **High Coverage** | 85%+ test coverage enforced | Confidence in changes, clear separation between free and paid tests |

## Key Patterns

### Dependency Injection

Dependencies flow through constructor parameters rather than global variables or singletons. This approach enables testing without real LLM calls or external services. All components receive their dependencies explicitly: toolsets receive `AgentConfig`, the Agent accepts an optional `chat_client` for testing, and the memory manager is injected into the Agent.

This pattern provides several key benefits. Tests can use a `MockChatClient` instead of making expensive API calls to real LLM providers, allowing the full test suite to run without incurring costs. Multiple configurations can exist simultaneously without conflicts, and there are no initialization order requirements to worry about. The explicit dependency chain makes it clear what each component needs and how components interact.

See ADR-0006 for detailed rationale on class-based design.

### Event-Driven Architecture

The framework uses an observer pattern through an event bus to decouple middleware and display components. Middleware emits events such as `TOOL_START` and `TOOL_COMPLETE`, while the display subscribes to these events and renders them. Importantly, neither component directly imports or depends on the other, maintaining clean separation of concerns.

This loose coupling enables several powerful capabilities. Middleware can be tested independently without requiring a display component. Different display implementations can be swapped in without modifying middleware code. Monitoring and logging can be added by subscribing to events without touching existing middleware. Multiple subscribers can react to the same events simultaneously, allowing for flexible architectures.

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

Memory management requires access to both request and response messages to store complete conversation turns. The Microsoft Agent Framework's ContextProvider pattern is specifically designed for this use case, providing hooks at both the `invoking` stage (before the LLM call) and the `invoked` stage (after receiving the response). Traditional middleware only sees traffic flowing in one direction, making it unsuitable for bidirectional operations like memory management.

ContextProvider offers distinct advantages for memory operations. It receives both request and response messages in the same component, can inject relevant context before the LLM processes a request, follows the framework's intended pattern for memory and context management, and represents a proven pattern validated in production implementations.

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

The framework consists of several specialized components, each with a focused responsibility:

| Component | Location | Responsibility |
|-----------|----------|----------------|
| **CLI** | `cli/` | Interactive interface with Typer, prompt_toolkit, session management |
| **Agent** | `agent.py` | Core orchestration, multi-provider LLM support (6 providers), dependency injection |
| **Toolsets** | `tools/` | Class-based tool implementations inheriting from `AgentToolset` |
| **Skills** | `skills/` | Progressive disclosure system for optional capabilities, ContextProvider-based documentation injection |
| **Providers** | `providers/` | Custom LLM provider implementations (Gemini custom client) |
| **Memory** | `memory/` | ContextProvider-based conversation storage with in-memory backend |
| **Event Bus** | `events.py` | Observer pattern for loose coupling between middleware and display |
| **Display** | `display/` | Rich-based execution visualization, tree hierarchy, multiple modes |
| **Persistence** | `persistence.py` | Session and memory state serialization |

See `src/agent/` for implementation details.

## Anti-Patterns Avoided

The architecture deliberately avoids several common anti-patterns that can lead to maintenance problems and testing difficulties.

All state is managed through class instances with explicit dependencies rather than global state. There are no module-level variables holding configuration or managers, which ensures clear ownership and prevents hidden coupling. Dependencies are injected at construction time rather than being lazily initialized with runtime checks—there are no `if not _manager: raise RuntimeError` patterns that defer error detection.

The event bus enables true component independence. The display component doesn't import middleware, and middleware doesn't import display, preventing circular dependencies and making each component easier to test and modify independently. Testing is simplified through dependency injection, which allows using `MockChatClient` in all tests except explicit LLM integration tests (marked with `@pytest.mark.llm`), eliminating expensive API calls during development.

See ADR-0006 for detailed examples of avoided patterns.

## Testing Approach

### Test Organization

Tests are organized by type with clear cost implications to ensure the development workflow remains fast and affordable:

| Test Type | Speed | Cost | Description |
|-----------|-------|------|-------------|
| **Unit** | Fast | Free | Isolated component tests with mocked dependencies |
| **Integration** | Moderate | Free | Component interaction tests using `MockChatClient` |
| **Validation** | Moderate | Free | CLI subprocess tests verifying end-to-end behavior |
| **LLM** | Slow | Paid | Real API calls (opt-in via `@pytest.mark.llm` marker) |

Only LLM tests make actual API calls. All others run in CI for free, keeping the development feedback loop quick and cost-effective.

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

The framework supports multiple LLM providers through a flexible configuration system built around `AgentConfig`. Configuration uses a layered approach with JSON-based settings as the foundation at `~/.agent/settings.json`, while environment variables can override any setting for deployment flexibility. Provider-specific validation runs on startup to catch configuration errors early. Memory settings control whether conversation history is enabled, which storage backend to use, and how much history to retain. All default values are centralized in `config/defaults.py` for easy maintenance.

Six LLM providers are currently supported, each offering different trade-offs:

| Provider | Hosting | Cost | Key Features |
|----------|---------|------|--------------|
| **Local** | Docker Desktop | Free | Offline operation, privacy |
| **OpenAI** | Direct API | Paid | Latest models (GPT-4o, o1) |
| **Anthropic** | Direct API | Paid | Long context, Claude models |
| **Gemini** | Google Cloud | Paid | 2M token context, multimodal |
| **Azure OpenAI** | Azure-hosted | Paid | Enterprise compliance, data residency |
| **Azure AI Foundry** | Managed platform | Paid | Model catalog, unified deployment |

Provider selection changes the underlying chat client implementation, but the Agent interface remains identical, allowing seamless switching between providers.

See ADR-0003 for multi-provider architecture strategy.

## Provider Architecture

### Design Decision

The framework supports multiple LLM providers through three distinct implementation patterns, chosen to balance developer convenience with flexibility. This approach enables users to choose providers based on cost, features, compliance requirements, or offline availability. By avoiding vendor lock-in to any single provider, the framework leverages the Microsoft Agent Framework's built-in multi-provider support while supporting both free local development and paid cloud providers. This meets diverse needs across students, enterprises, and privacy-conscious users.

Three implementation patterns handle different provider integration scenarios:

| Pattern | Use Case | Examples | Implementation |
|---------|----------|----------|----------------|
| **Framework clients** | Providers with official packages | OpenAI, Anthropic, Azure | Use `agent-framework-{provider}` packages, zero custom code |
| **Custom clients** | Providers without framework support | Gemini | Extend `BaseChatClient`, implement message conversion |
| **Client reuse** | OpenAI-compatible APIs | Local Docker | Reuse `OpenAIChatClient` with custom endpoint |

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

Memory management uses the Microsoft Agent Framework's ContextProvider pattern rather than traditional middleware. This choice stems from memory's need to access both request and response messages: the `invoking()` hook can inject relevant context before the LLM processes a request, while the `invoked()` hook stores the complete conversation turn after receiving the response. This bidirectional access makes ContextProvider the framework's intended pattern for memory management.

The memory system consists of four coordinated components:

| Component | Responsibility |
|-----------|----------------|
| `MemoryManager` | Abstract interface defining memory operations for extensibility |
| `InMemoryStore` | Default implementation providing search and retrieval |
| `MemoryContextProvider` | Integration layer with the agent framework |
| `MemoryPersistence` | Serialization for save/load with sessions |

Future extensibility is built in: the `InMemoryStore` can be swapped for external services like mem0 or langchain without changes to the Agent code, since the `MemoryManager` interface remains stable.

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

Sessions persist both thread state (conversation history) and memory state (long-term context) to enable resumable conversations. The architecture uses separate but coordinated persistence mechanisms: thread persistence leverages the framework's serialization for conversation history, while memory persistence uses a custom implementation to serialize the memory store. Although stored separately, both are saved and restored together as a unit. This separation positions the system for future enhancements like sharing memory across multiple conversation threads.

The implementation provides two primary operations through `ThreadPersistence`: `save_thread()` serializes conversation history, while `save_memory_state()` serializes the memory store. Both are written to the session directory with metadata tracking both files to ensure they remain synchronized.

## CLI Architecture

The command-line interface combines three complementary libraries: Typer for command structure and help generation, prompt_toolkit for advanced interactive input with history and shortcuts, and Rich for formatted output without manual terminal escape codes. These libraries integrate cleanly while each handling a distinct aspect of the user experience.

The CLI supports three types of user input. Interactive commands like `/clear` and `/continue` are handled internally before reaching the LLM. Shell commands prefixed with `!` execute system commands without exiting the agent session. Keyboard shortcuts provide quick access to common operations through an extensible handler system in `utils/keybindings/`.

See ADR-0009 for CLI framework selection.

## Display Architecture

The display system uses event-driven updates through Rich's Live display capabilities. Middleware components emit events without any rendering logic, while the display subscribes to these events and updates the interface. This separation allows swapping display modes without modifying middleware and enables testing middleware independently of display components.

Three display modes adapt the output to different use cases:

| Mode | Content | Use Case |
|------|---------|----------|
| **Default** | Completion summary with timing | Balanced detail for normal use |
| **Verbose** | Full execution tree | Debugging and understanding tool execution |
| **Quiet** | Response only | Scripts and automation |

Tree rendering leverages Rich's tree structure, updating incrementally as events arrive to provide real-time feedback during execution.

See ADR-0010 for display format decisions.

## Observability Architecture

### Design Decision

The framework includes optional OpenTelemetry integration for production monitoring, providing visibility into agent behavior and performance without impacting development workflows. This opt-in telemetry traces LLM calls, tool invocations, and execution flow using the industry-standard OpenTelemetry protocol. When disabled, there is zero performance impact, making it safe for production use. Support for both cloud exporters (Azure Application Insights) and local exporters (Aspire Dashboard) accommodates different deployment environments.

The Microsoft Agent Framework provides built-in OpenTelemetry instrumentation that automatically creates spans for agent operations and LLM calls. Configuration happens through environment variables: `ENABLE_OTEL` toggles telemetry on or off, while `ENABLE_SENSITIVE_DATA` controls whether prompt and response content is included in traces. Telemetry can export to Azure Application Insights for cloud monitoring or to the local Aspire Dashboard for development debugging.

**Telemetry dashboard:**
```bash
# Start local Aspire Dashboard (Docker-based)
/telemetry start

# Enable telemetry
export ENABLE_OTEL=true

# View traces at http://localhost:18888
agent -p "test prompt"
```

The tracing system captures agent initialization and configuration, LLM API calls with request/response details, tokens used, and latency, tool invocations with their results, session management operations, and error conditions with exceptions. Privacy controls ensure prompt and response content is excluded by default, with `ENABLE_SENSITIVE_DATA=true` available for debugging scenarios. Organizations can choose between Azure Application Insights for cloud monitoring or the local-only Aspire Dashboard for development environments.

See ADR-0014 for observability integration decisions.

## Design Decisions

The architecture decisions documented in this guide represent choices made through careful analysis of trade-offs and alternatives. Each decision is captured in detail through Architecture Decision Records (ADRs) that explain the context, considered options, and rationale. These records are organized by area:

| Category | ADRs | Topics Covered |
|----------|------|----------------|
| **Core Architecture** | 0001, 0003, 0004, 0006, 0007 | Naming conventions, multi-provider strategy, exception hierarchy, class-based toolsets, structured responses |
| **Component Integration** | 0005, 0012, 0013, 0019 | Event bus pattern, middleware approach, memory with ContextProvider, skills progressive disclosure |
| **User Interface** | 0009, 0010, 0011 | CLI framework choice, display format, session persistence |
| **Operations** | 0008, 0014 | Testing strategy, observability integration |
| **Provider Implementations** | 0015, 0016 | Gemini custom client, Local Docker integration |

For complete details on any decision including alternatives considered and implementation guidance, see the individual ADR documents in [docs/decisions/](../decisions/).

## See Also

- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Tool development guide
- [tests/README.md](../../tests/README.md) - Testing strategy and workflows
- [docs/decisions/](../decisions/) - Detailed architecture decision records
- [docs/design/requirements.md](requirements.md) - Base requirements specification
- [docs/design/skills.md](skills.md) - Skills architecture and implementation guide
