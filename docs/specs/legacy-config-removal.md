# Feature: Legacy Configuration System Removal

## Feature Description

Remove the legacy configuration system (`config/legacy.py`, `.env` files, and `AgentConfig` class) in favor of the modern Pydantic-based `AgentSettings` system with JSON file persistence. This implements the final phase (2.0.0) of the deprecation plan outlined in ADR-0020.

The feature will:
- **Remove 645 lines** of legacy configuration code (`config/legacy.py`)
- **Update 48 files** to use `AgentSettings` instead of `AgentConfig`
- **Maintain environment variable support** for CI/CD and Docker deployments
- **Preserve backward compatibility** through the configuration manager's `merge_with_env()` function
- **Complete the 2.0.0 breaking change** as planned in the deprecation timeline

## User Story

As a **developer maintaining the agent-base codebase**
I want to **remove the legacy configuration system**
So that **we have a single, well-tested configuration approach that reduces maintenance burden and improves type safety**

## Problem Statement

The codebase currently maintains two parallel configuration systems:

1. **Legacy System** (`config/legacy.py`, 645 lines):
   - Dataclass-based `AgentConfig`
   - Direct environment variable parsing
   - Used by 48 files (16 production, 32 tests)
   - Three factory methods: `from_env()`, `from_file()`, `from_combined()`

2. **New System** (`config/schema.py`, 435 lines):
   - Pydantic-based `AgentSettings` models
   - JSON file persistence with progressive disclosure
   - Better validation and type safety
   - Used by configuration management commands

This dual system creates:
- **Maintenance burden**: Duplicate validation logic
- **Confusion**: Two ways to accomplish the same thing
- **Risk**: Inconsistencies between systems
- **Technical debt**: ADR-0020 planned removal in 2.0.0

## Solution Statement

Execute Phase 4 of ADR-0020: Remove the legacy configuration system entirely and migrate all code to use `AgentSettings`. The solution ensures:

1. **Clean removal** of `config/legacy.py` and all references
2. **Consistent configuration loading** through `load_config()` function
3. **Preserved environment variable support** through existing `merge_with_env()` function
4. **Updated test patterns** to use `AgentSettings` fixtures
5. **Complete documentation** reflecting the single configuration approach

## Related Documentation

### Requirements
- [Configuration Design](../design/config.md) - Primary configuration documentation
- [Architecture](../design/architecture.md) - System architecture overview

### Architecture Decisions
- [ADR-0020: Legacy Config Deprecation Plan](../decisions/0020-legacy-config-deprecation-plan.md) - **Primary reference** for this removal
- [ADR-0001: Naming Conventions](../decisions/0001-module-and-package-naming-conventions.md) - Module naming patterns to follow

## Codebase Analysis Findings

### Architecture Patterns
- **Configuration Loading**: Primary entry points use `AgentConfig.from_combined()` pattern
- **Tool Initialization**: Tools receive config in `__init__` and extract needed attributes
- **Test Patterns**: Tests use direct instantiation with mock values
- **Environment Variables**: Still heavily used in CI/CD and must remain supported

### Naming Conventions
- Config classes: `AgentSettings` (Pydantic models)
- Config functions: `load_config()`, `save_config()`, `merge_with_env()`
- Test fixtures: `mock_<provider>_settings()` pattern

### Similar Implementations
The new configuration system (`config/schema.py`) is already implemented and working. This feature removes the old system and migrates code to use the new one exclusively.

### Integration Patterns
**Current Pattern (Legacy):**
```python
from agent.config import AgentConfig
config = AgentConfig.from_combined()
agent = Agent(config=config)
```

**Target Pattern (New):**
```python
from agent.config import load_config
settings = load_config()  # Handles file + env merge internally
agent = Agent(settings=settings)
```

## Archon Project

**Project ID**: `9ba97e0d-6f4c-49b2-867e-927bd485772c`

Tasks will be created during implementation phase.

## Relevant Files

### Files to Delete
- **src/agent/config/legacy.py** (645 lines) - Entire legacy config module

### Existing Files to Modify

#### High Complexity Changes (Core Infrastructure)
- **src/agent/agent.py** - Update `__init__` signature to accept `AgentSettings` instead of `AgentConfig`
- **src/agent/tools/toolset.py** - Update base class to use `AgentSettings` (affects all tools)

#### Medium Complexity Changes (Entry Points)
- **src/agent/cli/app.py** - Replace `AgentConfig.from_combined()` with `load_config()`
- **src/agent/cli/interactive.py** - Same as app.py
- **src/agent/cli/execution.py** - Same as app.py
- **src/agent/cli/session.py** - Same as app.py
- **src/agent/cli/health.py** - Same as app.py
- **src/agent/cli/utils.py** - Update config usage
- **src/agent/cli/config_commands.py** - Remove legacy references
- **src/agent/cli/skill_commands.py** - Update config usage

#### Medium Complexity Changes (Supporting Code)
- **src/agent/memory/manager.py** - Update to use `AgentSettings`
- **src/agent/memory/store.py** - Update to use `AgentSettings`
- **src/agent/memory/mem0_store.py** - Update to use `AgentSettings`
- **src/agent/memory/mem0_utils.py** - Update to use `AgentSettings`
- **src/agent/middleware.py** - Update trace logging setup

#### Low Complexity Changes (Tools)
- **src/agent/tools/hello.py** - Inherits from updated toolset
- **src/agent/tools/filesystem.py** - Inherits from updated toolset

#### Low Complexity Changes (Skills)
- **src/agent/skills/__init__.py** - Update config usage
- **src/agent/skills/loader.py** - Update config usage
- **src/agent/_bundled_skills/hello-extended/toolsets/hello.py** - Update config usage

#### Test Files (32 files - Complete Rewrite)
- **tests/fixtures/config.py** - **CRITICAL**: Complete rewrite of all fixtures
- **tests/unit/config/test_schema.py** - Already uses `AgentSettings`
- **tests/unit/config/test_manager.py** - Already uses `AgentSettings`
- **tests/unit/core/test_config.py** - Remove legacy tests, keep relevant ones
- **tests/unit/core/test_config_local.py** - Update to use `AgentSettings`
- **tests/unit/core/test_config_minimal.py** - Already uses `AgentSettings`
- **tests/unit/cli/test_*.py** (6 files) - Update config fixtures
- **tests/unit/memory/test_*.py** (8 files) - Update config fixtures
- **tests/unit/tools/test_*.py** (3 files) - Update config fixtures
- **tests/integration/config/test_config_integration.py** - Update tests
- **tests/integration/llm/test_*.py** (4 files) - Update config fixtures

#### Documentation Files (5 files)
- **README.md** - Remove any `.env` references, emphasize `settings.json`
- **CONTRIBUTING.md** - Update configuration instructions
- **docs/design/config.md** - Remove legacy system documentation
- **docs/decisions/0020-legacy-config-deprecation-plan.md** - Mark as "Implemented" in status
- **CHANGELOG.md** - Add 2.0.0 breaking change entry

## Implementation Plan

### Phase 1: Foundation (Preparation)
**Goal**: Ensure new configuration system is robust before removing legacy

1. **Verify New System Completeness**
   - Audit `AgentSettings` coverage of all legacy features
   - Ensure `merge_with_env()` handles all environment variables
   - Verify all providers work with new system

2. **Create Adapter Layer (if needed)**
   - Determine if `Agent` and tools can use `AgentSettings` directly
   - Or create lightweight adapter to convert `AgentSettings` to runtime config
   - Document chosen approach

3. **Update Test Infrastructure**
   - Rewrite `tests/fixtures/config.py` to use `AgentSettings`
   - Create comprehensive fixtures for all providers
   - Ensure fixtures support same patterns as legacy

### Phase 2: Core Implementation (Code Migration)
**Goal**: Migrate all production code from `AgentConfig` to `AgentSettings`

1. **Update Core Agent Class**
   - Change `Agent.__init__` signature: `settings: AgentSettings` instead of `config: AgentConfig`
   - Update internal attribute access patterns
   - Ensure backward compatibility during transition

2. **Update Tool Base Class**
   - Change `AgentToolset.__init__` signature to accept `AgentSettings`
   - Update attribute access patterns (e.g., `settings.providers.openai.api_key`)
   - Cascade changes to all tools (hello, filesystem, bundled skills)

3. **Update CLI Entry Points**
   - Replace `AgentConfig.from_combined()` with `load_config()`
   - Update all CLI modules: app, interactive, execution, session, health, utils
   - Ensure environment variables still override properly

4. **Update Memory System**
   - Update manager, store, mem0_store, mem0_utils to use `AgentSettings`
   - Update attribute access patterns

5. **Update Configuration Commands**
   - Remove legacy references from config_commands.py
   - Update skill_commands.py config usage

### Phase 3: Integration (Testing and Documentation)
**Goal**: Ensure complete functionality and update all documentation

1. **Update All Test Files (32 files)**
   - Replace `AgentConfig()` with `AgentSettings()` in all tests
   - Update mock patterns and fixtures
   - Remove legacy-specific tests
   - Ensure all tests pass

2. **Remove Legacy Module**
   - Delete `src/agent/config/legacy.py`
   - Update `src/agent/config/__init__.py` to remove `AgentConfig` export
   - Verify no broken imports

3. **Update Documentation**
   - Update README.md configuration section
   - Update CONTRIBUTING.md development setup
   - Update docs/design/config.md to remove legacy references
   - Mark ADR-0020 as "Implemented"
   - Add CHANGELOG.md entry for 2.0.0 breaking change

4. **Verify Environment Variable Support**
   - Test all environment variables still work
   - Test CI/CD use cases (env vars only, no settings.json)
   - Test hybrid mode (settings.json + env var overrides)
   - Document precedence clearly

## Step by Step Tasks

Execute tasks in order, top to bottom. Tasks will be created in Archon during implementation.

### Task 1: Analyze and Plan Adapter Approach
- **Description**: Determine how `Agent` and tools will consume `AgentSettings`
- **Decision Point**: Direct usage vs. lightweight adapter
- **Files to analyze**: `src/agent/agent.py`, `src/agent/tools/toolset.py`
- **Output**: Documented approach for attribute access patterns

### Task 2: Rewrite Test Fixtures
- **Description**: Complete rewrite of `tests/fixtures/config.py` to use `AgentSettings`
- **Files to modify**: `tests/fixtures/config.py`
- **Pattern**: Create fixtures like `mock_openai_settings()`, `mock_azure_settings()`, etc.
- **Validation**: Existing tests should run with new fixtures (may fail, but shouldn't error)

### Task 3: Update Agent Core Class
- **Description**: Change `Agent.__init__` to accept `AgentSettings` instead of `AgentConfig`
- **Files to modify**: `src/agent/agent.py`
- **Pattern**:
  ```python
  def __init__(self, settings: AgentSettings | None = None):
      self.settings = settings or load_config()
      # Update all config.* references to settings.*
  ```
- **Validation**: Agent instantiation works with new signature

### Task 4: Update Tool Base Class
- **Description**: Change `AgentToolset.__init__` to accept `AgentSettings`
- **Files to modify**: `src/agent/tools/toolset.py`
- **Pattern**: Update signature and attribute access
- **Validation**: Tools can be instantiated with new signature

### Task 5: Update Individual Tools
- **Description**: Update hello and filesystem tools to use `AgentSettings`
- **Files to modify**:
  - `src/agent/tools/hello.py`
  - `src/agent/tools/filesystem.py`
  - `src/agent/_bundled_skills/hello-extended/toolsets/hello.py`
- **Pattern**: Follow toolset.py patterns for attribute access
- **Validation**: Tools work correctly with new config

### Task 6: Update CLI Entry Points
- **Description**: Replace `AgentConfig.from_combined()` with `load_config()` in all CLI files
- **Files to modify**:
  - `src/agent/cli/app.py`
  - `src/agent/cli/interactive.py`
  - `src/agent/cli/execution.py`
  - `src/agent/cli/session.py`
  - `src/agent/cli/health.py`
  - `src/agent/cli/utils.py`
- **Pattern**:
  ```python
  from agent.config import load_config
  settings = load_config()  # Handles file + env merge
  agent = Agent(settings=settings)
  ```
- **Validation**: CLI commands work correctly

### Task 7: Update Memory System
- **Description**: Update all memory modules to use `AgentSettings`
- **Files to modify**:
  - `src/agent/memory/manager.py`
  - `src/agent/memory/store.py`
  - `src/agent/memory/mem0_store.py`
  - `src/agent/memory/mem0_utils.py`
- **Pattern**: Update attribute access patterns
- **Validation**: Memory system works correctly

### Task 8: Update Configuration Commands
- **Description**: Remove legacy references and update config usage
- **Files to modify**:
  - `src/agent/cli/config_commands.py`
  - `src/agent/cli/skill_commands.py`
- **Pattern**: Ensure only `AgentSettings` is referenced
- **Validation**: Config commands work correctly

### Task 9: Update Skills System
- **Description**: Update skills loader and initialization to use `AgentSettings`
- **Files to modify**:
  - `src/agent/skills/__init__.py`
  - `src/agent/skills/loader.py`
- **Pattern**: Update config usage
- **Validation**: Skills load correctly

### Task 10: Update Middleware
- **Description**: Update trace logging setup to use `AgentSettings`
- **Files to modify**: `src/agent/middleware.py`
- **Pattern**: Update attribute access
- **Validation**: Trace logging still works

### Task 11: Update All Unit Tests (Config)
- **Description**: Update config-specific unit tests
- **Files to modify**:
  - `tests/unit/core/test_config.py` - Remove legacy tests
  - `tests/unit/core/test_config_local.py` - Update to AgentSettings
- **Pattern**: Use new fixtures, remove `AgentConfig` references
- **Validation**: All config tests pass

### Task 12: Update All Unit Tests (CLI)
- **Description**: Update CLI unit tests (6 files)
- **Files to modify**: `tests/unit/cli/test_*.py`
- **Pattern**: Use new fixtures
- **Validation**: All CLI tests pass

### Task 13: Update All Unit Tests (Memory)
- **Description**: Update memory unit tests (8 files)
- **Files to modify**: `tests/unit/memory/test_*.py`
- **Pattern**: Use new fixtures
- **Validation**: All memory tests pass

### Task 14: Update All Unit Tests (Tools)
- **Description**: Update tool unit tests (3 files)
- **Files to modify**: `tests/unit/tools/test_*.py`
- **Pattern**: Use new fixtures
- **Validation**: All tool tests pass

### Task 15: Update Integration Tests
- **Description**: Update integration tests (5 files)
- **Files to modify**:
  - `tests/integration/config/test_config_integration.py`
  - `tests/integration/llm/test_*.py` (4 files)
- **Pattern**: Use new fixtures and patterns
- **Validation**: All integration tests pass

### Task 16: Remove Legacy Module
- **Description**: Delete legacy config module and update exports
- **Files to delete**: `src/agent/config/legacy.py`
- **Files to modify**: `src/agent/config/__init__.py`
- **Pattern**: Remove `AgentConfig` from exports, only export `AgentSettings`
- **Validation**: No broken imports, all tests pass

### Task 17: Update README.md
- **Description**: Remove `.env` references, emphasize `settings.json`
- **Files to modify**: `README.md`
- **Pattern**: Update configuration section to show only new system
- **Validation**: Documentation is accurate

### Task 18: Update CONTRIBUTING.md
- **Description**: Update development setup to use `AgentSettings`
- **Files to modify**: `CONTRIBUTING.md`
- **Pattern**: Update configuration instructions
- **Validation**: Developer setup instructions are accurate

### Task 19: Update Configuration Design Doc
- **Description**: Remove legacy system documentation
- **Files to modify**: `docs/design/config.md`
- **Pattern**: Remove all references to `.env` as primary method
- **Validation**: Documentation reflects single configuration approach

### Task 20: Mark ADR as Implemented
- **Description**: Update ADR-0020 status to "implemented"
- **Files to modify**: `docs/decisions/0020-legacy-config-deprecation-plan.md`
- **Pattern**: Change status from "proposed" to "implemented", add completion date
- **Validation**: ADR accurately reflects completion

### Task 21: Update CHANGELOG.md
- **Description**: Add 2.0.0 breaking change entry
- **Files to modify**: `CHANGELOG.md`
- **Pattern**: Document breaking change and migration path
- **Validation**: Users understand what changed

### Task 22: Run Full Test Suite
- **Description**: Execute all tests to ensure zero regressions
- **Validation Command**: `cd app/server && uv run pytest -v`
- **Expected**: All tests pass with new configuration system

### Task 23: Manual Testing - Environment Variables
- **Description**: Verify environment variables still work for all providers
- **Test Cases**:
  - CI/CD mode: Only env vars, no settings.json
  - Hybrid mode: settings.json + env var overrides
  - Verify precedence: CLI args > env vars > settings.json > defaults
- **Validation**: All environment variable use cases work

### Task 24: Manual Testing - CLI Commands
- **Description**: Test all CLI commands with new configuration
- **Commands to test**:
  - `agent config init`
  - `agent config show`
  - `agent --check`
  - `agent --provider openai`
  - `agent -p "Hello"`
- **Validation**: All commands work correctly

## Testing Strategy

### Unit Tests

#### Configuration Tests
- **File**: `tests/unit/config/test_schema.py` - Already tests `AgentSettings`
- **File**: `tests/unit/config/test_manager.py` - Already tests `load_config()` and `save_config()`
- **Coverage**: Ensure all environment variables are properly merged

#### Agent Tests
- **Test**: Agent initialization with `AgentSettings`
- **Test**: Agent attribute access patterns work correctly
- **Test**: Fallback to `load_config()` when no settings provided

#### Tool Tests
- **Test**: Tools receive `AgentSettings` correctly
- **Test**: Tools can access provider credentials
- **Test**: Filesystem tools read settings correctly

#### CLI Tests
- **Test**: CLI commands load config correctly
- **Test**: Provider override works
- **Test**: Model override works

#### Memory Tests
- **Test**: Memory system uses settings correctly
- **Test**: mem0 configuration works
- **Test**: In-memory configuration works

### Integration Tests

#### Full Stack Configuration Test
- **Test**: Agent runs end-to-end with `AgentSettings`
- **Test**: Environment variables override settings.json values
- **Test**: CLI arguments override both env vars and settings.json

#### Provider Tests
- **Test**: Each provider works with new configuration
- **Test**: Provider switching works
- **Test**: Invalid provider configuration fails gracefully

#### Backward Compatibility Tests
- **Test**: Environment variables still work without settings.json (CI/CD mode)
- **Test**: Hybrid mode works (settings.json + env var overrides)
- **Test**: All existing environment variables are supported

### Edge Cases

- **Missing settings.json**: Falls back to env vars and defaults
- **Corrupted settings.json**: Logs error and falls back gracefully
- **Missing environment variable**: Uses settings.json value or default
- **Invalid provider configuration**: Clear error message with resolution steps
- **Permission errors**: Graceful handling if can't read settings.json

### Migration Testing
- **Test**: Existing deployments using only env vars continue to work
- **Test**: Existing settings.json files continue to work
- **Test**: All environment variables documented in config.md work

## Acceptance Criteria

### Core Functionality
- [ ] Legacy config module (`config/legacy.py`) completely removed
- [ ] All 48 files updated to use `AgentSettings` instead of `AgentConfig`
- [ ] Agent initializes correctly with `AgentSettings`
- [ ] Tools receive and use `AgentSettings` correctly
- [ ] CLI commands work with new configuration system

### Environment Variable Support
- [ ] All documented environment variables still work
- [ ] CI/CD mode works (env vars only, no settings.json)
- [ ] Hybrid mode works (settings.json + env var overrides)
- [ ] Precedence order maintained: CLI args > env vars > settings.json > defaults

### Testing
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Test coverage >90% for modified code
- [ ] No regressions in existing functionality

### Documentation
- [ ] README.md updated to reflect single configuration approach
- [ ] CONTRIBUTING.md updated with new patterns
- [ ] docs/design/config.md cleaned of legacy references
- [ ] ADR-0020 marked as "implemented"
- [ ] CHANGELOG.md documents breaking change

### Quality
- [ ] No broken imports after legacy module removal
- [ ] All files follow project naming conventions
- [ ] Code is well-commented where patterns changed significantly
- [ ] Breaking changes are clearly documented

## Validation Commands

Execute every command to validate the feature works correctly with zero regressions.

```bash
# Full test suite
cd /Users/danielscholl/source/github/danielscholl/agent-base
uv run pytest -v

# Test specific modules
uv run pytest tests/unit/config/ -v
uv run pytest tests/unit/core/test_config.py -v
uv run pytest tests/unit/cli/ -v
uv run pytest tests/unit/memory/ -v
uv run pytest tests/unit/tools/ -v
uv run pytest tests/integration/ -v

# Test coverage
uv run pytest --cov=src/agent --cov-report=html

# Manual: Test environment variables (CI/CD mode)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-test123
export AGENT_MODEL=gpt-5-mini
agent --check
# Should work without settings.json

# Manual: Test hybrid mode
agent config init
# Set up OpenAI in settings.json
export AGENT_MODEL=gpt-4o
agent config show
# Should show env var override

# Manual: Test CLI overrides
agent --provider anthropic -p "Hello"
# Should use anthropic even if settings.json says openai

# Manual: Test settings.json only
unset LLM_PROVIDER
unset OPENAI_API_KEY
agent config show
agent --check
# Should work with only settings.json

# Manual: Test all CLI commands
agent config init
agent config show
agent --check
agent --provider local
agent -p "Test message"
agent  # Interactive mode

# Manual: Verify no AgentConfig references
grep -r "AgentConfig" src/agent/ --exclude-dir=__pycache__
# Should return no results (except comments explaining removal)

grep -r "from_env\|from_file\|from_combined" src/agent/
# Should return no results

# Manual: Verify AgentSettings usage
grep -r "AgentSettings" src/agent/ --exclude-dir=__pycache__
# Should show new usage throughout codebase

# Linting and formatting
uv run ruff check src/agent/
uv run ruff format src/agent/ --check
```

## Notes

### Configuration Loading Pattern

**Before (Legacy):**
```python
from agent.config import AgentConfig

# Three different loading methods
config = AgentConfig.from_env()           # Env vars only
config = AgentConfig.from_file(path)      # File only
config = AgentConfig.from_combined()      # File + env merge
```

**After (New):**
```python
from agent.config import load_config

# Single loading method (handles everything)
settings = load_config()  # File + env merge + defaults
```

### Attribute Access Patterns

**Before (Legacy):**
```python
config = AgentConfig.from_combined()
api_key = config.openai_api_key
model = config.openai_model
enabled = config.enable_otel
```

**After (New):**
```python
settings = load_config()
api_key = settings.providers.openai.api_key
model = settings.providers.openai.model
enabled = settings.telemetry.enabled
```

### Test Fixture Pattern

**Before (Legacy):**
```python
@pytest.fixture
def mock_openai_config():
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-5-mini"
    )
```

**After (New):**
```python
@pytest.fixture
def mock_openai_settings():
    settings = AgentSettings()
    settings.providers.enabled = ["openai"]
    settings.providers.openai.api_key = "test-key"
    settings.providers.openai.model = "gpt-5-mini"
    return settings
```

### Environment Variable Support Strategy

Environment variables remain fully supported through the `merge_with_env()` function in `config/manager.py`. This function:

1. Loads `settings.json` (if exists)
2. Reads all environment variables
3. Applies env var overrides to settings
4. Returns merged configuration

**Key environment variables that must continue to work:**
- `LLM_PROVIDER` - Provider selection
- `AGENT_MODEL` - Model override
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. - Provider credentials
- `AZURE_OPENAI_ENDPOINT`, `AZURE_PROJECT_ENDPOINT` - Azure endpoints
- `MEMORY_TYPE`, `MEMORY_ENABLED` - Memory configuration
- `ENABLE_OTEL`, `OTLP_ENDPOINT` - Observability settings
- `AGENT_DATA_DIR`, `LOG_LEVEL` - Agent settings

### Breaking Changes

**BREAKING CHANGE in 2.0.0:**

The `AgentConfig` class and `config/legacy.py` module have been removed. All code must now use `AgentSettings` and the `load_config()` function.

**Migration for users:**
- If using environment variables only: **No changes needed** - env vars still work
- If using settings.json: **No changes needed** - settings.json still works
- If importing `AgentConfig` in custom code: **Change to `AgentSettings`**

**Migration for developers/contributors:**
- Replace `from agent.config import AgentConfig` with `from agent.config import AgentSettings, load_config`
- Replace `AgentConfig.from_combined()` with `load_config()`
- Update attribute access: `config.openai_api_key` → `settings.providers.openai.api_key`
- Update test fixtures to use `AgentSettings` instead of `AgentConfig`

### Files Impact Summary

**Total files affected: 53**

- **Deleted**: 1 file (legacy.py)
- **High complexity**: 2 files (agent.py, toolset.py)
- **Medium complexity**: 13 files (CLI, memory, config commands)
- **Low complexity**: 5 files (individual tools, skills)
- **Test files**: 32 files (fixtures, unit tests, integration tests)
- **Documentation**: 5 files (README, CONTRIBUTING, config.md, ADR-0020, CHANGELOG)

### Risk Mitigation

**Risks:**
1. Breaking existing deployments that directly import `AgentConfig`
2. Missing environment variable edge cases
3. Test coverage gaps

**Mitigation:**
1. Comprehensive testing of all configuration loading paths
2. Explicit testing of all documented environment variables
3. Documentation clearly explains breaking changes and migration path
4. CHANGELOG.md entry for 2.0.0 breaking change

### Implementation Sequence

**Critical Path:**
1. Update test fixtures (Task 2) - Must be first to enable test-driven development
2. Update Agent core (Task 3) - Central to all other changes
3. Update tool base class (Task 4) - Affects all tools
4. Update CLI entry points (Task 6) - How users interact with system
5. Update all tests (Tasks 11-15) - Ensure everything works
6. Remove legacy module (Task 16) - Final cleanup

**Order matters**: Don't delete legacy.py until all code is migrated and all tests pass.

## Execution

This spec can be implemented using: `/sdlc:implement docs/specs/legacy-config-removal.md`

Or execute tasks manually in Archon by creating tasks from this specification.
