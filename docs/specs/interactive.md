# Feature: Phase 3 - Interactive Mode and Enhanced UX

## Feature Description

Implement a comprehensive interactive mode for agent-template that provides a rich command-line experience with execution visualization, session persistence, status bars, and keyboard shortcuts. This phase transforms the CLI from a simple single-prompt tool into a full-featured interactive agent interface matching the user experience quality of butler-agent.

The implementation adds four major capabilities:
1. **Interactive Mode with prompt_toolkit**: Multi-turn conversations with command history and special commands
2. **Execution Visualization**: Real-time display of agent reasoning, tool calls, and progress using Rich
3. **Session Management and Persistence**: Auto-save conversations, resume previous sessions, context restoration
4. **Status Bars and Keyboard Shortcuts**: Contextual status information and productivity keybindings

## User Story

As a developer using agent-template
I want an interactive conversation mode with visual feedback and session persistence
So that I can have productive multi-turn conversations with automatic progress tracking and the ability to resume work across sessions

## Problem Statement

The current agent-template implementation only supports single-prompt execution (`agent -p "prompt"`), which limits productivity for multi-turn conversations and provides no visibility into agent reasoning or tool execution. Users cannot:

- **Maintain context** across multiple interactions without restarting
- **See execution progress** when tools are running or LLM is thinking
- **Resume sessions** after closing the terminal
- **Track conversation history** for reference or replay
- **Use productivity shortcuts** like clearing prompts or executing shell commands
- **Understand timing** of different execution phases

This creates friction for development workflows where users need to iterate on prompts, understand agent behavior, and maintain working context across sessions.

## Solution Statement

Port the proven interactive features from butler-agent to agent-template, adapting them to maintain architectural consistency while achieving feature parity. The solution leverages:

- **prompt_toolkit** for interactive shell with history and keybindings
- **Rich Live display** for real-time execution visualization with 5Hz refresh
- **Phase-based event grouping** to organize LLM calls and tool executions
- **JSON-based session persistence** with fallback serialization and context summaries
- **Event-driven architecture** using existing EventBus with enhanced event correlation
- **Middleware integration** for automatic event emission during execution

The implementation maintains backward compatibility (single-prompt mode continues to work) while adding rich interactive capabilities that match butler-agent's user experience quality.

## Related Documentation

### Requirements
- `docs/design/requirements.md` - FR-1 (Natural Language Query Interface), FR-6 (Extensibility)
- `docs/specs/foundation.md` - Phase 3 specifications (lines 2959-2965)

### Architecture Decisions
- **ADR-0005**: Event Bus Pattern for Loose Coupling (provides foundation for visualization)
- **ADR-0006**: Class-based Toolset Architecture (enables middleware integration)
- **ADR-0009**: CLI Framework Selection (Typer + Rich foundation)
- **ADR-0010** (to be created): Display Output Format and Verbosity Levels
- **ADR-0011** (to be created): Session Management Architecture
- **ADR-0012** (to be created): Middleware Integration Strategy

## Reference Implementation

**All Phase 3 features are modeled after the butler-agent implementation located at `ai-examples/butler-agent/`.**

When implementing tasks in this specification, refer to the butler-agent codebase for proven patterns and implementation details:

### Key Reference Files

**Interactive Mode & CLI:**
- `ai-examples/butler-agent/src/agent/cli.py` - Complete interactive mode implementation with PromptSession, command handling, and display integration

**Execution Visualization:**
- `ai-examples/butler-agent/src/agent/display/events.py` - Event classes and EventEmitter
- `ai-examples/butler-agent/src/agent/display/execution_tree.py` - ExecutionTreeDisplay with Rich Live
- `ai-examples/butler-agent/src/agent/display/execution_context.py` - DisplayMode and context management

**Middleware Integration:**
- `ai-examples/butler-agent/src/agent/middleware.py` - Function-level and agent-level middleware with event emission

**Session Persistence:**
- `ai-examples/butler-agent/src/agent/persistence.py` - ThreadPersistence with fallback serialization and context summaries

**Utilities:**
- `ai-examples/butler-agent/src/agent/activity.py` - ActivityTracker for status updates
- `ai-examples/butler-agent/src/agent/utils/keybindings/` - Extensible keybinding system
- `ai-examples/butler-agent/src/agent/utils/terminal.py` - Shell command execution

### Usage Guidelines

1. **Study before implementing**: Read the butler-agent implementation for each task to understand the complete pattern
2. **Adapt, don't copy blindly**: Butler-agent uses some domain-specific features (Kubernetes, addons) that should be omitted
3. **Maintain consistency**: Follow agent-template naming conventions and architecture while implementing butler-agent patterns
4. **Reference line numbers**: This spec includes specific line number references to help locate relevant code sections
5. **Test thoroughly**: Butler-agent's patterns are proven but should be validated in agent-template's context

The butler-agent codebase represents production-quality implementations that have been tested and refined. Use it as the primary reference for all Phase 3 implementation work.

## Codebase Analysis Findings

### Architecture Patterns to Follow

**From agent-template analysis:**
- ✅ **Event bus pattern** (src/agent/events.py) - Already compatible, just needs event_id field
- ✅ **Dependency injection** (src/agent/agent.py) - Ready for middleware parameter
- ✅ **Typer + Rich CLI** (src/agent/cli.py) - Same foundation as butler-agent
- ✅ **Dataclass configuration** (src/agent/config.py) - Session directory already configured
- ✅ **Comprehensive testing** (tests/) - 85%+ coverage infrastructure ready

**From butler-agent analysis:**
- **Event-driven visualization** - EventEmitter with asyncio.Queue for event streaming
- **Phase-based grouping** - Group LLM call + tool calls into logical execution phases
- **Live display with 5Hz refresh** - Rich Live display for smooth updates
- **Middleware event emission** - Emit events from function-level middleware
- **Context propagation** - ExecutionContext + should_show_visualization() pattern
- **Nested event hierarchy** - parent_id field for tool → subtool relationships
- **Fallback serialization** - Manual session save when framework serialization fails
- **PromptSession** - prompt_toolkit with FileHistory for persistent command history

### Naming Conventions

**Module Structure (from agent-template):**
```
src/agent/
├── cli.py              # CLI entry point (Typer app)
├── agent.py            # Agent class with framework integration
├── config.py           # AgentConfig dataclass
├── events.py           # EventBus singleton
├── middleware.py       # NEW: Middleware functions
├── persistence.py      # NEW: ThreadPersistence class
├── activity.py         # NEW: ActivityTracker for status
├── display/            # NEW: Display subsystem
│   ├── __init__.py
│   ├── events.py       # Display event classes
│   ├── tree.py         # ExecutionTreeDisplay
│   └── context.py      # ExecutionContext, DisplayMode
└── utils/
    ├── keybindings/    # NEW: Keybinding handlers
    │   ├── __init__.py
    │   ├── handler.py
    │   └── manager.py
    └── terminal.py     # NEW: Shell command utilities
```

**Class Naming (PascalCase):**
- `ThreadPersistence` - Session management
- `ExecutionTreeDisplay` - Visualization renderer
- `ExecutionContext` - Display mode context
- `ActivityTracker` - Progress tracking
- `KeybindingManager` - Keybinding registry

**Function Naming (snake_case):**
- `run_chat_mode()` - Interactive mode entry point
- `should_show_visualization()` - Context-aware flag
- `get_event_emitter()` - Singleton accessor (alias to get_event_bus)
- `set_execution_context()` - Context setter

### Similar Implementations

**Reference Files from butler-agent:**
1. **Interactive Mode**: `ai-examples/butler-agent/src/agent/cli.py:366-778`
   - PromptSession setup with FileHistory
   - Command handling loop (/clear, /continue, /purge, !shell)
   - Auto-save on exit
   - Context integration

2. **Execution Visualization**: `ai-examples/butler-agent/src/agent/display/`
   - `events.py` - Event classes (LLMRequestEvent, ToolStartEvent, etc.)
   - `execution_tree.py` - ExecutionTreeDisplay with Rich Live
   - `execution_context.py` - DisplayMode enum, ExecutionContext dataclass

3. **Middleware**: `ai-examples/butler-agent/src/agent/middleware.py:102-195`
   - `logging_function_middleware()` - Emits tool events
   - `agent_run_logging_middleware()` - Emits LLM events
   - Context-aware emission (should_show_visualization)

4. **Session Persistence**: `ai-examples/butler-agent/src/agent/persistence.py`
   - `ThreadPersistence` class with save/load/list
   - Fallback serialization for manual message extraction
   - Context summary generation for AI restoration

5. **Keybindings**: `ai-examples/butler-agent/src/agent/utils/keybindings/`
   - Abstract `KeybindingHandler` base class
   - `KeybindingManager` registry pattern
   - `ClearPromptHandler` (ESC key implementation)

### Integration Patterns

**Event Flow Architecture:**
```
User Input
    ↓
CLI (run_chat_mode)
    ↓
Agent.run_stream(prompt, thread)
    ↓
[Middleware Layer]
    ├─→ agent_run_logging_middleware → emit LLM events
    └─→ logging_function_middleware → emit Tool events
         ↓
    EventBus.emit(Event)
         ↓
    ExecutionTreeDisplay.handle_event(Event)
         ↓
    Rich Live Display (5Hz refresh)
         ↓
    Terminal Output
```

**Context Propagation Pattern:**
```python
# At CLI level - set execution context
ctx = ExecutionContext(
    is_interactive=True,
    show_visualization=not quiet,
    display_mode=DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
)
set_execution_context(ctx)

# In middleware - check context
if should_show_visualization():
    get_event_emitter().emit(event)
```

**Thread Integration Pattern:**
```python
# Create thread for conversation continuity
thread = agent.get_new_thread()

# Pass thread to maintain context
response = await agent.run_stream(prompt, thread=thread)

# Save thread with persistence
await persistence.save_thread(thread, session_name)

# Restore thread
thread, context_summary = await persistence.load_thread(agent, session_name)
```

## Relevant Files

### Existing Files to Modify

- **`src/agent/cli.py`** (54 lines → ~450 lines)
  - Current: Single-prompt mode only
  - Add: Interactive chat mode function (~400 lines)
  - Add: Helper functions (banner, status bar, session management)
  - Reference: butler-agent/src/agent/cli.py:366-778

- **`src/agent/agent.py`** (170 lines → ~185 lines)
  - Current: Basic agent creation without middleware
  - Add: Middleware parameter to `__init__()` (+1 line)
  - Add: Thread support (get_new_thread, update run/run_stream) (+10 lines)
  - Add: Default middleware creation (+4 lines)
  - Reference: butler-agent agent setup pattern

- **`src/agent/config.py`** (134 lines → ~136 lines)
  - Current: Session directory already configured ✅
  - Add: Optional `log_level` field (+2 lines)
  - Reference: butler-agent/src/agent/config.py

- **`src/agent/events.py`** (87 lines → ~110 lines)
  - Current: EventBus with basic Event dataclass
  - Add: `event_id` field to Event (+1 line)
  - Add: Context tracking functions (+10 lines)
  - Add: `get_event_emitter()` alias (+2 lines)
  - Reference: butler-agent/src/agent/display/events.py pattern

- **`tests/conftest.py`** (~50 lines → ~80 lines)
  - Current: Basic fixtures (mock_config, mock_chat_client, agent_instance)
  - Add: Display fixtures (mock_event_emitter, mock_display)
  - Add: Session fixtures (mock_persistence, temp_session_dir)

### New Files to Create

**Core Infrastructure:**

- **`src/agent/middleware.py`** (~260 lines)
  - Function-level middleware: logging_function_middleware
  - Agent-level middleware: agent_run_logging_middleware
  - Helper: create_middleware() factory
  - Reference: butler-agent/src/agent/middleware.py

- **`src/agent/persistence.py`** (~300 lines)
  - ThreadPersistence class (save, load, list, delete)
  - Fallback serialization when framework fails
  - Context summary generation for AI
  - Session metadata management
  - Reference: butler-agent/src/agent/persistence.py

- **`src/agent/activity.py`** (~50 lines)
  - ActivityTracker class for status updates
  - Thread-safe activity management
  - Reference: butler-agent/src/agent/activity.py

**Display Subsystem:**

- **`src/agent/display/__init__.py`** (~20 lines)
  - Exports: DisplayMode, ExecutionContext, ExecutionTreeDisplay
  - Context functions: set_execution_context, get_execution_context

- **`src/agent/display/events.py`** (~150 lines)
  - Event classes: LLMRequestEvent, LLMResponseEvent, ToolStartEvent, ToolCompleteEvent, ToolErrorEvent
  - EventEmitter class with asyncio.Queue
  - Singleton: get_event_emitter()
  - Reference: butler-agent/src/agent/display/events.py

- **`src/agent/display/tree.py`** (~300 lines)
  - ExecutionTreeDisplay class with Rich Live
  - Phase-based grouping (ExecutionPhase, TreeNode)
  - Event processing loop (async background task)
  - Display modes: MINIMAL, VERBOSE
  - Reference: butler-agent/src/agent/display/execution_tree.py

- **`src/agent/display/context.py`** (~50 lines)
  - DisplayMode enum (MINIMAL, VERBOSE)
  - ExecutionContext dataclass
  - Context management functions
  - Reference: butler-agent/src/agent/display/execution_context.py

**Utilities:**

- **`src/agent/utils/keybindings/__init__.py`** (~10 lines)
  - Exports: KeybindingHandler, KeybindingManager

- **`src/agent/utils/keybindings/handler.py`** (~30 lines)
  - Abstract KeybindingHandler base class
  - Interface: trigger_key, description, handle()
  - Reference: butler-agent keybindings pattern

- **`src/agent/utils/keybindings/manager.py`** (~40 lines)
  - KeybindingManager registry
  - create_keybindings() factory
  - Reference: butler-agent/src/agent/utils/keybindings/manager.py

- **`src/agent/utils/keybindings/handlers/clear_prompt.py`** (~20 lines)
  - ClearPromptHandler (ESC key)
  - Reference: butler-agent clear prompt implementation

- **`src/agent/utils/terminal.py`** (~80 lines)
  - execute_shell_command() with timeout
  - Shell command parsing and execution
  - Reference: butler-agent/src/agent/utils/terminal.py

**Testing:**

- **`tests/unit/test_middleware.py`** (~100 lines)
  - Test event emission from middleware
  - Test middleware execution order
  - Test error handling

- **`tests/unit/test_persistence.py`** (~150 lines)
  - Test session save/load cycle
  - Test fallback serialization
  - Test context summary generation
  - Test session listing and deletion

- **`tests/unit/test_display.py`** (~120 lines)
  - Test ExecutionTreeDisplay event handling
  - Test phase grouping logic
  - Test display mode switching

- **`tests/integration/test_interactive_mode.py`** (~200 lines)
  - Test interactive command loop (mocked input)
  - Test /clear, /continue, /purge commands
  - Test session auto-save
  - Test shell command execution

- **`tests/integration/agent_validation_phase3.yaml`** (~50 lines)
  - YAML test definitions for interactive features
  - Session persistence validation
  - Command handling validation

## Implementation Plan

### Phase 1: Event System Enhancement (Week 1, Days 1-2)

**Goal**: Enhance the existing EventBus to support event correlation and display integration

**Tasks**:
1. Add `event_id` field to Event dataclass for correlation
2. Add execution context management (ExecutionContext, set/get functions)
3. Create display event classes (LLMRequestEvent, ToolStartEvent, etc.)
4. Implement EventEmitter with asyncio.Queue
5. Add `should_show_visualization()` helper
6. Write tests for enhanced event system

**Deliverables**:
- Enhanced `src/agent/events.py` with event_id
- New `src/agent/display/events.py` with specialized events
- New `src/agent/display/context.py` with context management
- New `tests/unit/test_display_events.py` with 100% coverage

### Phase 2: Middleware Integration (Week 1, Days 3-5)

**Goal**: Implement middleware for automatic event emission during agent execution

**Tasks**:
1. Create middleware.py with function-level middleware
2. Add agent-level middleware for LLM events
3. Integrate middleware into Agent class
4. Add thread support to Agent (get_new_thread, thread parameter)
5. Test middleware event emission
6. Validate middleware ordering and context propagation

**Deliverables**:
- New `src/agent/middleware.py` (~260 lines)
- Updated `src/agent/agent.py` with middleware support
- New `tests/unit/test_middleware.py` with event emission tests
- Integration test showing end-to-end middleware → display flow

### Phase 3: Execution Visualization (Week 2, Days 1-3)

**Goal**: Implement real-time execution tree display with Rich Live

**Tasks**:
1. Create ExecutionTreeDisplay class with Rich Live
2. Implement phase-based event grouping
3. Add display modes (MINIMAL, VERBOSE)
4. Implement event processing background task
5. Add timing display and progress indicators
6. Test display rendering and event handling

**Deliverables**:
- New `src/agent/display/tree.py` with ExecutionTreeDisplay
- New `src/agent/display/__init__.py` with exports
- New `tests/unit/test_display.py` with rendering tests
- Visual validation: Run agent with --verbose to see tree

### Phase 4: Session Persistence (Week 2, Days 4-5)

**Goal**: Implement session save/load with fallback serialization

**Tasks**:
1. Create ThreadPersistence class
2. Implement session save with metadata
3. Implement session load with fallback
4. Add context summary generation
5. Implement session listing and deletion
6. Add auto-save logic for interactive mode

**Deliverables**:
- New `src/agent/persistence.py` (~300 lines)
- New `tests/unit/test_persistence.py` with save/load cycle tests
- Session storage in `~/.agent/sessions/`
- Documentation: Session file format (JSON schema)

### Phase 5: Interactive Mode Implementation (Week 3, Days 1-3)

**Goal**: Implement interactive chat mode with command handling

**Tasks**:
1. Add run_chat_mode() function to CLI
2. Integrate PromptSession with FileHistory
3. Implement command handlers (/clear, /continue, /purge)
4. Add shell command execution (!command)
5. Integrate ExecutionTreeDisplay
6. Add auto-save on exit
7. Wire up keyboard shortcuts

**Deliverables**:
- Updated `src/agent/cli.py` with interactive mode (~400 lines added)
- New `src/agent/activity.py` for status tracking
- Interactive mode accessible via `agent` (no flags)
- Command history saved to `~/.agent_history`

### Phase 6: Status Bar and Keybindings (Week 3, Days 4-5)

**Goal**: Add status bar rendering and extensible keybinding system

**Tasks**:
1. Implement status bar rendering (cwd, git branch, model, version)
2. Create KeybindingHandler abstract base class
3. Implement KeybindingManager registry
4. Create ClearPromptHandler (ESC key)
5. Integrate keybindings with PromptSession
6. Add terminal utilities for shell commands

**Deliverables**:
- Status bar rendering in `src/agent/cli.py`
- New `src/agent/utils/keybindings/` module
- New `src/agent/utils/terminal.py` for shell utilities
- Extensible keybinding system for future shortcuts

### Phase 7: Testing and Validation (Week 4)

**Goal**: Comprehensive testing and validation of all Phase 3 features

**Tasks**:
1. Write integration tests for interactive mode
2. Create YAML validation tests for new commands
3. Test session persistence across restarts
4. Validate display rendering in different terminal sizes
5. Test error handling and edge cases
6. Run full test suite and ensure 85%+ coverage
7. Performance testing (5Hz display refresh stability)

**Deliverables**:
- New `tests/integration/test_interactive_mode.py`
- Updated `tests/integration/agent_validation.yaml`
- Coverage report showing 85%+ overall
- Performance validation report

## Step by Step Tasks

### Task 1: Enhance Event System with Correlation

**Description**: Add event_id field to Event dataclass and create display-specific event classes

**Files to modify**:
- `src/agent/events.py` - Add event_id field
- Create `src/agent/display/__init__.py` - Package exports
- Create `src/agent/display/events.py` - Specialized event classes
- Create `src/agent/display/context.py` - Context management

**Implementation details**:
```python
# src/agent/events.py (enhancement)
from uuid import uuid4

@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: str | None = None  # For nested events

# src/agent/display/events.py (new file)
@dataclass
class LLMRequestEvent:
    event_id: str
    message_count: int
    timestamp: float = field(default_factory=time.time)

@dataclass
class ToolStartEvent:
    event_id: str
    tool_name: str
    arguments: dict[str, Any]
    parent_id: str | None = None  # For nested tool calls
    timestamp: float = field(default_factory=time.time)
```

**Validation**:
```bash
# Run tests
uv run pytest tests/unit/test_events.py -v

# Check that events have unique IDs
uv run pytest tests/unit/test_display_events.py::test_event_correlation -v
```

**Success criteria**:
- [ ] Event class has event_id field with UUID default
- [ ] Display event classes defined (5 types)
- [ ] EventEmitter class with asyncio.Queue
- [ ] Context management functions work
- [ ] Tests pass with 100% coverage

---

### Task 2: Implement Middleware with Event Emission

**Description**: Create middleware.py with function-level and agent-level middleware that emits events

**Files to create**:
- `src/agent/middleware.py` - Middleware functions

**Files to modify**:
- `src/agent/agent.py` - Add middleware parameter and integration

**Implementation details**:
```python
# src/agent/middleware.py (new file, ~260 lines)
async def logging_function_middleware(context, next):
    """Function-level middleware that emits tool events."""
    if should_show_visualization():
        tool_name = context.function.name
        arguments = context.arguments

        event = ToolStartEvent(
            event_id=str(uuid4()),
            tool_name=tool_name,
            arguments=sanitize_arguments(arguments),
            parent_id=get_current_tool_event_id()
        )
        set_current_tool_event_id(event.event_id)
        get_event_emitter().emit(event)

    start_time = time.time()
    try:
        result = await next(context)
        duration = time.time() - start_time

        if should_show_visualization():
            complete_event = ToolCompleteEvent(
                event_id=event.event_id,
                tool_name=tool_name,
                result_summary=extract_summary(result),
                duration=duration
            )
            get_event_emitter().emit(complete_event)

        return result
    except Exception as e:
        if should_show_visualization():
            error_event = ToolErrorEvent(
                event_id=event.event_id,
                tool_name=tool_name,
                error_message=str(e),
                duration=time.time() - start_time
            )
            get_event_emitter().emit(error_event)
        raise
    finally:
        set_current_tool_event_id(None)

def create_middleware() -> dict[str, list]:
    """Factory function to create default middleware."""
    return {
        "agent": [agent_run_logging_middleware],
        "function": [logging_function_middleware, activity_tracking_middleware]
    }
```

**Validation**:
```bash
# Test middleware event emission
uv run pytest tests/unit/test_middleware.py::test_tool_event_emission -v

# Test middleware ordering
uv run pytest tests/unit/test_middleware.py::test_middleware_execution_order -v

# Integration test
uv run pytest tests/integration/test_middleware_integration.py -v
```

**Success criteria**:
- [ ] Middleware emits events at correct times
- [ ] Events have proper correlation IDs
- [ ] Nested tool calls have parent_id set
- [ ] Error handling preserves event emission
- [ ] Tests cover all middleware paths (85%+)

---

### Task 3: Implement Execution Tree Display

**Description**: Create ExecutionTreeDisplay class with Rich Live for real-time visualization

**Files to create**:
- `src/agent/display/tree.py` - ExecutionTreeDisplay class

**Implementation details**:
```python
# src/agent/display/tree.py (new file, ~300 lines)
class ExecutionTreeDisplay:
    def __init__(self, console: Console, display_mode: DisplayMode, show_completion_summary: bool = True):
        self.console = console
        self.display_mode = display_mode
        self.show_completion_summary = show_completion_summary
        self._live: Live | None = None
        self._phases: list[ExecutionPhase] = []
        self._node_map: dict[str, TreeNode] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self):
        """Start display with Live refresh."""
        self._live = Live(
            self._render_phases(),
            console=self.console,
            refresh_per_second=5,  # 5Hz for smooth updates
            transient=not self.show_completion_summary
        )
        self._live.start()
        self._task = asyncio.create_task(self._process_events())

    async def stop(self):
        """Stop display and show final summary."""
        if self._task:
            await self._task
        if self._live:
            self._live.stop()

    async def _process_events(self):
        """Background task to process events from emitter."""
        emitter = get_event_emitter()
        while True:
            try:
                event = await asyncio.wait_for(emitter._queue.get(), timeout=0.1)
                self._handle_event(event)
                self._live.update(self._render_phases())
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
```

**Validation**:
```bash
# Test display rendering
uv run pytest tests/unit/test_display.py::test_execution_tree_rendering -v

# Test phase grouping
uv run pytest tests/unit/test_display.py::test_phase_grouping -v

# Visual validation
uv run agent -p "Say hello to Alice" --verbose
```

**Success criteria**:
- [ ] Display starts and stops cleanly
- [ ] Events processed in real-time (5Hz refresh)
- [ ] Phases grouped correctly (LLM + tools)
- [ ] MINIMAL and VERBOSE modes work
- [ ] Timing displayed accurately
- [ ] Tree structure renders correctly

---

### Task 4: Implement Session Persistence

**Description**: Create ThreadPersistence class for saving and loading conversation sessions

**Files to create**:
- `src/agent/persistence.py` - ThreadPersistence class

**Implementation details**:
```python
# src/agent/persistence.py (new file, ~300 lines)
class ThreadPersistence:
    def __init__(self, storage_dir: Path | None = None):
        if storage_dir is None:
            storage_dir = Path.home() / ".agent" / "sessions"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_dir / "index.json"

    async def save_thread(self, thread: Any, name: str, description: str | None = None) -> Path:
        """Save thread with metadata."""
        safe_name = self._sanitize_name(name)

        # Try framework serialization first
        try:
            serialized = await thread.serialize()
        except Exception:
            # Fallback to manual serialization
            serialized = await self._fallback_serialize(thread)

        # Extract metadata
        messages = await thread.message_store.list_messages()
        message_count = len(messages)
        first_message = extract_content(messages[0]) if messages else ""

        # Build conversation data
        conversation_data = {
            "name": safe_name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "message_count": message_count,
            "first_message": first_message[:100],
            "thread": serialized
        }

        # Save to file
        file_path = self.storage_dir / f"{safe_name}.json"
        with open(file_path, "w") as f:
            json.dump(conversation_data, f, indent=2)

        return file_path

    async def load_thread(self, agent: Any, name: str) -> tuple[Any, str | None]:
        """Load thread, returning (thread, context_summary)."""
        file_path = self.storage_dir / f"{name}.json"

        with open(file_path, "r") as f:
            data = json.load(f)

        thread_data = data["thread"]

        # Check if fallback serialization was used
        if thread_data.get("metadata", {}).get("fallback"):
            # Display history to user
            console.print("\n[cyan]Resuming session. Previous conversation:[/cyan]")
            for msg in thread_data["messages"]:
                render_message(msg)

            # Generate context summary for AI
            context_summary = self._generate_context_summary(thread_data["messages"])

            # Create new thread
            thread = agent.get_new_thread()
            return thread, context_summary
        else:
            # Deserialize thread directly
            thread = await agent.chat_client.deserialize_thread(thread_data)
            return thread, None
```

**Validation**:
```bash
# Test save/load cycle
uv run pytest tests/unit/test_persistence.py::test_save_load_cycle -v

# Test fallback serialization
uv run pytest tests/unit/test_persistence.py::test_fallback_serialization -v

# Integration test
uv run pytest tests/integration/test_session_persistence.py -v
```

**Success criteria**:
- [ ] Sessions save to ~/.agent/sessions/
- [ ] Metadata extracted correctly
- [ ] Fallback serialization works
- [ ] Context summaries generated
- [ ] Session list/delete operations work
- [ ] Tests cover save/load/fallback paths

---

### Task 5: Implement Interactive Chat Mode

**Description**: Add interactive mode to CLI with command handling and session integration

**Files to modify**:
- `src/agent/cli.py` - Add run_chat_mode() function

**Files to create**:
- `src/agent/activity.py` - ActivityTracker for status

**Implementation details**:
```python
# src/agent/cli.py (additions, ~400 lines)
async def run_chat_mode(
    quiet: bool = False,
    verbose: bool = False,
    resume_session: str | None = None
):
    """Run interactive chat mode."""
    config = AgentConfig.from_env()
    agent = Agent(config=config)
    persistence = ThreadPersistence()

    # Setup execution context
    display_mode = DisplayMode.VERBOSE if verbose else DisplayMode.MINIMAL
    ctx = ExecutionContext(
        is_interactive=True,
        show_visualization=not quiet,
        display_mode=display_mode
    )
    set_execution_context(ctx)

    # Setup display
    execution_display = None
    if not quiet:
        execution_display = ExecutionTreeDisplay(
            console=console,
            display_mode=display_mode,
            show_completion_summary=False  # Don't show in interactive
        )

    # Load or create thread
    thread = agent.get_new_thread()
    context_summary = None
    if resume_session:
        thread, context_summary = await persistence.load_thread(agent, resume_session)

    # Setup prompt session with history
    history_file = Path.home() / ".agent_history"
    keybinding_manager = KeybindingManager()
    keybinding_manager.register_handler(ClearPromptHandler())
    key_bindings = keybinding_manager.create_keybindings()

    session: PromptSession = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=key_bindings
    )

    # Render startup banner and status
    _render_startup_banner(config)
    _render_status_bar(config)

    # Message counter for auto-save
    message_count = 0

    try:
        while True:
            # Prompt for input
            try:
                user_input = await session.prompt_async("\n> ")
            except KeyboardInterrupt:
                console.print("\n[yellow]Use Ctrl+D to exit[/yellow]")
                continue
            except EOFError:
                break

            # Skip empty input
            if not user_input.strip():
                continue

            # Handle special commands
            if user_input.startswith("/"):
                await handle_command(user_input, persistence, thread, agent)
                continue

            # Handle shell commands
            if user_input.startswith("!"):
                execute_shell_command(user_input[1:])
                continue

            # Execute agent with display
            message_count += 1
            console.print(f"\n[bold]User:[/bold] {user_input}\n")
            console.print("[bold]Agent:[/bold] ", end="")

            if execution_display:
                await execution_display.start()

            try:
                # Add context summary if resuming session
                prompt = user_input
                if context_summary:
                    prompt = f"[Previous context: {context_summary}]\n\nUser: {user_input}"
                    context_summary = None  # Clear after first use

                # Stream response
                async for chunk in agent.run_stream(prompt, thread=thread):
                    console.print(chunk, end="")
                console.print("\n")
            finally:
                if execution_display:
                    await execution_display.stop()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    finally:
        # Auto-save session
        await _auto_save_session(persistence, thread, message_count, quiet)
```

**Validation**:
```bash
# Test interactive mode
uv run agent

# Test with session resume
uv run agent --continue

# Test commands
# In interactive mode: /clear, /help, !ls
```

**Success criteria**:
- [ ] Interactive prompt loop works
- [ ] Command history persists across sessions
- [ ] /clear, /continue, /purge commands work
- [ ] Shell commands execute (!command)
- [ ] ESC key clears prompt
- [ ] Auto-save on exit
- [ ] Session resume works

---

### Task 6: Implement Status Bar and Keybindings

**Description**: Add status bar rendering and extensible keybinding system

**Files to modify**:
- `src/agent/cli.py` - Add status bar rendering functions

**Files to create**:
- `src/agent/utils/keybindings/__init__.py`
- `src/agent/utils/keybindings/handler.py` - Abstract base class
- `src/agent/utils/keybindings/manager.py` - Registry
- `src/agent/utils/keybindings/handlers/clear_prompt.py` - ESC handler
- `src/agent/utils/terminal.py` - Shell utilities

**Implementation details**:
```python
# src/agent/cli.py (status bar helper)
def _render_status_bar(config: AgentConfig):
    """Render status bar with context info."""
    # Get current directory
    cwd = Path.cwd()
    try:
        cwd_display = f"~/{cwd.relative_to(Path.home())}"
    except ValueError:
        cwd_display = str(cwd)

    # Get git branch
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            branch_display = f" [⎇ {branch}]" if branch else ""
        else:
            branch_display = ""
    except Exception:
        branch_display = ""

    # Format with alignment
    left = f" {cwd_display}{branch_display}"
    right = f"{config.get_model_display_name()} · v{__version__}"
    padding = max(1, console.width - len(left) - len(right))

    console.print(f"[dim]{left}[/dim]{' ' * padding}[cyan]{right}[/cyan]")
    console.print(f"[dim]{'─' * console.width}[/dim]")

# src/agent/utils/keybindings/handler.py (new file)
class KeybindingHandler(ABC):
    """Abstract base class for keybinding handlers."""

    @property
    @abstractmethod
    def trigger_key(self) -> str:
        """prompt_toolkit key name (e.g., 'escape', 'c-x')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @abstractmethod
    def handle(self, event: Any) -> None:
        """Handle the key press event."""
        pass

# src/agent/utils/keybindings/handlers/clear_prompt.py
class ClearPromptHandler(KeybindingHandler):
    @property
    def trigger_key(self) -> str:
        return "escape"

    @property
    def description(self) -> str:
        return "Clear the current prompt text"

    def handle(self, event: Any) -> None:
        event.app.current_buffer.text = ""
```

**Validation**:
```bash
# Visual validation - run interactive mode
uv run agent

# Check status bar shows:
# - Current directory
# - Git branch (if in repo)
# - Model name
# - Version

# Test ESC key clears prompt
```

**Success criteria**:
- [ ] Status bar renders correctly
- [ ] Status bar updates terminal width
- [ ] Git branch detection works
- [ ] ESC key clears prompt
- [ ] Keybinding system is extensible
- [ ] Shell command execution works

---

### Task 7: Write Comprehensive Tests

**Description**: Create unit and integration tests for all Phase 3 features

**Files to create**:
- `tests/unit/test_middleware.py` (~100 lines)
- `tests/unit/test_persistence.py` (~150 lines)
- `tests/unit/test_display.py` (~120 lines)
- `tests/integration/test_interactive_mode.py` (~200 lines)
- `tests/integration/agent_validation_phase3.yaml` (~50 lines)

**Files to modify**:
- `tests/conftest.py` - Add display and session fixtures

**Implementation details**:
```python
# tests/unit/test_middleware.py
@pytest.mark.asyncio
async def test_tool_event_emission(mock_config, mock_chat_client):
    """Test that middleware emits tool events."""
    # Setup event capture
    emitted_events = []

    class TestListener:
        def handle_event(self, event):
            emitted_events.append(event)

    get_event_bus().subscribe(TestListener())

    # Create agent with middleware
    agent = Agent(config=mock_config, chat_client=mock_chat_client)

    # Run agent
    await agent.run("test prompt")

    # Verify events emitted
    assert len(emitted_events) > 0
    tool_events = [e for e in emitted_events if e.type == EventType.TOOL_START]
    assert len(tool_events) > 0

# tests/unit/test_persistence.py
@pytest.mark.asyncio
async def test_save_load_cycle(tmp_path, mock_config, mock_chat_client):
    """Test saving and loading a session."""
    persistence = ThreadPersistence(storage_dir=tmp_path)
    agent = Agent(config=mock_config, chat_client=mock_chat_client)

    # Create thread and add message
    thread = agent.get_new_thread()
    await agent.run("test prompt", thread=thread)

    # Save session
    await persistence.save_thread(thread, "test-session")

    # Load session
    loaded_thread, context_summary = await persistence.load_thread(agent, "test-session")

    # Verify thread loaded
    assert loaded_thread is not None
```

**Validation**:
```bash
# Run all unit tests
uv run pytest tests/unit/ -v

# Run integration tests
uv run pytest tests/integration/ -v

# Check coverage
uv run pytest --cov=src/agent --cov-report=html --cov-fail-under=85

# Open coverage report
open htmlcov/index.html
```

**Success criteria**:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Coverage ≥ 85%
- [ ] YAML validation tests pass
- [ ] No regressions in existing tests

---

### Task 8: Documentation and Polish

**Description**: Update documentation and create ADRs for Phase 3 decisions

**Files to create**:
- `docs/decisions/0010-display-output-format.md`
- `docs/decisions/0011-session-management-architecture.md`
- `docs/decisions/0012-middleware-integration-strategy.md`

**Files to modify**:
- `README.md` - Update with Phase 3 features
- `docs/design/usage.md` - Add interactive mode documentation
- `CONTRIBUTING.md` - Update testing guidelines

**Implementation details**:

**ADR-0010: Display Output Format and Verbosity Levels**
- **Context**: Need real-time execution visualization
- **Decision**: Phase-based grouping with MINIMAL/VERBOSE modes
- **Alternatives**: Flat event list, streaming-only, no visualization
- **Rationale**: Reduces noise, focuses on current work, user-configurable

**ADR-0011: Session Management Architecture**
- **Context**: Need conversation persistence across sessions
- **Decision**: JSON-based storage with fallback serialization
- **Alternatives**: Database storage, pickle, framework-only
- **Rationale**: Human-readable, debuggable, robust to framework changes

**ADR-0012: Middleware Integration Strategy**
- **Context**: Need automatic event emission without tool modifications
- **Decision**: Function-level middleware with context propagation
- **Alternatives**: Direct tool modification, polling, manual logging
- **Rationale**: Decoupled, reusable, framework-native

**docs/design/usage.md Updates**:
```markdown
## Interactive Mode

Start interactive mode:
```bash
agent
```

### Commands

- `/clear` - Clear screen
- `/continue` - Resume a previous session
- `/purge` - Delete all saved sessions
- `/help` - Show help message
- `!command` - Execute shell command

### Examples

**Multi-turn conversation:**
```bash
$ agent
> Tell me about Python type hints
[Agent explains type hints]

> Can you show me an example?
[Agent provides code example]

> Thanks!
```

**Resume session:**
```bash
$ agent --continue
[Session picker UI]
Select session: auto-2025-01-15-10-30
[Previous conversation restored]
```

### Keyboard Shortcuts

- `ESC` - Clear current prompt
- `Ctrl+D` - Exit interactive mode
- `Ctrl+C` - Interrupt current operation
```

**Validation**:
```bash
# Check documentation completeness
grep -r "Phase 3" docs/

# Verify all ADRs created
ls docs/decisions/001*.md
```

**Success criteria**:
- [ ] All ADRs created and accepted
- [ ] README updated with Phase 3 features
- [ ] docs/design/usage.md has interactive mode guide
- [ ] Examples demonstrate all features
- [ ] Documentation reviewed for accuracy

## Testing Strategy

### Unit Tests

**New Test Files:**

1. **`tests/unit/test_middleware.py`** (~100 lines)
   - Test event emission from function middleware
   - Test event emission from agent middleware
   - Test middleware execution order
   - Test error handling preserves events
   - Test context propagation

2. **`tests/unit/test_persistence.py`** (~150 lines)
   - Test session save with metadata
   - Test session load with deserialization
   - Test fallback serialization
   - Test context summary generation
   - Test session listing and filtering
   - Test session deletion

3. **`tests/unit/test_display.py`** (~120 lines)
   - Test ExecutionTreeDisplay initialization
   - Test event handling and phase creation
   - Test phase grouping logic
   - Test display mode switching
   - Test timing calculations
   - Test tree rendering

4. **`tests/unit/test_keybindings.py`** (~50 lines)
   - Test KeybindingManager registration
   - Test ClearPromptHandler behavior
   - Test keybinding creation

**Updated Test Files:**

5. **`tests/conftest.py`** (additions)
   - Add `mock_event_emitter` fixture
   - Add `mock_execution_display` fixture
   - Add `mock_persistence` fixture
   - Add `temp_session_dir` fixture

### Integration Tests

1. **`tests/integration/test_interactive_mode.py`** (~200 lines)
   - Test interactive prompt loop with mocked input
   - Test /clear command
   - Test /continue command with session picker
   - Test /purge command with confirmation
   - Test shell command execution
   - Test auto-save on exit
   - Test session resume with context

2. **`tests/integration/test_middleware_integration.py`** (~100 lines)
   - Test end-to-end middleware → display flow
   - Test event correlation across phases
   - Test nested tool calls with parent_id

3. **`tests/integration/test_session_persistence.py`** (~80 lines)
   - Test save/load cycle with real agent
   - Test multiple sessions
   - Test session metadata accuracy

### YAML Validation Tests

**`tests/integration/agent_validation_phase3.yaml`** (new file, ~50 lines):
```yaml
command_tests:
  - name: "Interactive help"
    command: "echo '/help' | uv run agent"
    timeout: 10
    expected:
      exit_code: 0
      stdout_contains: ["/clear", "/continue", "/purge"]

  - name: "Session auto-save"
    command: "echo 'test prompt' | uv run agent"
    timeout: 30
    expected:
      exit_code: 0
      stdout_contains: ["auto-saved"]

  - name: "Verbose mode"
    command: "uv run agent -p 'Say hello' --verbose"
    timeout: 30
    expected:
      exit_code: 0
      stdout_contains: ["Phase", "Thinking"]
```

### Edge Cases to Test

**Middleware:**
- Tool that raises exception (event still emitted)
- Multiple tools called in sequence
- Nested tool calls (parent_id correct)
- Middleware disabled (no events emitted)

**Persistence:**
- Session with 0 messages (no save)
- Session with very large message history
- Corrupted session file
- Session directory doesn't exist
- Multiple sessions with same name

**Display:**
- Terminal width changes during execution
- Very long tool names/output
- Rapid event emission (queue doesn't overflow)
- Display stop during event processing
- MINIMAL mode shows active phase only

**Interactive Mode:**
- Empty input (skip)
- Very long input (handled correctly)
- Ctrl+C during agent execution
- Ctrl+D to exit
- Command history navigation
- Git repo detection fails gracefully

### Performance Tests

1. **Display Refresh Rate**:
   - Verify 5Hz refresh (200ms interval)
   - Measure CPU usage during display
   - Test with 100+ events

2. **Session Persistence**:
   - Save large session (1000+ messages)
   - Load large session
   - List 100+ sessions

3. **Event Queue**:
   - Rapid event emission (100 events/sec)
   - Queue doesn't grow unbounded
   - Events processed in order

### Coverage Targets

**Overall**: 85%+ (existing target, maintained)

**New Code Coverage**:
- `src/agent/middleware.py`: 90%+
- `src/agent/persistence.py`: 90%+
- `src/agent/display/tree.py`: 85%+
- `src/agent/display/events.py`: 95%+
- `src/agent/utils/keybindings/`: 90%+

**Excluded from Coverage**:
- CLI display logic (hard to test, manual validation)
- Terminal utilities (subprocess-heavy)

## Acceptance Criteria

**Core Functionality:**
- [ ] Interactive mode starts with `agent` command
- [ ] Streaming responses display in real-time
- [ ] Command history persists across sessions
- [ ] /clear, /continue, /purge commands work
- [ ] Shell commands execute with !prefix
- [ ] ESC key clears prompt
- [ ] Ctrl+D exits cleanly
- [ ] Ctrl+C interrupts gracefully

**Execution Visualization:**
- [ ] MINIMAL mode shows active phase only
- [ ] VERBOSE mode shows all phases with timing
- [ ] Tool calls display with arguments
- [ ] LLM thinking shows message count
- [ ] Display refreshes at 5Hz
- [ ] Display stops cleanly on completion
- [ ] Nested tool calls show hierarchy

**Session Management:**
- [ ] Sessions auto-save on exit
- [ ] Session metadata includes message count
- [ ] Session resume works via --continue
- [ ] Context summary generated for AI
- [ ] Session listing shows all sessions
- [ ] Session deletion works
- [ ] Fallback serialization works

**Status and Context:**
- [ ] Status bar shows current directory
- [ ] Status bar shows git branch (when in repo)
- [ ] Status bar shows model name
- [ ] Status bar shows version
- [ ] Startup banner displays

**Backward Compatibility:**
- [ ] Single-prompt mode still works (`-p`)
- [ ] --check flag still works
- [ ] --config flag still works
- [ ] Existing tests still pass
- [ ] No breaking API changes

**Testing:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] YAML validation tests pass
- [ ] Coverage ≥ 85% overall
- [ ] Coverage ≥ 90% for middleware and persistence
- [ ] No test regressions

**Documentation:**
- [ ] README updated with Phase 3 features
- [ ] docs/design/usage.md has interactive mode guide
- [ ] CONTRIBUTING.md updated for testing
- [ ] ADR-0010 created (Display format)
- [ ] ADR-0011 created (Session management)
- [ ] ADR-0012 created (Middleware integration)

**Performance:**
- [ ] Display refresh stable at 5Hz
- [ ] Large sessions (1000+ messages) load < 2s
- [ ] Event queue doesn't grow unbounded
- [ ] CPU usage reasonable during display

## Validation Commands

```bash
# Installation
uv sync

# Run all tests
uv run pytest tests/ -v --cov=src/agent --cov-report=term-missing --cov-report=html

# Run only Phase 3 tests
uv run pytest tests/unit/test_middleware.py tests/unit/test_persistence.py tests/unit/test_display.py -v
uv run pytest tests/integration/test_interactive_mode.py -v

# Code quality
uv run black --check src/ tests/
uv run ruff check src/ tests/
uv run mypy src/agent

# Interactive mode testing (manual)
uv run agent
# Try: /help, /clear, !ls, ESC key, Ctrl+D

# Single-prompt with visualization
uv run agent -p "Say hello to Alice"
uv run agent -p "Say hello to Alice" --verbose
uv run agent -p "Say hello to Alice" --quiet

# Session management
uv run agent --continue  # Resume last session

# Check coverage
open htmlcov/index.html

# YAML validation
python tests/integration/run_validation.py --config tests/integration/agent_validation_phase3.yaml
```

## Notes

### Architectural Decisions

**Why Phase-Based Grouping?**
- **Problem**: Flat event streams are noisy and hard to follow
- **Solution**: Group LLM call + tool calls into logical "phases"
- **Benefit**: User sees reasoning → action flow, not individual events
- **Reference**: Butler-agent ExecutionPhase pattern

**Why Fallback Serialization?**
- **Problem**: Framework thread serialization may fail or change
- **Solution**: Manual message extraction as backup
- **Benefit**: Sessions never lost, always human-readable
- **Trade-off**: Context must be summarized for AI (not full history)

**Why 5Hz Display Refresh?**
- **Problem**: Too fast = CPU waste, too slow = laggy
- **Solution**: 5 updates/second (200ms interval)
- **Benefit**: Smooth visual updates without performance impact
- **Reference**: Butler-agent tested this rate

**Why EventEmitter with asyncio.Queue?**
- **Problem**: Middleware runs in agent context, display in CLI context
- **Solution**: Async queue bridges contexts without blocking
- **Benefit**: Decoupled, works across async boundaries
- **Alternative**: Direct callback would block middleware

**Why Context Propagation Pattern?**
- **Problem**: Middleware needs to know if visualization is enabled
- **Solution**: ExecutionContext + should_show_visualization()
- **Benefit**: Clean mode detection without parameter passing
- **Reference**: Butler-agent pattern, widely used

### Implementation Insights from Butler-Agent

1. **Rich Live Display Transient Mode**:
   - `transient=True` clears display after completion
   - `transient=False` keeps final summary visible
   - Use `not show_completion_summary` for interactive mode

2. **Event Processing Loop**:
   - Background `asyncio.create_task()` processes events
   - 0.1s timeout on queue.get() prevents blocking
   - Graceful cancellation on display stop

3. **Nested Tool Events**:
   - `set_current_tool_event_id()` sets parent context
   - Child events automatically get parent_id
   - `TreeNode.add_child()` builds hierarchy

4. **Session Metadata**:
   - First message preview (100 chars)
   - Message count for sizing
   - Timestamp for sorting
   - Description for user notes

5. **Command Handling**:
   - `/` prefix for internal commands
   - `!` prefix for shell commands
   - Keep separate (shell needs Enter key)

6. **Keybinding Closure Pattern**:
   - `make_handler()` creates closure to capture handler
   - Prevents late-binding issues with loop variables
   - Standard Python keybinding registration pattern

### Future Enhancements (Post-Phase 3)

**Phase 4 Ideas:**
- Additional keybindings (Ctrl+X for abort, Ctrl+S for save)
- Session export to markdown
- Session search/filter UI
- Multi-session comparison
- Token usage tracking per session
- Cost estimation display
- Audio input/output support
- Web UI for session browsing

**Display Enhancements:**
- Syntax highlighting for code blocks
- Collapsible tree nodes
- Table rendering for structured data
- Progress bars for long operations
- Nested tool call visualization
- Timing charts/graphs

**Session Features:**
- Session tags for organization
- Session branching (fork conversations)
- Session merge (combine sessions)
- Session replay (step through)
- Session sharing (export/import)

### Development Workflow

**Recommended Order:**
1. Start with event system (foundation)
2. Add middleware (enables everything else)
3. Build display (visual feedback)
4. Implement persistence (state management)
5. Add interactive mode (user interface)
6. Polish with status/keybindings
7. Comprehensive testing

**Testing Strategy:**
- Write tests alongside implementation (TDD)
- Use YAML validation for CLI testing
- Manual testing for visual elements
- Performance testing for display refresh

**Code Review Checklist:**
- [ ] No global state introduced
- [ ] Backward compatibility maintained
- [ ] Events properly correlated (event_id, parent_id)
- [ ] Error handling preserves event emission
- [ ] Display cleanup on interrupt
- [ ] Session files human-readable
- [ ] Tests achieve 85%+ coverage

### Dependencies Added

```toml
# Already in pyproject.toml:
prompt-toolkit>=3.0.0    # ✅ Already listed
rich>=14.1.0              # ✅ Already listed

# No new dependencies needed!
```

### Success Metrics

**Quantitative:**
- Test coverage: 85%+ maintained
- Interactive mode startup: < 500ms
- Display refresh rate: 5Hz stable
- Session save time: < 100ms
- Session load time: < 2s (large sessions)

**Qualitative:**
- User experience matches butler-agent quality
- Visual feedback is smooth and informative
- Sessions restore context effectively
- Commands are intuitive and responsive
- Error messages are clear and helpful

## Execution

This spec can be implemented using: `/implement docs/specs/phase3-interactive-features.md`

### Archon Integration

**Project Creation:**
```bash
# Create Archon project for Phase 3
project_id = manage_project(
    action="create",
    title="Phase 3: Interactive Mode and Enhanced UX",
    description="Implement interactive mode, execution visualization, session persistence, and keyboard shortcuts"
)
```

**Task Breakdown:**
Each "Task N" section will become an Archon task:
1. Enhance Event System with Correlation
2. Implement Middleware with Event Emission
3. Implement Execution Tree Display
4. Implement Session Persistence
5. Implement Interactive Chat Mode
6. Implement Status Bar and Keybindings
7. Write Comprehensive Tests
8. Documentation and Polish

**Task Assignment:**
- Tasks 1-3: Core infrastructure (Week 1)
- Tasks 4-6: User-facing features (Weeks 2-3)
- Tasks 7-8: Quality and documentation (Week 4)

### Estimated Timeline

**Week 1: Core Infrastructure**
- Task 1 (Event Enhancement): 1 day
- Task 2 (Middleware): 2 days
- Task 3 (Display): 2 days

**Week 2: Session Management**
- Task 4 (Persistence): 3 days
- Task 5 (Interactive Mode) Part 1: 2 days

**Week 3: Interactive Features**
- Task 5 (Interactive Mode) Part 2: 2 days
- Task 6 (Status/Keybindings): 1 day

**Week 4: Testing and Polish**
- Task 7 (Testing): 3 days
- Task 8 (Documentation): 2 days

**Total**: ~4 weeks for complete Phase 3 implementation

### Next Steps After Phase 3

1. **Phase 4: Advanced Tools** - API integrations, data processing, web scraping
2. **Phase 5: Observability** - Application Insights, metrics, tracing
3. **Phase 6: Multi-Agent** - Agent delegation, sub-agents, coordination
4. **Phase 7: Web UI** - Browser-based interface for session management
5. **Phase 8: Cloud Deployment** - Container deployment, scaling, monitoring
