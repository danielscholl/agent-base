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

- **Environment-based** - Load from `.env` via `from_env()`
- **Validation** - Provider-specific validation on `validate()`
- **Memory settings** - Enable/disable, type selection, history limits
- **No defaults in code** - All defaults in `.env.example`

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

### Design Decision

Enable domain-specific capabilities through lightweight, installable extensions without increasing the core agent's footprint.

**Rationale:**
- Core tools should be universally useful (filesystem, hello world)
- Specialized capabilities (API integrations, computations, data processing) belong in optional skills
- Skills should load progressively - documentation only when relevant, scripts only when executed
- Avoid bloating every request with documentation for capabilities that might never be used
- Enable community contributions without modifying core codebase

### What are Skills?

Think of skills as optional capability packs. Each skill is a self-contained directory with a manifest (SKILL.md) and executable scripts. Skills can add specialized tools for things like web scraping, data analysis, API interactions, or domain-specific computations.

The key insight: **not every agent needs every capability**. A student using the agent for homework doesn't need AWS deployment scripts. A DevOps engineer doesn't need chemistry calculation tools. Skills let users install only what they need.

### The Progressive Disclosure Problem

Early implementations made a critical mistake: loading all skill documentation into every LLM request, regardless of whether that skill was relevant.

**The issue:**
A single skill might include 1200 tokens of detailed documentation - XML schemas, parameter descriptions, usage examples, language mappings. When a user asks "What is 2+2?", the LLM receives full documentation for greeting skills, web scraping skills, calculation skills, and every other installed skill. The agent was spending 60-80% of its context window on irrelevant documentation.

**The cost:**
- Slower responses (more tokens to process)
- Higher API costs (charged per input token)
- Wasted context window (less room for actual conversation)
- Poor user experience (slower for no reason)

### Three-Tier Progressive Disclosure

Skills now follow the same progressive loading principle as scripts - load documentation only when needed.

**Tier 1: Minimal Breadcrumb**

When skills are installed but don't match the current query, inject almost nothing:
```
[3 skills available]
```

Just enough for the LLM to know skills exist, if it needs them. About 10 tokens. The user asks "What is 2+2?" and the agent doesn't waste context on greeting documentation.

**Tier 2: Skill Registry**

When the user explicitly asks about capabilities ("What can you do?"), show a brief menu:
```
## Available Skills

- **hello-extended**: Multi-language greetings and translations
- **calculator**: Perform mathematical calculations
- **weather**: Get weather information
```

About 10-15 tokens per skill. Enough to understand what's available, not enough to know how to use it yet.

**Tier 3: Full Documentation**

When triggers match the user's query, inject complete documentation. The user says "Say hello in French" and now the agent receives the full hello-extended documentation with all its language mappings, parameter options, and examples.

**The impact:**
A query like "What is 2+2?" went from 3500 tokens (1000 base + 2500 skill docs) to 1200 tokens (1000 base + 200 other + 10 breadcrumb). That's 66% reduction in context usage for non-skill queries.

### How Progressive Disclosure Works

Here's how a user query flows through the system:

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│ SkillContextProvider.invoking()    │
│ (receives incoming message)         │
└─────────────┬───────────────────────┘
              │
              ▼
         ┌─────────┐
         │ Parse   │
         │ Message │
         └────┬────┘
              │
              ▼
    ┌─────────────────────┐
    │ Check Query Type    │
    └─────────┬───────────┘
              │
    ┌─────────┼─────────────────────────┐
    │         │                         │
    ▼         ▼                         ▼
"What can  "Say hello               "What is
 you do?"   in French"               2 + 2?"
    │         │                         │
    ▼         ▼                         ▼
┌─────┐   ┌─────┐                  ┌─────┐
│Wants│   │Match│                  │Match│
│Info │   │Trig-│                  │Trig-│
│     │   │gers?│                  │gers?│
└──┬──┘   └──┬──┘                  └──┬──┘
   │         │                         │
   │         │ YES                     │ NO
   │         │                         │
   ▼         ▼                         ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   TIER 2     │  │   TIER 3     │  │   TIER 1     │
│              │  │              │  │              │
│Show Registry │  │Full Docs for │  │Breadcrumb    │
│              │  │Matched Skills│  │              │
│~40 tokens    │  │~1200 tokens  │  │~10 tokens    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └────────┬────────┴─────────────────┘
                │
                ▼
        ┌───────────────┐
        │Context(       │
        │instructions=  │
        │relevant_docs) │
        └───────┬───────┘
                │
                ▼
           ┌────────┐
           │  LLM   │
           │Request │
           └────────┘
```

**Example flows:**

1. **"What can you do?"** → Wants info → Tier 2 (Registry)
   - Inject skill menu: 3 skills × 15 tokens = ~45 tokens
   - User sees capabilities, not implementation details

2. **"Say hello in French"** → Match triggers → Tier 3 (Full docs)
   - Keywords match: "hello", "french"
   - Inject complete hello-extended documentation: ~1200 tokens
   - LLM has everything needed to execute

3. **"What is 2+2?"** → No match → Tier 1 (Breadcrumb)
   - No skill-related triggers
   - Inject minimal breadcrumb: `[3 skills available]` = ~10 tokens
   - LLM knows skills exist if needed, but context stays clean

4. **"Calculate the square root of 144"** → Match triggers → Tier 3
   - Keywords match: "calculate"
   - Inject calculator skill documentation: ~800 tokens
   - Multiple skills can match, limited to max_skills (default: 3)

### Token Impact Visualization

Here's what changed in practice for a simple query like "What is 2+2?":

```
BEFORE: Static Injection (All Skills Always Loaded)
┌────────────────────────────────────────────┐
│ System Prompt                 1000 tokens  │
├────────────────────────────────────────────┤
│ User Message: "What is 2+2?"    10 tokens  │
├────────────────────────────────────────────┤
│ hello-extended docs           1200 tokens  │ ◄─┐
├────────────────────────────────────────────┤   │
│ calculator docs                800 tokens  │ ◄─┼─ Wasted
├────────────────────────────────────────────┤   │  (not relevant)
│ weather docs                   500 tokens  │ ◄─┘
├────────────────────────────────────────────┤
│ Other context                  200 tokens  │
└────────────────────────────────────────────┘
Total: 3710 tokens → Higher cost, slower response


AFTER: Progressive Disclosure (Load Only What's Needed)
┌────────────────────────────────────────────┐
│ System Prompt                 1000 tokens  │
├────────────────────────────────────────────┤
│ User Message: "What is 2+2?"    10 tokens  │
├────────────────────────────────────────────┤
│ [3 skills available]            10 tokens  │ ◄─ Minimal breadcrumb
├────────────────────────────────────────────┤
│ Other context                  200 tokens  │
└────────────────────────────────────────────┘
Total: 1220 tokens → 67% reduction


COMPARISON: When skill IS relevant ("Say hello in French")
┌────────────────────────────────────────────┐
│ System Prompt                 1000 tokens  │
├────────────────────────────────────────────┤
│ User Message: "Say hello..."    15 tokens  │
├────────────────────────────────────────────┤
│ hello-extended docs           1200 tokens  │ ◄─ Injected (matched!)
├────────────────────────────────────────────┤
│ [2 more skills available]       10 tokens  │ ◄─ Others stay minimal
├────────────────────────────────────────────┤
│ Other context                  200 tokens  │
└────────────────────────────────────────────┘
Total: 2425 tokens → 35% reduction, skill still works

The skill system works just as well, but costs 35-67% fewer tokens.
```

### Trigger Matching Strategy

The ContextProvider needs to decide which skills are relevant to the current request. This happens through structured triggers defined in each skill's manifest.

**Four matching strategies work together:**

1. **Skill name mentioned** - If the user explicitly says "use the weather skill", match it
2. **Keywords** - "hello", "greet", "bonjour" trigger the greeting skill
3. **Verbs** - "calculate", "compute" trigger the calculator skill
4. **Patterns** - Regular expressions like `\d+\s*[+\-*/]\s*\d+` catch "what is 5+3?"

The matching uses word boundaries to avoid false positives. "I'm a runner" doesn't accidentally trigger a "run" skill. Invalid regex patterns are caught gracefully - one bad skill doesn't break the whole system.

**Why single-message matching:**
The context provider looks only at the current user message, not conversation history. This keeps matching fast and predictable. If you say "Say hello in French" in message 1, then "Now do it in Spanish" in message 2, the second message alone doesn't match the greeting skill's triggers. This is intentional - it forces explicit requests and avoids assumptions about context.

Future enhancement: conversation-aware matching could consider recent messages for ambiguous requests.

### Implementation Pattern

Skills use the same ContextProvider pattern as memory (ADR-0013). Both need to inject dynamic context before the LLM call, both need to make per-request decisions about what to include.

**SkillContextProvider responsibilities:**
- Receive the incoming message via `invoking()`
- Analyze the message for trigger matches
- Decide which tier of information to inject
- Return `Context(instructions=relevant_docs)` for the LLM

**SkillDocumentationIndex separation:**
Skills have two distinct metadata systems that serve different purposes:
- `SkillRegistry` - Persistent install metadata (where is it, when installed, is it enabled)
- `SkillDocumentationIndex` - Runtime documentation (triggers, instructions, brief descriptions)

The registry answers "what's installed?" The index answers "what's relevant right now?" This separation keeps concerns clear and enables future enhancements like cross-session skill analytics.

### Discovery and Distribution

Skills live in two places:

**Bundled skills** ship with the agent. These are maintained by the core team, tested in CI, and automatically available. Think of these as the "standard library" of skills.

**Plugin skills** install from any Git repository:
```bash
agent skill install https://github.com/user/my-skill
```

The skill manifest uses YAML frontmatter in SKILL.md, similar to Jekyll or Hugo posts. This makes skills readable as documentation even without the agent. You can browse a skill repository on GitHub and understand what it does from the markdown.

Scripts follow PEP 723 inline dependency specification. Each script declares its own dependencies:
```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27.0", "click>=8.1.0"]
# ///
```

When the agent runs a skill script via `uv run`, dependencies are installed in an isolated environment automatically. No global pollution, no version conflicts between skills.

### What it enables

**For users:**
- Install only the capabilities you need
- No performance penalty for skills you're not using
- Community can share specialized skills
- Skills update independently of core agent

**For developers:**
- Add capabilities without core pull requests
- Test skills in isolation
- Distribute domain expertise as packages
- No risk of breaking core functionality

**For the architecture:**
- Context window stays small and fast
- Each skill's dependencies are isolated
- Progressive loading applies to both docs and execution
- Clear separation between core and extensions

### Why ContextProvider instead of alternatives?

**Why not static injection?**
Static injection (the original approach) loaded all documentation at initialization. Simple to implement, but violated the progressive disclosure principle. Skills that might never be used consumed tokens in every request.

**Why not middleware-based matching?**
Middleware sees messages in only one direction. A skill context provider needs to inject context before the LLM call, which requires seeing the incoming user message. Middleware is designed for request/response processing, not context augmentation.

**Why not LLM-based matching?**
Using the LLM itself to decide which skills to load creates a chicken-and-egg problem - you'd need to make an LLM call to decide what context to include in the LLM call. Structured triggers with keyword/pattern matching are fast, predictable, and don't consume extra tokens.

**Why not semantic matching with embeddings?**
Embeddings and vector similarity could improve matching accuracy, but add complexity, latency, and external dependencies. The current keyword/verb/pattern approach delivers 60-80% token reduction with zero external services. Semantic matching remains a possible Phase 2 enhancement.

### Future Extensibility

The three-tier system and trigger-based matching provide a solid foundation for enhancements:

**Conversation-aware matching** - Consider recent message history when triggers are ambiguous. "Now do it in Spanish" could look back to see what "it" refers to.

**Semantic triggers** - Add embedding-based matching alongside keyword triggers for better accuracy with paraphrased requests.

**Usage analytics** - Track which skills are used most often, which triggers work best, and suggest improvements to skill manifests.

**Cross-session patterns** - Learn user preferences over time. If a user frequently uses the weather skill, lower the trigger threshold.

All of these can be added without changing the core architecture. The ContextProvider interface, documentation index, and trigger structure remain stable.

See ADR-0019 for detailed progressive disclosure decisions and token impact measurements.

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
