# Feature: CLI Agent Tool Architecture

> **Historical Note:** This foundational specification references the legacy `AgentConfig` system in examples. As of v0.3.0, the configuration system uses `AgentSettings` and `load_config()`. The architectural principles and patterns described here remain current.

## Feature Description

Transform the agent-template from a chat-only CLI agent into a tool-enabled agent that follows proven architectural patterns while avoiding common implementation flaws. This MVP implementation will establish the foundation for tool support by creating a "hello world" tool that demonstrates the complete tool lifecycle, registration, invocation, error handling, and testing patterns.

The architecture will enable future integration of custom tools and APIs while maintaining clean separation of concerns, testability, and extensibility.

**Multi-Provider LLM Support**: The agent supports three LLM providers through Microsoft Agent Framework (v1.0.0b251106+):
- **OpenAI**: Direct OpenAI API (gpt-4o, gpt-4-turbo, etc.)
- **Anthropic**: Direct Anthropic API (claude-sonnet-4-5, claude-opus-4, etc.)
- **Azure AI Foundry**: Microsoft's managed AI platform with access to 1,800+ models

## User Story

As a developer working on agent-template
I want to establish a robust tool architecture pattern
So that I can confidently add custom tools following proven patterns without introducing architectural technical debt

## Problem Statement

The current agent-template project exists only as requirements documentation with no implementation. We need to establish a robust tool architecture that avoids common architectural flaws:

1. **Global state for tools** - Makes testing difficult and prevents multiple configurations
2. **Runtime initialization requirements** - No compile-time safety
3. **Tight middleware-display coupling** - Cannot test independently
4. **Fragile pattern matching** - Brittle learning systems
5. **Low test coverage for core logic** - Core tools excluded from testing
6. **Monolithic CLI module** - Large files violating single responsibility
7. **Complex multi-phase patterns** - Unclear contracts

Instead, we will implement proven patterns: dependency injection, rich CLI visualization, event-driven execution tracking, session persistence, and structured error responses.

## Solution Statement

Implement a class-based toolset architecture using dependency injection that enables:

1. **Clean tool registration** via factory pattern (no global state)
2. **Type-safe tool initialization** via class constructors
3. **Loose coupling** via event bus pattern for middleware/display communication
4. **High test coverage** via mockable dependencies
5. **Modular CLI** via extracted session management and command handling classes
6. **Proven UX patterns**: execution visualization, status bars, interactive shell

The MVP will implement a HelloTools class with a single `hello_world()` tool demonstrating all architectural patterns that future tools will follow.

## Related Documentation

### Requirements
- `docs/design/requirements.md` - Generic chatbot agent requirements
  - FR-1: Natural Language Query Interface
  - FR-6: Extensibility for tool integration
  - Security, configuration, and session management requirements

### Architecture Decisions
- **ADR-001** (to be created): Class-based toolset architecture over global state
- **ADR-002** (to be created): Event bus pattern for loose coupling
- **ADR-003** (to be created): Session management extraction from CLI

## Architectural Patterns

### Patterns to Implement

1. **Agent Framework Integration**
   ```python
   self.agent = self.chat_client.create_agent(
       name="Agent",
       instructions=instructions,
       tools=tools,
       middleware=all_middleware,
       context_providers=context_providers
   )
   ```
   - Clean framework integration
   - Declarative configuration
   - Automatic tool invocation handling

2. **Dependency Injection**
   ```python
   def __init__(self, config: AgentConfig | None = None,
                chat_client: Any | None = None):
       # Production: create client from config
       # Test: use provided mock client
   ```
   - Enables isolated unit testing
   - Clear separation of concerns
   - Supports both production and test modes

3. **Two-Tier Middleware**
   ```python
   {
       "agent": [agent_run_logging_middleware, observability_middleware],
       "function": [logging_function_middleware, activity_tracking_middleware]
   }
   ```
   - Agent-level: LLM request/response lifecycle
   - Function-level: Individual tool calls
   - Composable and testable

4. **Rich CLI Visualization**
   - Event-driven display system
   - Real-time progress visualization
   - Tree-based execution hierarchy
   - Status bar with model name and session info
   - Completion summaries

5. **Session Persistence**
   - Auto-save on exit
   - Context restoration
   - Session switching
   - Metadata tracking

6. **Structured Error Responses**
   ```python
   return {
       "success": False,
       "error": "resource_not_found",
       "message": "Resource 'example' not found. Use list_resources."
   }
   ```

### Anti-Patterns to Avoid

1. **Global State (CRITICAL)**
   ```python
   # ❌ BAD: Global instances
   _manager: Manager | None = None
   _config: Config | None = None

   def initialize_tools(config: AgentConfig) -> None:
       global _manager, _config
       _manager = Manager()
   ```
   **Problem**: Difficult to test, no type safety, initialization order dependencies

   **Solution**: Class-based toolsets with constructor injection

2. **Runtime Initialization**
   ```python
   # ❌ BAD: Every tool checks at runtime
   if not _manager or not _config:
       raise RuntimeError("Tools not initialized")
   ```
   **Problem**: No compile-time enforcement

   **Solution**: Factory pattern with type safety

3. **Tight Middleware-Display Coupling**
   ```python
   # ❌ BAD: Direct imports
   from agent.display import ToolStartEvent, get_event_emitter
   ```
   **Problem**: Cannot test middleware without display

   **Solution**: Event bus with observer registration

4. **Monolithic CLI**
   - Large files with many responsibilities mixed together

   **Solution**: Extract SessionManager, CommandHandler, InteractiveShell classes

5. **Low Core Test Coverage**
   ```toml
   omit = ["src/agent/tools.py"]  # ❌ Core logic excluded!
   ```
   **Problem**: High risk of regressions

   **Solution**: Class-based architecture enables mocking, target 85%+ coverage

### Project Current State
**Status**: Requirements only, no implementation exists

- `docs/design/requirements.md` - Generic chatbot agent requirements
- No `src/` directory yet
- No `tests/` directory yet

### Reference Implementations
For proven architectural patterns and best practices, refer to example implementations in the `ai-examples/` directory. These examples demonstrate:
- Agent framework integration patterns
- Tool registration and dependency injection
- Testing strategies with mocks
- CLI design and session management
- Middleware and event-driven architectures

## Relevant Files

### Files to Create

#### Core Architecture
- `src/agent/__init__.py` - Package initialization, version, exports
- `src/agent/agent.py` - Agent class, framework integration
- `src/agent/config.py` - AgentConfig dataclass with validation
- `src/agent/cli.py` - CLI entry point, argument parsing
- `src/agent/session.py` - SessionManager class (extracted from CLI)
- `src/agent/middleware.py` - Agent and function-level middleware
- `src/agent/events.py` - EventBus implementation for loose coupling

#### Display System
- `src/agent/display/__init__.py` - Display exports
- `src/agent/display/events.py` - Display event classes
- `src/agent/display/execution_tree.py` - Execution visualization
- `src/agent/display/execution_context.py` - Context tracking

#### Tool Architecture (MVP)
- `src/agent/tools/__init__.py` - Tool exports
- `src/agent/tools/toolset.py` - AgentToolset base class
- `src/agent/tools/hello.py` - HelloTools implementation (MVP)

#### Utilities
- `src/agent/utils/__init__.py` - Utility exports
- `src/agent/utils/errors.py` - Custom exception hierarchy

#### Testing
- `tests/conftest.py` - Shared fixtures
- `tests/mocks/__init__.py` - Mock exports
- `tests/mocks/mock_client.py` - MockChatClient implementation
- `tests/unit/__init__.py` - Unit test package
- `tests/unit/test_agent.py` - Agent tests
- `tests/unit/test_config.py` - Config tests
- `tests/unit/test_hello_tools.py` - Hello tool tests

#### Configuration
- `pyproject.toml` - Project configuration, dependencies, build settings
- `.env.example` - Environment variable template
- `README.md` - Project overview and quick start

## Implementation Plan

### Phase 1: Foundation Setup
Establish project structure, configuration, and core agent framework integration without tools.

**Goals**:
- Create Python package structure
- Configure build system and dependencies
- Implement AgentConfig with multi-provider LLM support
- Create basic Agent class with framework integration
- Set up testing infrastructure

### Phase 2: Tool Architecture (MVP)
Implement class-based toolset architecture with HelloTools demonstrating all patterns.

**Goals**:
- Create AgentToolset base class with dependency injection
- Implement HelloTools with `hello_world()` function
- Demonstrate tool registration and invocation
- Show structured error responses
- Achieve 85%+ test coverage for tool layer

### Phase 3: CLI & Display System
Build interactive CLI with execution visualization and session management.

**Goals**:
- Extract SessionManager from CLI
- Implement event bus for loose coupling
- Create execution visualization system
- Add startup banner, status bar, keyboard shortcuts
- Support interactive and single-prompt modes

## UI/UX Design Specification

This section defines the visual language, layout patterns, and user experience for the agent CLI.

### Design Principles

1. **Minimal & Clean** - Use simple, clear visual elements that don't distract
2. **Informative** - Provide status, timing, and progress information without overwhelming
3. **Scannable** - Use hierarchy and indentation for easy visual parsing
4. **Responsive** - Adapt verbosity based on user flags (quiet/normal/verbose)
5. **Professional** - Consistent use of icons, colors, and formatting

### Icon Set

Use Unicode characters for cross-platform compatibility:

| Icon | Purpose | Usage |
|------|---------|-------|
| `🤖` | Agent identity | App title, headers |
| `✓` | Success | Completed actions, available dependencies |
| `✗` | Error | Failed actions, missing dependencies |
| `●` | Primary bullet | Main list items |
| `•` | Secondary bullet | Nested/sub items |
| `→` | Tool call | Indicate tool invocation |
| `├──` | Tree branch | Execution tree (not last item) |
| `└──` | Tree end | Execution tree (last item) |
| `⏱` | Timing | Optional timing indicator |

### Color Scheme (via rich library)

| Color | Usage | Example |
|-------|-------|---------|
| `[green]` | Success, positive state | ✓ Available, ✓ Complete |
| `[red]` | Errors, critical issues | ✗ Failed, ✗ Missing |
| `[yellow]` | Warnings, info | ⚠ Warning, Interactive mode not ready |
| `[blue]` | Metadata, secondary info | Model names, timings |
| `[bold]` | Headers, emphasis | Section headers, User: Agent: |
| `[dim]` | Less important info | Timestamps, verbose details |

### Layout Patterns

#### 1. Command Output Header (Default Mode)

```
✓ Complete (2.3s) - msg:2 tool:1

[Agent response text here]

────────────────────────────────────────────────────────────────
```

**Components:**
- Status icon (✓/✗)
- Status text (Complete/Failed)
- Total timing in parentheses
- Message count (`msg:N`)
- Tool call count (`tool:N`)
- Response text (word-wrapped)
- Bottom separator line

#### 2. Verbose Execution Tree

```
• Phase 1: greet_user (1.2s)
├── • Thinking (1 messages) - Response received (1.0s)
└── • → greet_user - Complete (0.2s)

[Agent response text here]

────────────────────────────────────────────────────────────────
```

**Components:**
- Phase header with bullet and timing
- Tree structure for steps
- Thinking/reasoning steps
- Tool calls with → indicator
- Status per step
- Individual timings

#### 3. Health Check Display

```
🤖 Agent Health Check

Dependencies:
 ● python: ✓ Available (3.12.0)
 ● uv: ✓ Available (0.5.0)

Environment:
 ● Provider: OpenAI gpt-4o
 ● Data Dir: ~/.agent (exists)

✓ All checks passed!
```

**Components:**
- App icon and title header
- Section grouping (Dependencies, Environment)
- Indented list items with status
- Version/value information in parentheses
- Final status summary

#### 4. Configuration Display

```
🤖 Agent Configuration

LLM Provider:
 • Provider: OpenAI
 • Model: gpt-4o
 • API Key: ****abc123 (last 6 chars)

Agent Settings:
 • Data Directory: ~/.agent
 • Session Directory: ~/.agent/sessions
 • Log Level: info
```

**Components:**
- Grouped sections
- Key-value pairs with secondary bullets
- Sensitive data masking (API keys)
- Nested information

#### 5. Help Display

```
usage: agent [-h] [-p PROMPT] [-q] [-v] [--check] [--config] [--continue]
             [--version]

Agent - AI-powered conversational assistant with extensible tools

options:
  -h, --help            show this help message and exit
  -p PROMPT, --prompt PROMPT
                        Execute a single prompt and exit
  -q, --quiet           Minimal output (disables execution tree)
  -v, --verbose         Show detailed execution tree with phases and tools
  --check               Run health check for dependencies and configuration
  --config              Show current configuration
  --continue            Resume last saved session
  --version             show program's version number and exit
```

**Components:**
- Standard argparse format
- Clear one-line description
- Grouped options with descriptions
- Consistent flag naming

#### 6. Interactive Mode Banner

```
🤖 Agent v0.1.0

Type 'help' for commands, 'exit' to quit
Model: gpt-4o | Session: default

> _
```

**Components:**
- App icon, name, and version
- Quick help reminder
- Status line with model and session
- Prompt indicator (>)
- Cursor (_)

### Output Modes

#### Quiet Mode (`-q` / `--quiet`)

Minimal output, no execution tree:

```
[Agent response text only]
```

#### Normal Mode (default)

Shows summary timing and counts:

```
✓ Complete (2.3s) - msg:2 tool:1

[Agent response text]

────────────────────────────────────────────────────────────────
```

#### Verbose Mode (`-v` / `--verbose`)

Shows full execution tree:

```
• Phase 1: analysis (2.0s)
├── • Thinking (2 messages) - Response received (1.5s)
├── • → search_knowledge - Complete (0.3s)
└── • → format_results - Complete (0.2s)

• Phase 2: response (0.5s)
└── • Thinking (1 messages) - Response received (0.5s)

[Agent response text]

────────────────────────────────────────────────────────────────
```

### Timing Format

- **Duration < 1s**: `0.2s`
- **Duration 1-60s**: `5.3s`
- **Duration > 60s**: `2m 15s`

### Word Wrapping

- Default width: 80 characters
- Respect terminal width if available
- Clean breaks at word boundaries
- Indent continuation lines for lists

### Progress Indicators

For long-running operations:

```
Working... (3.2s elapsed)
```

Update in place using rich's Live display or simple carriage return.

### Error Display

```
✗ Error (0.5s)

Error: Configuration validation failed

Details:
 • Missing required environment variable: OPENAI_API_KEY
 • Please set in .env file or environment

See --help for configuration instructions
────────────────────────────────────────────────────────────────
```

**Components:**
- Error icon and status
- Clear error message
- Detailed list of issues
- Helpful next steps
- Separator line

### Interactive Mode Commands

Special commands in interactive mode (minimal set for MVP):

- `/help` - Show available commands
- `/exit` or `/quit` - Exit interactive mode
- `/clear` - Clear screen

**Note**: Session management is handled via CLI flags:
- `--continue` - Resume last saved session (command-line flag, not interactive command)
- Sessions auto-save on exit
- Use `--config` flag to view configuration (not an interactive command)

Additional interactive commands can be added in Phase 3 based on user needs.

Display command responses with consistent formatting.

### File Paths

Display file paths in a clear, clickable format:
- Full paths: `/Users/username/.agent/config.yaml`
- Relative paths: `./config.yaml`
- Use `[link]` tags if terminal supports hyperlinks

### Code Blocks

When displaying code or structured data:

```python
# Use syntax highlighting via rich
def hello_world():
    return "Hello, World!"
```

### Tables

For structured data display:

```
Configuration Values:
┌─────────────┬──────────────────────┐
│ Setting     │ Value                │
├─────────────┼──────────────────────┤
│ Provider    │ OpenAI               │
│ Model       │ gpt-4o               │
│ Data Dir    │ ~/.agent             │
└─────────────┴──────────────────────┘
```

Use rich's Table for automatic formatting and sizing.

### Implementation Notes

- Use `rich` library for all formatting
- Use `typer` for CLI argument parsing
- Respect `NO_COLOR` environment variable
- Support redirecting to files (strip formatting)
- Handle narrow terminals gracefully (minimum 60 chars)
- Use `Console.print()` for all output
- Use `Live()` for updating displays
- Use `Progress()` for long operations with known duration

## Architecture Decision Records (ADRs)

### Overview

An Architectural Decision (AD) is a justified software design choice that addresses a functional or non-functional requirement that is architecturally significant. An Architectural Decision Record (ADR) captures a single AD and its rationale.

**During implementation of this specification, all significant architectural decisions MUST be documented as ADRs.**

For more information, see [adr.github.io](https://adr.github.io/)

### When to Create an ADR

Create an ADR when you make a decision about:

1. **Architecture Patterns** - Tool registration, dependency injection, event bus design
2. **Technology Choices** - Framework selection, library decisions
3. **Design Patterns** - How components interact, abstraction layers
4. **API Designs** - Public interfaces, method signatures, response formats
5. **Naming Conventions** - Class names, module structure, terminology
6. **Testing Strategies** - Test organization, mocking patterns, coverage targets
7. **Performance Trade-offs** - Caching strategies, optimization choices
8. **Security Decisions** - Authentication methods, data handling
9. **UI/UX Patterns** - Display formats, interaction models

**Rule of thumb**: If the decision could be made differently and the alternative would be reasonable, document it with an ADR.

### ADR Workflow

1. **Create ADR File**
   - Copy `docs/decisions/adr-template.md` to `docs/decisions/NNNN-title-with-dashes.md`
   - Use next sequential number (0001, 0002, etc.)
   - Check existing ADRs and PRs to avoid number conflicts
   - For simpler decisions, use `docs/decisions/adr-short-template.md`

2. **Fill in ADR Content**
   - **Status**: Initially `proposed`
   - **Contact**: Your github id or name
   - **Date**: Current date (YYYY-MM-DD)
   - **Deciders**: List people who will approve the decision
   - **Consulted**: List people whose opinions were sought
   - **Informed**: List people who should know about the decision

3. **Document the Decision**
   - **Context and Problem Statement**: 2-3 sentences explaining the situation
   - **Decision Drivers**: List forces influencing the decision
   - **Considered Options**: List all alternatives considered
   - **Decision Outcome**: Chosen option and justification
   - **Pros and Cons**: For each option, list good/neutral/bad aspects
   - **Consequences**: Positive and negative impacts of the decision

4. **Update Status**
   - Change status to `accepted` once decision is agreed
   - Update date to reflect acceptance date

5. **Superseding Decisions**
   - Later decisions can supersede earlier ones
   - Update original ADR status: `superseded by [ADR-NNNN](NNNN-new-decision.md)`
   - Document any negative outcomes in original ADR

### ADR Template Structure

```markdown
---
status: proposed
contact: your-github-id
date: 2025-01-15
deciders: lead-dev, architect
consulted: team-member-1, team-member-2
informed: stakeholder-1
---

# Title: Class-based Toolset Architecture

## Context and Problem Statement

We need to decide how to structure tool registration and dependency
management for the agent. The current codebase has no implementation,
and we want to avoid common pitfalls like global state.

## Decision Drivers

- Testability: Must be easy to mock dependencies
- Type safety: Compile-time verification preferred
- Extensibility: Easy to add new tools
- Avoid global state

## Considered Options

1. Class-based toolsets with dependency injection
2. Function-based tools with global state
3. Plugin system with dynamic loading

## Decision Outcome

Chosen option: "Class-based toolsets with dependency injection"

This approach provides the best balance of testability, type safety,
and extensibility. Dependencies are explicitly passed through
constructors, making testing straightforward.

### Consequences

- Good: Easy to test with mocked dependencies
- Good: Type-safe initialization
- Good: Clear ownership of dependencies
- Bad: Slightly more boilerplate than function-based approach

## Pros and Cons of the Options

### Option 1: Class-based toolsets with dependency injection

- Good: Testable with mocked dependencies
- Good: Type-safe initialization via constructors
- Good: Clear dependency ownership
- Good: No global state
- Neutral: Requires more initial setup
- Bad: More boilerplate than functions

### Option 2: Function-based tools with global state

- Good: Less boilerplate code
- Good: Simple to implement initially
- Bad: Difficult to test (global state)
- Bad: No type safety for initialization
- Bad: Order-dependent initialization

### Option 3: Plugin system with dynamic loading

- Good: Very extensible
- Good: No code changes to add plugins
- Bad: More complex implementation
- Bad: Runtime errors vs compile-time
- Bad: Harder to debug
```

### ADR Examples to Create During Implementation

Based on the tasks in this specification, the following ADRs should be created:

1. **ADR-0001: Module and Package Naming Conventions**
   - Why: Python naming standards, package structure
   - When: Task 1 (Project Structure)

2. **ADR-0002: Repository Infrastructure and DevOps Setup**
   - Why: CI/CD approach, release automation, security scanning
   - When: Task 1 (Project Structure)

3. **ADR-0003: Configuration Management Strategy**
   - Why: Environment variables vs config files vs dataclasses
   - When: Task 2 (Configuration System)

4. **ADR-0004: Custom Exception Hierarchy Design**
   - Why: Structure of error types and inheritance
   - When: Task 3 (Custom Exception Hierarchy)

5. **ADR-0005: Event Bus Pattern for Loose Coupling**
   - Why: How to decouple middleware from display
   - When: Task 4 (Event Bus Implementation)

6. **ADR-0006: Class-based Toolset Architecture**
   - Why: Choosing between class-based vs function-based tools
   - When: Task 5 (AgentToolset Base Class)

7. **ADR-0007: Tool Response Format**
   - Why: How to structure tool responses (success/error format)
   - When: Task 6 (HelloTools Implementation)

8. **ADR-0008: Testing Strategy and Coverage Targets**
   - Why: Unit vs integration tests, mocking strategy, coverage goals
   - When: Tasks 7-10 (Testing tasks)

9. **ADR-0009: CLI Argument Design**
   - Why: Flag choices, command structure, interactive vs single-prompt
   - When: Task 9 (Basic CLI Entry Point)

10. **ADR-0010: Display Output Format and Verbosity Levels**
    - Why: Default/quiet/verbose modes, execution tree format
    - When: Phase 3 (CLI & Display System)

11. **ADR-0011: Session Management Architecture**
    - Why: How to persist and restore sessions
    - When: Phase 3 (Session Management)

### ADR Location and Organization

**File Location**: `docs/decisions/`

**File Structure**:
```
docs/decisions/
├── README.md                           # ADR process documentation
├── adr-template.md                     # Full template
├── adr-short-template.md               # Simplified template
├── 0001-class-based-toolsets.md       # Example ADR
├── 0002-event-bus-pattern.md          # Example ADR
└── ...
```

### ADR Best Practices

1. **Keep it Concise** - Focus on the decision, not implementation details
2. **List Alternatives** - Document what was considered and rejected
3. **State Constraints** - Explain limiting factors (time, resources, requirements)
4. **Be Honest** - Document trade-offs and downsides
5. **Update Status** - Keep ADRs current as decisions evolve
6. **Link Related ADRs** - Cross-reference related decisions
7. **Include Examples** - Show code snippets when helpful
8. **Think Future** - Consider how the decision might need to change

### Reference Implementation

See `ai-examples/agent-framework/docs/decisions/` for real-world examples of:
- Well-structured ADRs
- Decision drivers and rationale
- Pros/cons analysis
- Superseded decisions
- Naming conventions documentation

## Repository Infrastructure & DevOps

This section defines the essential repository structure, documentation, and automation needed for a production-ready project. Reference `ai-examples/` for working implementations.

### Documentation Files

#### README.md

**Purpose**: Primary project introduction and quick start guide

**Structure**:
```markdown
# Agent Template

[One-line description]

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview

[2-3 paragraph description of what the agent does]

[Example usage showing the value proposition]

**[📖 Full Usage Guide](docs/design/usage.md)** | **[🚀 Quick Start](#quick-setup)**

## Features

[Bulleted list of key features organized by category]

## Prerequisites

### Required
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- [List other required tools]

### Optional
- [List optional tools and their purpose]

## Quick Setup

```bash
# Installation steps
uv tool install git+https://github.com/your-org/agent-template.git

# Configuration steps
cp .env.example .env

# Verification
agent --check
agent --config
```

## Usage

[Brief usage examples - link to docs/design/usage.md for details]

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

## License (MIT)

[License type and link]
```

**Key Elements**:
- Badges for Python version, license, build status
- Clear value proposition in first paragraph
- Example usage showing outcomes
- Links to detailed documentation (docs/design/usage.md, CONTRIBUTING.md)
- Quick setup that gets users to "hello world" fast

#### docs/design/usage.md

**Purpose**: Comprehensive user guide with examples and patterns

**Structure**:
```markdown
# Usage Guide

Detailed guide for using the agent.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Configuration](#configuration)
3. [Command Reference](#command-reference)
4. [Examples](#examples)
5. [Troubleshooting](#troubleshooting)

## Basic Usage

### Single Prompt Mode

```bash
agent -p "your prompt here"
```

### Interactive Mode

```bash
agent

> your prompt
> /help    # Show commands
> /exit    # Exit
```

### Output Modes

- Default: Summary with timing
- Quiet (`-q`): Minimal output
- Verbose (`-v`): Full execution tree

## Configuration

### Environment Variables

[Table of all environment variables with descriptions and defaults]

### Configuration File

[If applicable, show .env format]

### Provider Setup

[Instructions for OpenAI, Azure OpenAI, etc.]

## Command Reference

### CLI Arguments

[Complete list of flags and options]

### Interactive Commands

[List all /commands available in interactive mode]

## Examples

### Example 1: [Common Task]

[Detailed example with explanation]

### Example 2: [Advanced Task]

[Detailed example with explanation]

## Troubleshooting

### Common Issues

[List frequent problems and solutions]

### Debug Mode

[How to enable verbose logging]
```

#### CONTRIBUTING.md

**Purpose**: Developer onboarding and contribution guidelines

**Structure**:
```markdown
# Contributing to Agent Template

Thank you for your interest in contributing!

## Development Setup

### Prerequisites

- Python 3.12+
- uv package manager
- Git
- [Other tools]

### Initial Setup

```bash
git clone https://github.com/your-org/agent-template.git
cd agent-template
uv sync
uv run agent --help
```

### Environment Configuration

```bash
cp .env.example .env
# Edit .env with required values
```

## Code Quality

### Quality Checks

Run before submitting PRs:

```bash
# Auto-fix formatting
uv run black src/agent/ tests/
uv run ruff check --fix src/agent/ tests/

# Verify checks pass
uv run black --check src/agent/ tests/
uv run ruff check src/agent/ tests/
uv run mypy src/agent/
uv run pytest --cov=src/agent --cov-fail-under=85
```

### CI Pipeline

Our GitHub Actions CI runs:
1. **Black**: Code formatting
2. **Ruff**: Linting
3. **MyPy**: Type checking
4. **PyTest**: Tests with 85% coverage
5. **CodeQL**: Security scanning

All checks must pass for merge.

### Testing

```bash
# Full test suite
uv run pytest

# With coverage
uv run pytest --cov=src/agent --cov-report=html
open htmlcov/index.html

# Specific tests
uv run pytest tests/unit/test_agent.py
```

## Commit Guidelines

This project uses [Conventional Commits](https://www.conventionalcommits.org/).

### Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Commit Types

- `feat`: New feature (minor version bump)
- `fix`: Bug fix (patch version bump)
- `docs`: Documentation
- `style`: Code style
- `refactor`: Refactoring
- `test`: Tests
- `chore`: Maintenance
- `ci`: CI/CD changes

### Breaking Changes

```
feat!: redesign CLI interface

BREAKING CHANGE: Command syntax has changed
```

## Pull Request Process

1. Create feature branch: `git checkout -b feat/your-feature`
2. Make changes with conventional commits
3. Run quality checks
4. Push and create PR
5. Address review feedback
6. Maintainers will merge when approved

## Architecture Decision Records

For significant decisions, create an ADR in `docs/decisions/`:

```bash
cp docs/decisions/adr-template.md docs/decisions/0001-your-decision.md
# Edit ADR and include in PR
```

See [docs/decisions/README.md](docs/decisions/README.md) for details.

## Code Style

- Line length: 100 characters
- Type hints: Required for public APIs
- Docstrings: Google style for public functions
- Test coverage: 85% minimum
```

#### LICENSE

**Recommended**: MIT

**Create**:
```bash
# MIT
# Create from template with your name/org
```

#### .gitignore

**Python-specific ignores**:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.hypothesis/

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# uv
.uv/
uv.lock  # If not committing lock file

# Agent-specific
.agent/
.local/
*.log
```

#### .env.example

**Template for environment variables**:
```bash
# ==============================================================================
# LLM Provider Configuration
# ==============================================================================
# Supported providers: openai, anthropic, azure_ai_foundry
LLM_PROVIDER=openai

# ==============================================================================
# OpenAI Configuration (when LLM_PROVIDER=openai)
# ==============================================================================
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o

# ==============================================================================
# Anthropic Configuration (when LLM_PROVIDER=anthropic)
# ==============================================================================
# ANTHROPIC_API_KEY=your-api-key-here
# ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# ==============================================================================
# Azure AI Foundry Configuration (when LLM_PROVIDER=azure_ai_foundry)
# ==============================================================================
# Requires: az login (uses AzureCliCredential)
# AZURE_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project-id
# AZURE_MODEL_DEPLOYMENT=gpt-4o

# ==============================================================================
# Agent Settings
# ==============================================================================
AGENT_DATA_DIR=~/.agent
LOG_LEVEL=info

# ==============================================================================
# Optional: Observability
# ==============================================================================
# APPLICATION_INSIGHTS_CONNECTION_STRING=your-connection-string
```

### GitHub Workflows

Location: `.github/workflows/`

#### 1. CI Workflow (`ci.yml`)

**Purpose**: Run tests and quality checks on every PR and push

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

# Cancel in-progress runs for same PR/branch
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: Test Python ${{ matrix.python-version }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
    - uses: actions/checkout@v5

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v6
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      uses: astral-sh/setup-uv@v7
      with:
        enable-cache: true
        cache-dependency-glob: "uv.lock"

    - name: Install dependencies
      run: |
        uv sync --frozen --prerelease=allow
        uv pip install -e .[dev]

    - name: Check code formatting with black
      id: black
      continue-on-error: true
      run: |
        uv run black --check src/agent/ tests/ --diff

    - name: Lint with ruff
      id: ruff
      continue-on-error: true
      run: |
        uv run ruff check src/agent/ tests/ --output-format=github

    - name: Type check with mypy
      id: mypy
      continue-on-error: true
      run: |
        uv run mypy src/agent --pretty

    - name: Run tests with coverage
      id: pytest
      continue-on-error: true
      timeout-minutes: 10
      run: |
        uv run pytest \
          --cov=src/agent \
          --cov-report=xml \
          --cov-report=term-missing \
          --cov-fail-under=85 \
          -v

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v5
      if: matrix.python-version == '3.12'
      continue-on-error: true
      with:
        files: ./coverage.xml
        fail_ci_if_error: false

    # Quality check summary
    - name: Quality Check Summary
      if: always()
      run: |
        echo "## Quality Check Summary" >> $GITHUB_STEP_SUMMARY

        # Check outcomes and generate summary
        [[ "${{ steps.black.outcome }}" == "failure" ]] && \
          echo "❌ Black formatting failed" >> $GITHUB_STEP_SUMMARY || \
          echo "✅ Black formatting passed" >> $GITHUB_STEP_SUMMARY

        [[ "${{ steps.ruff.outcome }}" == "failure" ]] && \
          echo "❌ Ruff linting failed" >> $GITHUB_STEP_SUMMARY || \
          echo "✅ Ruff linting passed" >> $GITHUB_STEP_SUMMARY

        [[ "${{ steps.mypy.outcome }}" == "failure" ]] && \
          echo "❌ MyPy type checking failed" >> $GITHUB_STEP_SUMMARY || \
          echo "✅ MyPy type checking passed" >> $GITHUB_STEP_SUMMARY

        [[ "${{ steps.pytest.outcome }}" == "failure" ]] && \
          echo "❌ PyTest failed" >> $GITHUB_STEP_SUMMARY || \
          echo "✅ PyTest passed" >> $GITHUB_STEP_SUMMARY

        # Fail if any check failed
        if [[ "${{ steps.black.outcome }}" == "failure" ]] || \
           [[ "${{ steps.ruff.outcome }}" == "failure" ]] || \
           [[ "${{ steps.mypy.outcome }}" == "failure" ]] || \
           [[ "${{ steps.pytest.outcome }}" == "failure" ]]; then
          exit 1
        fi
```

**Key Features**:
- Matrix testing for Python 3.12 and 3.13
- uv with dependency caching
- All quality checks (black, ruff, mypy, pytest)
- Continue-on-error to show all failures
- Summary generation
- Coverage upload to Codecov
- Concurrency control

#### 2. Release Workflow (`release.yml`)

**Purpose**: Automated releases using release-please

```yaml
name: Release

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  release-please:
    runs-on: ubuntu-latest
    outputs:
      release_created: ${{ steps.release.outputs.release_created }}
      tag_name: ${{ steps.release.outputs.tag_name }}
      pr: ${{ steps.release.outputs.pr }}
    steps:
      - uses: googleapis/release-please-action@v4
        id: release
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json

      # Update uv.lock when release PR is created/updated
      - name: Checkout release PR branch
        if: ${{ steps.release.outputs.pr }}
        uses: actions/checkout@v5
        with:
          ref: ${{ fromJson(steps.release.outputs.pr).headBranchName }}
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Install uv
        if: ${{ steps.release.outputs.pr }}
        uses: astral-sh/setup-uv@v7

      - name: Update uv.lock
        if: ${{ steps.release.outputs.pr }}
        run: uv lock

      - name: Commit updated uv.lock
        if: ${{ steps.release.outputs.pr }}
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email 'github-actions[bot]@users.noreply.github.com'
          git add uv.lock
          git diff --staged --quiet || git commit -m "chore: update uv.lock"
          git push

  build-artifacts:
    runs-on: ubuntu-latest
    needs: release-please
    if: needs.release-please.outputs.release_created == 'true'
    steps:
      - uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Build package
        run: |
          uv pip install --system build
          python -m build

      - name: Upload to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ needs.release-please.outputs.tag_name }}
          files: dist/*
```

**Key Features**:
- Automated version bumping based on conventional commits
- Release PR creation/updates
- uv.lock synchronization
- Package building and upload to GitHub Releases
- Separate jobs for release-please and artifact building

#### 3. Security Workflow (`security.yml`)

**Purpose**: Security scanning and SBOM generation

```yaml
name: Security Scanning

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:

permissions:
  contents: read
  security-events: write

jobs:
  dependency-review:
    name: Dependency Review
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v5
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: moderate

  sbom-generation:
    name: Generate SBOM
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v7

      - name: Install dependencies
        run: |
          uv sync --frozen
          uv pip install cyclonedx-bom

      - name: Generate SBOM
        run: uv run cyclonedx-py environment -o sbom.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v5
        with:
          name: sbom-${{ github.sha }}
          path: sbom.json
          retention-days: 90

  codeql-analysis:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v4
        with:
          languages: python
          queries: security-and-quality

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v4
```

**Key Features**:
- Dependency review on PRs
- SBOM generation using CycloneDX
- CodeQL security scanning
- Weekly scheduled scans
- Artifact retention

### GitHub Configuration Files

#### Dependabot (`dependabot.yml`)

**Purpose**: Automated dependency updates

```yaml
version: 2
updates:
  # Python dependencies (uv)
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
    open-pull-requests-limit: 5
    groups:
      python-dev:
        patterns:
          - "pytest*"
          - "mypy"
          - "black"
          - "ruff"
      python-prod:
        patterns:
          - "*"
        exclude-patterns:
          - "pytest*"
          - "mypy"
          - "black"
          - "ruff"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "04:00"
    open-pull-requests-limit: 3
```

**Key Features**:
- Weekly updates for Python dependencies and Actions
- Groups dependencies (dev vs prod)
- Limits concurrent PRs
- Scheduled on Monday mornings

### Release Automation

#### release-please-config.json

```json
{
  "packages": {
    ".": {
      "release-type": "python",
      "package-name": "agent-template",
      "bump-minor-pre-major": true,
      "bump-patch-for-minor-pre-major": true,
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance Improvements" },
        { "type": "docs", "section": "Documentation" },
        { "type": "refactor", "section": "Code Refactoring" },
        { "type": "test", "section": "Tests" },
        { "type": "build", "section": "Build System" },
        { "type": "ci", "section": "Continuous Integration" },
        { "type": "chore", "section": "Miscellaneous" }
      ]
    }
  }
}
```

#### .release-please-manifest.json

```json
{
  ".": "0.1.0"
}
```

**Features**:
- Conventional commits → automatic version bumping
- Organized changelog generation
- Pre-1.0 version handling
- Customizable changelog sections

### pyproject.toml Configuration

**Key sections for tooling**:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
asyncio_mode = "auto"
markers = [
    "integration: Integration tests",
]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
check_untyped_defs = true
strict_equality = true

[tool.black]
line-length = 100
target-version = ['py312']

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # function calls in argument defaults
]

[tool.ruff.lint.isort]
known-first-party = ["agent"]

[tool.coverage.run]
source = ["src/agent"]
omit = [
    "tests/*",
    "src/agent/display/*",  # Display logic hard to test
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
```

### Repository Setup Checklist

When setting up the repository:

- [ ] Create repository with Apache 2.0 or MIT license
- [ ] Set up branch protection rules for `main`:
  - [ ] Require PR reviews (1+ approvers)
  - [ ] Require status checks to pass (CI workflow)
  - [ ] Require branches to be up to date
  - [ ] Do not allow force pushes
  - [ ] Do not allow deletions
- [ ] Enable Dependabot
- [ ] Enable GitHub Actions
- [ ] Add repository secrets (if needed):
  - [ ] `CODECOV_TOKEN` (optional, for private repos)
  - [ ] `RELEASE_PLEASE_TOKEN` (optional, for fine-grained control)
- [ ] Set up repository topics/tags for discoverability
- [ ] Add repository description and website link
- [ ] Configure issue templates (optional)
- [ ] Set up project board (optional)

### ADR for Infrastructure Decisions

**ADR-0002: Repository Infrastructure and DevOps Setup** should document:
- Why release-please over manual releases
- Why conventional commits standard
- CI/CD tool choices (GitHub Actions vs alternatives)
- Coverage targets rationale (85% minimum)
- Security scanning approach (CodeQL, dependency review, SBOM)
- Why uv package manager
- Branch protection strategy

### Reference Implementation

See `ai-examples/` for working examples of:
- GitHub workflows (CI, release, security)
- Documentation structure
- Release automation
- Dependency management
- Code quality configuration

## Step by Step Tasks

### Task 1: Project Structure & Build Configuration
**Description**: Create Python package structure with modern build configuration, documentation, and DevOps infrastructure

**Files to create**:

**Core Project Files**:
- `pyproject.toml` - Project metadata, dependencies, build config, tool configs
- `src/agent/__init__.py` - Package init with version
- `.env.example` - Environment variable template
- `.gitignore` - Python, IDE, environment files
- `LICENSE` - Apache 2.0 or MIT license

**Documentation Files**:
- `README.md` - Project overview, installation, quick start
- `docs/design/usage.md` - Comprehensive user guide with examples
- `CONTRIBUTING.md` - Developer onboarding and contribution guidelines
- `CHANGELOG.md` - Version history (auto-generated by release-please)

**ADR Infrastructure** (already exists):
- `docs/decisions/README.md` - ADR process documentation
- `docs/decisions/adr-template.md` - Full ADR template
- `docs/decisions/adr-short-template.md` - Short ADR template

**GitHub Workflows**:
- `.github/workflows/ci.yml` - CI pipeline (tests, linting, type checking)
- `.github/workflows/release.yml` - Release automation with release-please
- `.github/workflows/security.yml` - Security scanning and SBOM generation
- `.github/dependabot.yml` - Automated dependency updates

**Release Configuration**:
- `release-please-config.json` - Release-please configuration
- `.release-please-manifest.json` - Version manifest

**Dependencies**:
```toml
[project]
name = "agent-template"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    # Microsoft Agent Framework (latest beta - Nov 6, 2025)
    "agent-framework>=1.0.0b251106",

    # Core dependencies
    "pydantic>=2.11.10",
    "python-dotenv>=1.1.1",
    "rich>=14.1.0",
    "prompt-toolkit>=3.0.0",
    "typer>=0.12.0",

    # LLM Provider SDKs (required by agent-framework)
    "openai>=1.58.1",
    "anthropic>=0.40.0",
    "azure-identity>=1.25.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-cov>=7.0.0",
    "ruff>=0.10.0",
    "black>=25.1.0",
    "mypy>=1.14.1",
]
```

**Validation**:
```bash
# Verify package structure
uv sync
uv run python -c "import agent; print(agent.__version__)"

# Verify workflows are valid
cat .github/workflows/ci.yml
cat .github/workflows/release.yml
cat .github/workflows/security.yml

# Verify documentation exists
ls -la README.md docs/design/usage.md CONTRIBUTING.md LICENSE
```

**Success criteria**:
- Package structure follows best practices
- Build system configured with all tool settings
- Dependencies resolved
- Import works
- All documentation files created
- GitHub workflows valid and ready
- Release automation configured
- Dependabot configured
- .gitignore covers all necessary patterns

**ADRs to Create**:
1. **ADR-0001: Module and Package Naming Conventions**
   - Document: Package structure (`src/agent/`), module naming, Python conventions
   - Decisions: Why `agent` vs other names, module organization rationale
   - Alternatives: Other package structures, naming schemes

2. **ADR-0002: Repository Infrastructure and DevOps Setup**
   - Document: CI/CD approach, release automation, security scanning
   - Decisions: GitHub Actions vs other CI, release-please vs manual, coverage targets
   - Alternatives: GitLab CI, Jenkins, manual releases, alternative scanners

---

### Task 2: Configuration System (AgentConfig)
**Description**: Implement AgentConfig dataclass with environment variable loading and multi-provider LLM support

**Files to create**:
- `src/agent/config.py` - AgentConfig dataclass

**Implementation details**:
```python
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
import os

@dataclass
class AgentConfig:
    """Configuration for Agent.

    Supports three LLM providers:
    - openai: OpenAI API (gpt-4o, gpt-4-turbo, etc.)
    - anthropic: Anthropic API (claude-sonnet-4-5, claude-opus-4, etc.)
    - azure_ai_foundry: Azure AI Foundry with managed models
    """

    # LLM Provider (openai, anthropic, or azure_ai_foundry)
    llm_provider: str

    # OpenAI (when llm_provider == "openai")
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # Anthropic (when llm_provider == "anthropic")
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Azure AI Foundry (when llm_provider == "azure_ai_foundry")
    azure_project_endpoint: str | None = None
    azure_model_deployment: str | None = None
    # Uses AzureCliCredential for auth, no API key needed

    # Agent-specific
    agent_data_dir: Path | None = None
    agent_session_dir: Path | None = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        load_dotenv()

        llm_provider = os.getenv("LLM_PROVIDER", "openai")

        config = cls(
            llm_provider=llm_provider,
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            # Anthropic
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
            # Azure AI Foundry
            azure_project_endpoint=os.getenv("AZURE_PROJECT_ENDPOINT"),
            azure_model_deployment=os.getenv("AZURE_MODEL_DEPLOYMENT"),
        )

        # Set default paths
        home = Path.home()
        config.agent_data_dir = Path(os.getenv("AGENT_DATA_DIR", home / ".agent"))
        config.agent_session_dir = config.agent_data_dir / "sessions"

        return config

    def validate(self) -> None:
        """Validate configuration."""
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI requires API key (OPENAI_API_KEY)")
        elif self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic requires API key (ANTHROPIC_API_KEY)")
        elif self.llm_provider == "azure_ai_foundry":
            if not self.azure_project_endpoint:
                raise ValueError("Azure AI Foundry requires project endpoint (AZURE_PROJECT_ENDPOINT)")
            if not self.azure_model_deployment:
                raise ValueError("Azure AI Foundry requires model deployment (AZURE_MODEL_DEPLOYMENT)")
            # Note: Uses AzureCliCredential for auth, user must be logged in via `az login`
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_provider}. "
                           f"Supported: openai, anthropic, azure_ai_foundry")

    def get_model_display_name(self) -> str:
        """Get display name for current model."""
        if self.llm_provider == "openai":
            return f"OpenAI/{self.openai_model}"
        elif self.llm_provider == "anthropic":
            return f"Anthropic/{self.anthropic_model}"
        elif self.llm_provider == "azure_ai_foundry":
            return f"Azure AI Foundry/{self.azure_model_deployment}"
        return "Unknown"
```

**Testing**:
- `tests/unit/test_config.py` - Test env loading, validation, defaults

**Validation**:
```bash
uv run pytest tests/unit/test_config.py -v
```

**Success criteria**:
- Config loads from environment for all three providers (OpenAI, Anthropic, Azure AI Foundry)
- Validation catches missing values for each provider
- Multi-provider support works correctly
- Provider-specific validation enforces required fields
- Tests pass with 100% coverage for all three providers

**ADR to Create**:
- **ADR-0003: Configuration Management Strategy**
  - Document: Environment variables approach, dataclass design, multi-provider support (OpenAI, Anthropic, Azure AI Foundry)
  - Decisions: Why env vars vs config files, validation strategy per provider, default paths, authentication methods
  - Alternatives: YAML/TOML config files, pydantic BaseSettings, config registry, unified auth

---

### Task 3: Custom Exception Hierarchy
**Description**: Define domain-specific exceptions for clear error handling

**Files to create**:
- `src/agent/utils/__init__.py`
- `src/agent/utils/errors.py`

**Implementation**:
```python
"""Custom exceptions for Agent."""

class AgentError(Exception):
    """Base exception for Agent errors."""
    pass

class ConfigurationError(AgentError):
    """Configuration validation errors."""
    pass

class ToolError(AgentError):
    """Tool execution errors."""
    pass

class ToolNotFoundError(ToolError):
    """Tool not found in registry."""
    pass

class ToolExecutionError(ToolError):
    """Tool execution failed."""
    pass

# Future: Domain-specific errors
class APIError(AgentError):
    """API integration errors."""
    pass

class ResourceNotFoundError(APIError):
    """Resource not found."""
    pass
```

**Success criteria**:
- Exception hierarchy defined
- Imports work correctly

**ADR to Create**:
- **ADR-0004: Custom Exception Hierarchy Design**
  - Document: Exception inheritance structure, base classes, domain-specific errors
  - Decisions: Single base `AgentError` vs multiple bases, granularity of error types
  - Alternatives: Flat exception structure, using standard exceptions only, error codes

---

### Task 4: Event Bus Implementation
**Description**: Create event bus for loose coupling between middleware and display

**Files to create**:
- `src/agent/events.py` - EventBus singleton with observer pattern

**Pattern**:
```python
from typing import Any, Callable, Protocol
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    """Event types for the event bus."""
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"
    TOOL_ERROR = "tool_error"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"

@dataclass
class Event:
    """Base event class."""
    type: EventType
    data: dict[str, Any]

class EventListener(Protocol):
    """Protocol for event listeners."""
    def handle_event(self, event: Event) -> None: ...

class EventBus:
    """Singleton event bus for loose coupling."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = []
        return cls._instance

    def subscribe(self, listener: EventListener) -> None:
        """Subscribe to events."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """Unsubscribe from events."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def emit(self, event: Event) -> None:
        """Emit event to all listeners."""
        for listener in self._listeners:
            listener.handle_event(event)

    def clear(self) -> None:
        """Clear all listeners (for testing)."""
        self._listeners.clear()

def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    return EventBus()
```

**Testing**:
- `tests/unit/test_events.py` - Test subscription, emission, clearing

**Success criteria**:
- Event bus implements observer pattern
- Subscribers receive events
- Singleton behavior works
- Tests pass

**ADR to Create**:
- **ADR-0005: Event Bus Pattern for Loose Coupling**
  - Document: Observer pattern implementation, singleton design, event types
  - Decisions: Singleton vs dependency injection, protocol-based listeners
  - Alternatives: Direct coupling, callback registration, pub/sub library

---

### Task 5: AgentToolset Base Class
**Description**: Create base class for toolsets with dependency injection (avoiding global state)

**Files to create**:
- `src/agent/tools/__init__.py`
- `src/agent/tools/toolset.py`

**Pattern**:
```python
from abc import ABC, abstractmethod
from typing import Callable
from agent.config import AgentConfig

class AgentToolset(ABC):
    """Base class for Agent toolsets.

    Toolsets encapsulate related tools with shared dependencies.
    This avoids global state and enables dependency injection for testing.
    """

    def __init__(self, config: AgentConfig):
        """Initialize toolset with configuration.

        Args:
            config: Agent configuration with LLM settings and paths
        """
        self.config = config

    @abstractmethod
    def get_tools(self) -> list[Callable]:
        """Get list of tool functions.

        Returns:
            List of callable tool functions with proper type hints
            and docstrings for LLM consumption.
        """
        pass

    def _create_success_response(self, result: Any, message: str = "") -> dict:
        """Create standardized success response.

        Args:
            result: Tool execution result
            message: Optional success message

        Returns:
            Structured response dict with success=True
        """
        return {
            "success": True,
            "result": result,
            "message": message,
        }

    def _create_error_response(self, error: str, message: str) -> dict:
        """Create standardized error response.

        Args:
            error: Machine-readable error code
            message: Human-friendly error message

        Returns:
            Structured response dict with success=False
        """
        return {
            "success": False,
            "error": error,
            "message": message,
        }
```

**Success criteria**:
- Base class defined with abstract method
- Helper methods for responses
- No global state

**ADR to Create**:
- **ADR-0006: Class-based Toolset Architecture**
  - Document: Abstract base class design, dependency injection pattern, helper methods
  - Decisions: ABC vs Protocol, constructor injection, structured response format
  - Alternatives: Function-based tools, global state, plugin system

---

### Task 6: HelloTools Implementation (MVP)
**Description**: Implement HelloTools class with `hello_world()` function demonstrating all tool patterns

**Files to create**:
- `src/agent/tools/hello.py`

**Implementation**:
```python
from typing import Annotated
from pydantic import Field
from agent.tools.toolset import AgentToolset
from agent.config import AgentConfig

class HelloTools(AgentToolset):
    """Hello World tools for demonstrating tool architecture."""

    def __init__(self, config: AgentConfig):
        """Initialize HelloTools with configuration."""
        super().__init__(config)

    def get_tools(self) -> list:
        """Get list of hello tools."""
        return [self.hello_world, self.greet_user]

    async def hello_world(
        self,
        name: Annotated[str, Field(description="Name to greet")] = "World"
    ) -> dict:
        """Say hello to someone.

        Args:
            name: Name of person to greet (default: "World")

        Returns:
            Success response with greeting message

        Example:
            >>> tools = HelloTools(config)
            >>> result = await tools.hello_world("Alice")
            >>> print(result)
            {'success': True, 'result': 'Hello, Alice!', 'message': ''}
        """
        greeting = f"Hello, {name}!"
        return self._create_success_response(
            result=greeting,
            message=f"Greeted {name}"
        )

    async def greet_user(
        self,
        name: Annotated[str, Field(description="User's name")],
        language: Annotated[str, Field(description="Language code (en, es, fr)")] = "en"
    ) -> dict:
        """Greet user in different languages.

        Args:
            name: User's name
            language: Language code (en, es, fr)

        Returns:
            Success response with localized greeting or error if unsupported language
        """
        greetings = {
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!",
            "fr": f"Bonjour, {name}!",
        }

        if language not in greetings:
            return self._create_error_response(
                error="unsupported_language",
                message=f"Language '{language}' not supported. Use: en, es, fr"
            )

        return self._create_success_response(
            result=greetings[language],
            message=f"Greeted {name} in {language}"
        )
```

**Testing**:
- `tests/unit/test_hello_tools.py` - Test all paths, error cases

**Test implementation**:
```python
import pytest
from agent.tools.hello import HelloTools
from agent.config import AgentConfig

@pytest.fixture
def hello_tools(mock_config):
    """Create HelloTools instance for testing."""
    return HelloTools(mock_config)

@pytest.mark.asyncio
async def test_hello_world_default(hello_tools):
    """Test hello_world with default name."""
    result = await hello_tools.hello_world()
    assert result["success"] is True
    assert result["result"] == "Hello, World!"

@pytest.mark.asyncio
async def test_hello_world_custom_name(hello_tools):
    """Test hello_world with custom name."""
    result = await hello_tools.hello_world("Alice")
    assert result["success"] is True
    assert result["result"] == "Hello, Alice!"

@pytest.mark.asyncio
async def test_greet_user_english(hello_tools):
    """Test greet_user in English."""
    result = await hello_tools.greet_user("Bob", "en")
    assert result["success"] is True
    assert result["result"] == "Hello, Bob!"

@pytest.mark.asyncio
async def test_greet_user_unsupported_language(hello_tools):
    """Test greet_user with unsupported language."""
    result = await hello_tools.greet_user("Alice", "de")
    assert result["success"] is False
    assert result["error"] == "unsupported_language"
```

**Validation**:
```bash
# From project root
uv run pytest tests/unit/test_hello_tools.py -v --cov=src/agent/tools/hello
```

**Success criteria**:
- Both tools implemented
- Structured responses
- Error handling works
- Tests achieve 100% coverage

**ADR to Create**:
- **ADR-0007: Tool Response Format**
  - Document: Structured success/error response format, field naming, error codes
  - Decisions: Dict vs dataclass responses, required vs optional fields
  - Alternatives: Exceptions for errors, simple return values, Result type

---

### Task 7: Mock Chat Client for Testing
**Description**: Create MockChatClient for testing agent without LLM calls

**Files to create**:
- `tests/mocks/__init__.py`
- `tests/mocks/mock_client.py`

**Reference**: See `ai-examples/` for testing patterns

**Implementation**:
```python
from typing import Any, AsyncIterator

class MockAgent:
    """Mock agent for testing."""

    def __init__(self, response: str = "Mock response"):
        self.response = response

    async def run_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream mock response."""
        for word in self.response.split():
            yield word + " "

    async def run(self, prompt: str, **kwargs) -> str:
        """Return full mock response."""
        return self.response

class MockChatClient:
    """Mock chat client for testing."""

    def __init__(self, response: str = "Mock response"):
        self.response = response
        self.created_agents = []

    def create_agent(
        self,
        name: str,
        instructions: str,
        tools: list = None,
        middleware: dict = None,
        context_providers: list = None,
        **kwargs
    ) -> MockAgent:
        """Create mock agent."""
        agent = MockAgent(self.response)
        self.created_agents.append({
            "name": name,
            "instructions": instructions,
            "tools": tools or [],
            "middleware": middleware or {},
        })
        return agent
```

**Success criteria**:
- Mock client creates mock agents
- Mock agents return configurable responses
- Supports async operations

---

### Task 8: Agent Class Implementation
**Description**: Create Agent class with framework integration and tool registration

**Files to create**:
- `src/agent/agent.py`

**Reference**: See `ai-examples/` for agent implementation patterns

**Implementation**:
```python
from typing import Any
from agent_framework.openai import OpenAIChatClient
from agent_framework.anthropic import AnthropicClient
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from agent.config import AgentConfig
from agent.tools.toolset import AgentToolset
from agent.tools.hello import HelloTools

class Agent:
    """Agent with multi-provider LLM support and extensible tools."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        chat_client: Any | None = None,
        toolsets: list[AgentToolset] | None = None,
    ):
        """Initialize Agent.

        Args:
            config: Agent configuration (required if chat_client not provided)
            chat_client: Chat client (for testing, optional)
            toolsets: List of toolsets (default: HelloTools)
        """
        self.config = config or AgentConfig.from_env()

        # Dependency injection for testing
        if chat_client is not None:
            self.chat_client = chat_client
        else:
            self.chat_client = self._create_chat_client()

        # Initialize toolsets (avoid global state)
        if toolsets is None:
            toolsets = [HelloTools(self.config)]
        self.toolsets = toolsets

        # Collect all tools from toolsets
        self.tools = []
        for toolset in self.toolsets:
            self.tools.extend(toolset.get_tools())

        # Create agent
        self.agent = self._create_agent()

    def _create_chat_client(self) -> Any:
        """Create chat client based on configuration.

        Supports:
        - openai: OpenAI API (gpt-4o, gpt-4-turbo, etc.)
        - anthropic: Anthropic API (claude-sonnet-4-5, claude-opus-4, etc.)
        - azure_ai_foundry: Azure AI Foundry with managed models
        """
        if self.config.llm_provider == "openai":
            return OpenAIChatClient(
                model_id=self.config.openai_model,
                api_key=self.config.openai_api_key,
            )
        elif self.config.llm_provider == "anthropic":
            return AnthropicClient(
                model_id=self.config.anthropic_model,
                api_key=self.config.anthropic_api_key,
            )
        elif self.config.llm_provider == "azure_ai_foundry":
            return AzureAIAgentClient(
                project_endpoint=self.config.azure_project_endpoint,
                model_deployment_name=self.config.azure_model_deployment,
                async_credential=AzureCliCredential(),
            )
        else:
            raise ValueError(
                f"Unknown provider: {self.config.llm_provider}. "
                f"Supported: openai, anthropic, azure_ai_foundry"
            )

    def _create_agent(self) -> Any:
        """Create agent with tools."""
        instructions = """You are a helpful AI assistant that can use tools to assist with various tasks.

You help users with:
- Natural language interactions
- Information synthesis and summarization
- Tool-based task execution
- Context-aware conversations

Be helpful, concise, and clear in your responses."""

        return self.chat_client.create_agent(
            name="Agent",
            instructions=instructions,
            tools=self.tools,
        )

    async def run(self, prompt: str) -> str:
        """Run agent with prompt.

        Args:
            prompt: User prompt

        Returns:
            Agent response
        """
        return await self.agent.run(prompt)

    async def run_stream(self, prompt: str):
        """Run agent with streaming response.

        Args:
            prompt: User prompt

        Yields:
            Response chunks
        """
        async for chunk in self.agent.run_stream(prompt):
            yield chunk
```

**Testing**:
- `tests/unit/test_agent.py` - Test agent creation, tool registration

**Test fixture** (`tests/conftest.py`):
```python
import pytest
from agent.config import AgentConfig
from agent.agent import Agent
from tests.mocks.mock_client import MockChatClient

@pytest.fixture
def mock_openai_config():
    """Create mock OpenAI configuration."""
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4o",
    )

@pytest.fixture
def mock_anthropic_config():
    """Create mock Anthropic configuration."""
    return AgentConfig(
        llm_provider="anthropic",
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-4-5-20250929",
    )

@pytest.fixture
def mock_azure_foundry_config():
    """Create mock Azure AI Foundry configuration."""
    return AgentConfig(
        llm_provider="azure_ai_foundry",
        azure_project_endpoint="https://test-project.services.ai.azure.com/api/projects/test",
        azure_model_deployment="gpt-4o",
    )

@pytest.fixture
def mock_config(mock_openai_config):
    """Default mock configuration (OpenAI)."""
    return mock_openai_config

@pytest.fixture
def mock_chat_client():
    """Create mock chat client."""
    return MockChatClient(response="Hello from mock!")

@pytest.fixture
def agent_instance(mock_config, mock_chat_client):
    """Create agent with mocks."""
    return Agent(
        config=mock_config,
        chat_client=mock_chat_client,
    )
```

**Validation**:
```bash
# From project root
uv run pytest tests/unit/test_agent.py -v --cov=src/agent/agent
```

**Success criteria**:
- Agent initializes with tools
- Tools registered correctly
- Mock client works in tests
- Tests pass with 85%+ coverage

---

### Task 9: Basic CLI Entry Point
**Description**: Create minimal CLI entry point for testing agent interactions

**Files to create**:
- `src/agent/cli.py` - Basic CLI (will be enhanced in Phase 3)
- `src/agent/__main__.py` - Enable `python -m agent`

**Implementation** (minimal for MVP):
```python
# src/agent/cli.py
import asyncio
import typer
from rich.console import Console
from agent.config import AgentConfig
from agent.agent import Agent

app = typer.Typer()
console = Console()

@app.command()
def main(
    prompt: str = typer.Option(None, "-p", "--prompt", help="Single prompt to execute"),
    check: bool = typer.Option(False, "--check", help="Check configuration"),
):
    """Agent - Generic chatbot agent CLI."""

    if check:
        config = AgentConfig.from_env()
        try:
            config.validate()
            console.print("[green]✓[/green] Configuration valid")
            console.print(f"  Provider: {config.llm_provider}")
            console.print(f"  Model: {config.get_model_display_name()}")
        except ValueError as e:
            console.print(f"[red]✗[/red] Configuration error: {e}")
            raise typer.Exit(1)
        return

    if prompt:
        # Single-prompt mode
        asyncio.run(run_single_prompt(prompt))
    else:
        console.print("[yellow]Interactive mode not implemented yet[/yellow]")
        console.print("Use: agent -p 'your prompt here'")

async def run_single_prompt(prompt: str):
    """Run single prompt and display response."""
    config = AgentConfig.from_env()
    agent = Agent(config=config)

    console.print(f"\n[bold]User:[/bold] {prompt}\n")
    console.print("[bold]Agent:[/bold] ", end="")

    async for chunk in agent.run_stream(prompt):
        console.print(chunk, end="")

    console.print("\n")

if __name__ == "__main__":
    app()
```

```python
# src/agent/__main__.py
from agent.cli import app

if __name__ == "__main__":
    app()
```

**Update** `pyproject.toml`:
```toml
[project.scripts]
agent = "agent.cli:app"
```

**Validation**:
```bash
# From project root

# Check configuration
uv run agent --check

# Test single prompt
uv run agent -p "Say hello to Alice"
```

**Success criteria**:
- CLI executable works
- Configuration check works
- Single-prompt mode works
- Agent uses HelloTools

---

### Task 10: Integration Tests
**Description**: Create integration tests that exercise the full stack (config → agent → tools)

**Files to create**:
- `tests/integration/__init__.py`
- `tests/integration/test_hello_integration.py`

**Implementation**:
```python
import pytest
from agent.config import AgentConfig
from agent.agent import Agent
from agent.tools.hello import HelloTools
from tests.mocks.mock_client import MockChatClient

@pytest.mark.asyncio
async def test_agent_with_hello_tools():
    """Test full agent integration with HelloTools."""
    config = AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4o",
    )

    # Use mock client to avoid real LLM calls
    mock_client = MockChatClient(response="Hello from integration test!")

    # Create agent with HelloTools
    toolsets = [HelloTools(config)]
    agent = Agent(config=config, chat_client=mock_client, toolsets=toolsets)

    # Verify tools registered
    assert len(agent.tools) == 2
    assert agent.tools[0].__name__ == "hello_world"
    assert agent.tools[1].__name__ == "greet_user"

    # Run agent
    response = await agent.run("Say hello")
    assert response == "Hello from integration test!"

@pytest.mark.asyncio
async def test_hello_tools_directly():
    """Test HelloTools can be instantiated and called directly."""
    config = AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
    )

    tools = HelloTools(config)

    # Test hello_world
    result = await tools.hello_world("Integration Test")
    assert result["success"] is True
    assert "Integration Test" in result["result"]

    # Test greet_user
    result = await tools.greet_user("Integration", "es")
    assert result["success"] is True
    assert "¡Hola" in result["result"]
```

**Validation**:
```bash
# From project root
uv run pytest tests/integration/ -v
```

**Success criteria**:
- Integration tests pass
- Full stack works end-to-end
- Tools callable directly and through agent

---

### Task 11: Repository Infrastructure & Documentation
**Description**: Create all repository infrastructure, documentation files, and GitHub workflows

**Reference**: See "Repository Infrastructure & DevOps" section above for complete specifications and examples

**Files to create**:

1. **Documentation Files**:
   - `README.md` - Follow structure from "Repository Infrastructure & DevOps" section
   - `docs/design/usage.md` - Comprehensive user guide
   - `CONTRIBUTING.md` - Developer guidelines
   - `docs/architecture/tool-architecture.md` - Architecture documentation

2. **GitHub Workflows**:
   - `.github/workflows/ci.yml` - CI pipeline (copy from specs section)
   - `.github/workflows/release.yml` - Release automation
   - `.github/workflows/security.yml` - Security scanning
   - `.github/dependabot.yml` - Dependency updates

3. **Release Configuration**:
   - `release-please-config.json` - Release-please setup
   - `.release-please-manifest.json` - Initial version (0.1.0)

4. **Additional Files** (if not already created in Task 1):
   - `LICENSE` - Apache 2.0 or MIT
   - `.gitignore` - Comprehensive Python ignores
   - `.env.example` - Environment template

**Implementation Steps**:

1. Create `README.md` with:
   - Project title and one-line description
   - Badges (Python version, license, build status)
   - Overview and value proposition
   - Features organized by category
   - Prerequisites (required and optional)
   - Quick setup instructions
   - Usage examples
   - Links to docs/design/usage.md and CONTRIBUTING.md
   - License information

2. Create `docs/design/usage.md` with:
   - Table of contents
   - Basic usage (single-prompt and interactive modes)
   - Configuration guide (environment variables, providers)
   - Command reference (all CLI flags and interactive commands)
   - Examples for common tasks
   - Troubleshooting section

3. Create `CONTRIBUTING.md` with:
   - Development setup instructions
   - Code quality requirements
   - Testing guidelines
   - Commit message format (conventional commits)
   - Pull request process
   - ADR process reference

4. Create GitHub workflows using templates from specs section

5. Create `docs/architecture/tool-architecture.md` documenting:
   - Class-based toolset pattern
   - Dependency injection approach
   - Event bus design
   - Testing strategy
   - Anti-patterns avoided

**Validation**:
```bash
# Check all documentation exists
ls -la README.md docs/design/usage.md CONTRIBUTING.md LICENSE

# Check GitHub workflows
ls -la .github/workflows/

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"
python -c "import yaml; yaml.safe_load(open('.github/workflows/security.yml'))"

# Check release-please config
cat release-please-config.json .release-please-manifest.json

# Validate documentation links
grep -r "docs/design/usage.md\|CONTRIBUTING.md" README.md

# Test workflows locally (optional, requires act)
# act -l  # List workflows
```

**Success criteria**:
- All documentation files created and comprehensive
- README links to docs/design/usage.md and CONTRIBUTING.md
- CONTRIBUTING.md includes ADR process
- All GitHub workflows created and valid
- Release automation configured
- Dependabot configured
- Architecture documentation complete
- Examples are clear and generic

**ADRs Referenced**:
- **ADR-0002**: Documents why we chose this CI/CD and release approach
- **ADR-0010**: Documents display/UI patterns (if Phase 3 complete)

---

## Testing Strategy

### Unit Tests
All unit tests use mocked dependencies to test components in isolation:

- `tests/unit/test_config.py` - Configuration loading, validation, multi-provider
- `tests/unit/test_events.py` - Event bus subscription, emission, clearing
- `tests/unit/test_hello_tools.py` - HelloTools both functions, error cases
- `tests/unit/test_agent.py` - Agent initialization, tool registration

**Target**: 100% coverage for unit-testable code

### Integration Tests
Integration tests verify full stack without mocking internal components:

- `tests/integration/test_hello_integration.py` - Full agent → tools flow
- Future: GitLab tools integration tests (with mocked GitLab API)

**Target**: 85%+ coverage overall

### Test Fixtures
Shared fixtures in `tests/conftest.py`:

- `mock_openai_config` - Test AgentConfig with OpenAI
- `mock_anthropic_config` - Test AgentConfig with Anthropic
- `mock_azure_foundry_config` - Test AgentConfig with Azure AI Foundry
- `mock_config` - Default mock configuration (aliases mock_openai_config)
- `mock_chat_client` - MockChatClient for agent testing
- `agent_instance` - Fully constructed Agent with mocks

### Mocks
- `tests/mocks/mock_client.py` - MockChatClient and MockAgent for testing framework integration

### Edge Cases to Test
- Missing environment variables for each provider
- Invalid LLM provider name
- Missing required fields per provider (API keys, endpoints, deployments)
- Unsupported language in greet_user
- Empty tool lists
- Multiple toolsets registration
- Event bus with no subscribers
- Provider-specific authentication failures

## Acceptance Criteria

- [ ] Project structure created with proper Python packaging and all infrastructure files
- [ ] AgentConfig supports all three LLM providers (OpenAI, Anthropic, Azure AI Foundry)
- [ ] AgentToolset base class defined with dependency injection
- [ ] HelloTools implemented with 2 functions demonstrating all patterns
- [ ] Agent integrates with Microsoft Agent Framework (v1.0.0b251106+)
- [ ] Agent class supports creating clients for all three providers
- [ ] Event bus implements observer pattern for loose coupling
- [ ] Custom exception hierarchy defined
- [ ] MockChatClient enables testing without LLM calls
- [ ] CLI supports `--check`, `--config`, `--continue`, and single-prompt mode
- [ ] Unit tests achieve 85%+ coverage
- [ ] Integration tests verify full stack with all three provider configs
- [ ] README, docs/design/usage.md, and CONTRIBUTING.md created
- [ ] GitHub workflows created (CI, release, security)
- [ ] Release automation configured (release-please)
- [ ] Dependabot configured
- [ ] All ADRs created for significant decisions
- [ ] No global state in tool architecture
- [ ] All architectural anti-patterns avoided

## Validation Commands

```bash
# From project root

# Install dependencies
uv sync

# Run all tests with coverage
uv run pytest tests/ -v --cov=src/agent --cov-report=term-missing --cov-report=html

# Run only unit tests
uv run pytest tests/unit/ -v

# Run only integration tests
uv run pytest tests/integration/ -v

# Check code quality
uv run ruff check src/ tests/
uv run black --check src/ tests/
uv run mypy src/

# Build package
uv build

# Test CLI
uv run agent --check
uv run agent -p "Say hello to Alice"

# Check coverage report
open htmlcov/index.html
```

## Notes

### Architectural Flaws Avoided

This implementation explicitly avoids 7 common architectural flaws:

1. ✅ **No Global State** - AgentToolset uses class-based architecture
2. ✅ **No Runtime Initialization** - Dependencies injected in constructor
3. ✅ **Loose Coupling** - Event bus separates middleware from display
4. ✅ **Simple Patterns** - Avoid fragile pattern matching
5. ✅ **High Test Coverage** - Target 85%+ including core logic
6. ✅ **Modular CLI** - Will extract SessionManager in Phase 3
7. ✅ **Clear Contracts** - Simple, single-phase patterns

### Future Enhancements (Phase 3+)

**CLI & Display**:
- SessionManager extraction from CLI
- Execution visualization with Rich
- Status bar with model name and session info
- Interactive shell with prompt_toolkit
- Keyboard shortcuts for common operations
- Auto-save and session resume

**Middleware**:
- Agent-level logging middleware
- Function-level activity tracking
- Observability middleware
- Event emission from middleware

**Tools**:
- APITools for custom API integrations
- DataTools for data processing
- WebTools for web scraping and content fetching
- FileTools for file system operations

**Architecture**:
- Plugin system for third-party tools
- Circuit breaker for API failures
- Caching layer for improved performance
- Webhook support for async operations

### Development Workflow

1. **TDD Approach**: Write tests before implementation
2. **Incremental**: Complete each task before moving to next
3. **Validation**: Run tests and validation commands after each task
4. **Documentation**: Update docs as architecture evolves

### Success Metrics

- ✅ All acceptance criteria met
- ✅ All validation commands pass
- ✅ Test coverage ≥85%
- ✅ No global state in codebase
- ✅ All tools return structured responses
- ✅ CLI executable works
- ✅ README documentation complete

## Execution

This spec can be implemented using: `/implement docs/specs/foundation.md`

### Archon Integration

When implementing, the `/implement` command will:
1. Create Archon project: "CLI Agent Tool Architecture"
2. Create tasks from each "Task N" section
3. Track progress using Archon task management
4. Mark tasks as doing → review → done
5. Link to this specification document

### Estimated Timeline

- **Phase 1 (Foundation)**: Tasks 1-4, ~4 hours
- **Phase 2 (Tool Architecture)**: Tasks 5-8, ~6 hours
- **Phase 3 (CLI & Tests)**: Tasks 9-11, ~4 hours

**Total**: ~14 hours for MVP implementation

### Next Steps After MVP

1. Implement display system (execution visualization)
2. Add session management
3. Create custom tool integrations for specific domains
4. Add domain-specific extensions (e.g., data processing, web scraping)
5. Add middleware for logging and observability
