# Feature: Configurable System Prompt

## Feature Description

Implement a configurable system prompt architecture that allows agent instructions to be loaded from external files with placeholder replacement support. This feature will enable users to customize agent behavior by providing their own system prompts through environment variables, while maintaining a sensible default prompt packaged with the application.

The implementation follows the proven pattern from butler-agent, using `importlib.resources` for package resource loading and supporting dynamic placeholder replacement for runtime configuration values.

## User Story

As a **developer using agent-base**
I want to **customize the agent's system prompt via configuration**
So that **I can test different agent behaviors, personalities, and instruction sets without modifying code**

## Problem Statement

Currently, the agent's system instructions are hardcoded as a string literal in `src/agent/agent.py` (lines 190-198). This creates several limitations:

1. **No customization**: Users cannot modify agent behavior without editing source code
2. **Testing difficulty**: Experimenting with different prompts requires code changes and restarts
3. **Prompt versioning**: Cannot easily version or share prompt configurations
4. **Context limitation**: Cannot inject runtime configuration values into prompts
5. **Maintenance overhead**: Prompt changes require code commits rather than config updates

## Solution Statement

Implement a four-tiered system prompt loading mechanism:

1. **AGENT_SYSTEM_PROMPT env variable** (highest priority): Load from file specified in `AGENT_SYSTEM_PROMPT` environment variable
2. **User default** (~/.agent/system.md): Load from user's data directory if file exists
3. **Package default** (fallback): Load from `src/agent/prompts/system.md` using `importlib.resources`
4. **Hardcoded fallback** (safety): Use embedded string if all file loading fails

Support placeholder replacement to inject runtime configuration values (e.g., `{{DATA_DIR}}`, `{{MODEL}}`) into prompts, enabling dynamic contextualization.

This design provides:
- Explicit per-project overrides via env variable
- Convenient global customization via ~/.agent/system.md
- Sensible defaults for new users
- Graceful fallback for reliability

## Related Documentation

### Requirements
- [docs/design/architecture.md](../design/architecture.md) - Dependency injection and configuration patterns
- [docs/design/requirements.md](../design/requirements.md) - Base requirements for extensibility

### Architecture Decisions
- [ADR-0001](../decisions/0001-module-and-package-naming-conventions.md) - Module naming (prompts package)
- [ADR-0006](../decisions/0006-class-based-toolset-architecture.md) - Dependency injection pattern
- [ADR-0008](../decisions/0008-testing-strategy-and-coverage-targets.md) - Testing strategy

## Archon Project

**Project ID**: `5d926de6-0b5f-4d0f-86f9-76f7939fa7c9`

This feature is tracked in Archon for task management and progress tracking. Use `/implement docs/specs/configurable-system-prompt.md` to begin implementation with integrated task management.

## Codebase Analysis Findings

### Architecture Patterns
- **Dependency Injection**: Agent receives `AgentConfig` via constructor (src/agent/agent.py:30-37)
- **Class-based Configuration**: `@dataclass` with `from_env()` factory method (src/agent/config.py:10-104)
- **Lazy Initialization**: Agent created in `_create_agent()` method, allowing pre-configuration setup
- **Fallback Pattern**: Multiple fallback layers throughout codebase (e.g., memory, middleware)

### Naming Conventions
- Package: `agent.prompts` (snake_case)
- Module: `system.md` (markdown for human readability)
- Method: `_load_system_prompt()` (private method, snake_case)
- Config field: `system_prompt_file` (snake_case)
- Env var: `AGENT_SYSTEM_PROMPT` (UPPER_SNAKE_CASE with prefix)

### Similar Implementations
- **Butler-agent reference**: `ai-examples/butler-agent/src/agent/agent.py:140-168`
  - Uses `importlib.resources.files("agent.prompts")`
  - Implements placeholder replacement with `.replace()`
  - Provides fallback to hardcoded string
  - Logs loading success/failure

### Integration Patterns
- **Configuration flow**: `AgentConfig.from_env()` → `Agent.__init__()` → `Agent._create_agent()`
- **Testing pattern**: Mock config in fixtures, inject via constructor
- **Path handling**: Use `Path.expanduser()` for tilde expansion (config.py:91-92)

### External Library Usage
- `importlib.resources` (Python 3.9+ stdlib) for package resource loading
- `pathlib.Path` for cross-platform path handling
- `python-dotenv` for `.env` file loading

## Relevant Files

### Existing Files to Modify
- `src/agent/agent.py` - Add `_load_system_prompt()` method, update `_create_agent()`
- `src/agent/config.py` - Add `system_prompt_file` field and env loading
- `.env.example` - Document `AGENT_SYSTEM_PROMPT` environment variable
- `tests/fixtures/config.py` - Add fixture for custom prompt testing
- `tests/unit/core/test_agent.py` - Add tests for prompt loading

### New Files to Create
- `src/agent/prompts/__init__.py` - Package initialization
- `src/agent/prompts/system.md` - Default system prompt template
- `tests/unit/core/test_system_prompt.py` - Dedicated prompt loading tests

## Implementation Plan

### Phase 1: Foundation (Package Structure)
Set up the prompts package and default system prompt file before implementing the loading logic.

### Phase 2: Core Implementation (Configuration & Loading)
Implement configuration fields, environment variable loading, and the `_load_system_prompt()` method with placeholder replacement.

### Phase 3: Integration & Testing
Wire up the new loading mechanism, create comprehensive tests, and update documentation.

## Step by Step Tasks

### Task 1: Create Prompts Package Structure
- **Description**: Create the `src/agent/prompts/` package directory with `__init__.py` and `system.md` default prompt file
- **Files to modify**:
  - Create `src/agent/prompts/__init__.py`
  - Create `src/agent/prompts/system.md`
- **Details**:
  - `__init__.py` should be minimal (just docstring)
  - `system.md` should contain the current hardcoded instructions plus placeholders
  - Use markdown format for human readability
  - Include placeholders: `{{DATA_DIR}}`, `{{MODEL}}`, `{{SESSION_DIR}}`

### Task 2: Add Configuration Fields
- **Description**: Add `system_prompt_file` field to `AgentConfig` dataclass and load from environment
- **Files to modify**:
  - `src/agent/config.py` (add field at ~line 52, load in `from_env()` at ~line 103)
  - `.env.example` (document new environment variable)
- **Details**:
  - Add field: `system_prompt_file: str | None = None`
  - Load in `from_env()`: `system_prompt_file=os.getenv("AGENT_SYSTEM_PROMPT")`
  - Document in `.env.example` with usage examples
  - Add validation in `validate()` method to check file exists if specified

### Task 3: Implement `_load_system_prompt()` Method
- **Description**: Create method to load system prompt with three-tier fallback and placeholder replacement
- **Files to modify**:
  - `src/agent/agent.py` (add method before `_create_agent()` at ~line 183)
- **Details**:
  - Import `importlib.resources` at top of file
  - Implement three-tier loading: custom file → package default → hardcoded
  - Add placeholder replacement for config values
  - Include try/except with logging
  - Return string (instructions)

### Task 4: Update `_create_agent()` to Use Loaded Prompt
- **Description**: Replace hardcoded instructions string with call to `_load_system_prompt()`
- **Files to modify**:
  - `src/agent/agent.py` (modify `_create_agent()` at ~line 190)
- **Details**:
  - Replace `instructions = """..."""` with `instructions = self._load_system_prompt()`
  - Ensure method is called before `create_agent()`
  - No other changes needed in `_create_agent()`

### Task 5: Create Test Fixtures
- **Description**: Add fixtures for testing custom and default prompt loading
- **Files to modify**:
  - `tests/fixtures/config.py` (add `custom_prompt_config` fixture)
- **Details**:
  - Create fixture that generates temporary prompt file
  - Create fixture for config with custom prompt path
  - Ensure fixtures clean up after tests

### Task 6: Write Unit Tests for Prompt Loading
- **Description**: Create comprehensive tests for all three loading paths and placeholder replacement
- **Files to modify**:
  - Create `tests/unit/core/test_system_prompt.py`
- **Details**:
  - Test default prompt loading from package
  - Test custom prompt loading from file
  - Test fallback to hardcoded on error
  - Test placeholder replacement
  - Test missing custom file raises appropriate error
  - Test non-existent placeholders are left unchanged

### Task 7: Write Integration Tests
- **Description**: Test end-to-end agent creation with different prompt configurations
- **Files to modify**:
  - `tests/unit/core/test_agent.py` (add tests)
- **Details**:
  - Test agent creation with default prompt
  - Test agent creation with custom prompt file
  - Test instructions appear in created agent
  - Test placeholders are replaced correctly
  - Use `mock_chat_client` to verify instructions

### Task 8: Update Documentation
- **Description**: Document the new feature in README and add usage examples
- **Files to modify**:
  - `README.md` (add section on custom prompts)
  - `docs/design/usage.md` (add examples)
- **Details**:
  - Add "Custom System Prompts" section to README
  - Include example prompt file
  - Document available placeholders
  - Show environment variable usage
  - Add troubleshooting section

## Testing Strategy

### Unit Tests

**Prompt Loading Tests** (`tests/unit/core/test_system_prompt.py`):
- `test_load_default_prompt_from_package()` - Verify default prompt loads from `prompts/system.md`
- `test_load_custom_prompt_from_file()` - Verify custom file path works
- `test_fallback_on_missing_custom_file()` - Verify fallback when custom file doesn't exist
- `test_fallback_on_corrupt_prompt_file()` - Verify fallback when file is unreadable
- `test_placeholder_replacement()` - Verify all placeholders are replaced
- `test_missing_placeholders_ignored()` - Verify unknown placeholders left unchanged
- `test_placeholder_values_from_config()` - Verify values come from config

**Configuration Tests** (`tests/unit/core/test_config.py`):
- `test_system_prompt_file_from_env()` - Verify env variable loading
- `test_system_prompt_file_defaults_to_none()` - Verify default when not set
- `test_system_prompt_file_path_expansion()` - Verify tilde expansion works

**Agent Creation Tests** (`tests/unit/core/test_agent.py`):
- `test_agent_uses_default_prompt()` - Verify agent gets default prompt
- `test_agent_uses_custom_prompt()` - Verify agent gets custom prompt
- `test_agent_instructions_have_placeholders_replaced()` - Verify replacements happen
- `test_agent_creation_succeeds_on_prompt_load_failure()` - Verify graceful fallback

### Integration Tests

**End-to-End Prompt Loading** (`tests/integration/test_prompt_loading.py`):
- `test_full_agent_workflow_with_custom_prompt()` - Complete flow from env var to agent
- `test_prompt_reload_on_agent_recreation()` - Verify prompts reload on new agent instances

### Edge Cases
- Empty prompt file (should use fallback)
- Prompt file with partial placeholders (should replace available ones)
- Prompt file with malformed encoding (should use fallback)
- Very large prompt file (>10KB) (should load successfully)
- Prompt file path with spaces/special characters (should handle correctly)
- Relative vs absolute paths in `AGENT_SYSTEM_PROMPT` (should expand correctly)
- Multiple agents with different configs (should each get correct prompt)

## Acceptance Criteria

- [ ] Default system prompt loads from `src/agent/prompts/system.md` when no custom file specified
- [ ] Custom system prompt loads from file path specified in `AGENT_SYSTEM_PROMPT` environment variable
- [ ] Hardcoded fallback activates when file loading fails (logged as warning)
- [ ] Placeholders `{{DATA_DIR}}`, `{{MODEL}}`, `{{SESSION_DIR}}` are replaced with config values
- [ ] Unknown placeholders are left unchanged in prompt
- [ ] Missing custom file logs error and uses fallback
- [ ] Environment variable supports both absolute and relative paths (with tilde expansion)
- [ ] All tests pass with 85%+ coverage maintained
- [ ] Documentation includes usage examples and available placeholders
- [ ] `.env.example` documents the new environment variable
- [ ] Existing agent behavior unchanged when no custom prompt configured
- [ ] Prompt loading is logged at INFO level for observability

## Validation Commands

```bash
# Run all tests
uv run pytest -m "not llm" -n auto

# Run specific test file
uv run pytest tests/unit/core/test_system_prompt.py -v

# Run agent tests to verify integration
uv run pytest tests/unit/core/test_agent.py -v

# Run with coverage check
uv run pytest --cov=src/agent --cov-fail-under=85

# Test with custom prompt
echo "AGENT_SYSTEM_PROMPT=~/my-prompt.md" >> .env
uv run agent -p "hello"

# Verify default prompt is used
unset AGENT_SYSTEM_PROMPT
uv run agent -p "hello"

# Type check
uv run mypy src/agent/

# Lint check
uv run ruff check src/agent/
```

## Notes

### Design Decisions

**Why `importlib.resources` over `__file__`?**
- Works correctly when package is installed (not just in development)
- Recommended approach for accessing package data in Python 3.9+
- Handles different installation methods (wheel, sdist, editable)
- Future-proof against packaging changes

**Why markdown for system prompt?**
- Human-readable and editable
- Supports documentation and comments
- Common format for prompt engineering
- Can be version-controlled with diffs
- Syntax highlighting in editors

**Why three-tier fallback?**
- Flexibility: Users can override via env var
- Robustness: Package default ensures working state
- Safety: Hardcoded fallback prevents agent creation failure
- Observability: Each tier logged for debugging

**Why simple string replacement for placeholders?**
- Sufficient for current use case (small number of simple values)
- No external template library dependency
- Easy to understand and maintain
- Fast execution (no parsing overhead)
- Can upgrade to Jinja2/template engine later if needed

### Available Placeholders

The following placeholders will be supported in system prompts:

- `{{DATA_DIR}}` - Agent data directory path (from `config.agent_data_dir`)
- `{{SESSION_DIR}}` - Session storage directory (from `config.agent_session_dir`)
- `{{MODEL}}` - LLM model display name (from `config.get_model_display_name()`)
- `{{PROVIDER}}` - LLM provider name (from `config.llm_provider`)
- `{{MEMORY_ENABLED}}` - Whether memory is enabled (from `config.memory_enabled`)

Future enhancements could add:
- `{{TOOLS}}` - List of available tools
- `{{CAPABILITIES}}` - Agent capabilities description
- `{{VERSION}}` - Agent version number

### Example Custom Prompt File

```markdown
# Custom Agent Instructions

You are a specialized coding assistant for Python development.

## Configuration
- Data directory: {{DATA_DIR}}
- Model: {{MODEL}}
- Memory: {{MEMORY_ENABLED}}

## Your Expertise
- Python 3.12+ best practices
- Type hints and mypy compliance
- pytest testing strategies
- Async/await patterns

## Response Style
- Be concise and code-focused
- Provide working examples
- Explain complex patterns
- Reference Python documentation

## Tools Available
You have access to tools for task execution. Use them appropriately.
```

### Future Enhancements

1. **Prompt Templates Library**: Package multiple prompt templates for different use cases
2. **Hot Reload**: Detect prompt file changes and reload without restart
3. **Jinja2 Integration**: Support template logic (conditionals, loops)
4. **Prompt Validation**: Schema validation for required sections
5. **Prompt Composition**: Support multiple prompt files (base + overrides)
6. **Environment-Specific Prompts**: Different prompts for dev/staging/prod

### Migration Path

Existing deployments:
1. No changes required - default prompt maintains current behavior
2. Optional: Move hardcoded customizations to `prompts/system.md`
3. Optional: Override via `AGENT_SYSTEM_PROMPT` for testing

## Execution

This spec can be implemented using: `/implement docs/specs/configurable-system-prompt.md`
