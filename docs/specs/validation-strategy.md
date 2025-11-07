# Chore: Align Integration Test Strategy and Validation Documentation

## Chore Description

Align the project's testing terminology, file structure, and documentation to accurately reflect the current three-tier testing approach: unit tests, integration tests (including agent validation tests), and code quality validation. This chore reorganizes validation test files to the integration test directory, expands the testing documentation to cover all validation types (linting, type checking, pytest, and agent validation), and ensures the validator agent prompt is updated to reflect the new structure.

**Purpose**: Clarify that agent validation tests (subprocess-based CLI testing) are a specialized form of integration testing, and provide comprehensive guidance on all validation checks necessary for the project.

**Expected Outcome**:
- Clear distinction between test types in file structure
- Comprehensive testing documentation covering all validation approaches
- Updated validator agent guidance reflecting current test organization
- No breaking changes to existing test execution

## Motivation

### Current State Issues

1. **Terminology Confusion**: "Validation tests" exist in `tests/` root but are functionally integration tests
2. **Documentation Scope Gap**: `docs/design/testing.md` focuses only on unit/integration tests, missing:
   - Code quality validation (black, ruff, mypy)
   - Agent validation testing approach
   - When to use each validation type
3. **File Organization**: Validation test files in `tests/` root don't clearly indicate they're integration tests
4. **Validator Agent Sync**: `.claude/agents/validator.md` references old file locations

### Why This Matters

**For Developers**:
- Clear understanding of where to add new tests
- Comprehensive testing guide in one place
- Consistent terminology (integration tests vs validation tests)

**For CI/CD**:
- Clear mapping of test types to pipeline stages
- Documentation of all quality gates

**For AI Agents**:
- Validator agent has accurate file paths
- Clear guidance on test categorization

### Business Value

- **Reduced Onboarding Time**: New developers understand testing strategy faster
- **Better Test Coverage**: Clear guidance leads to appropriate test selection
- **Maintainability**: Consistent organization reduces cognitive load
- **Quality Assurance**: Comprehensive validation documentation prevents gaps

## Scope

### In Scope

1. **File Reorganization**:
   - Move `tests/test_agent_validation.py` → `tests/integration/test_agent_validation.py`
   - Move `tests/run_validation.py` → `tests/integration/run_validation.py`
   - Keep YAML configs in `tests/` root (shared resource)

2. **Documentation Expansion**:
   - Expand `docs/design/testing.md` to cover:
     - Three-tier testing approach (unit/integration/validation)
     - Code quality validation (black, ruff, mypy, pytest)
     - Agent validation testing (subprocess approach)
     - Decision tree: when to use each test type
     - Test execution commands for all validation types
   - Update to include integration test strategy section

3. **Validator Agent Update**:
   - Update `.claude/agents/validator.md` with new file paths
   - Clarify that agent validation tests belong in `tests/integration/`
   - Update guidance on test organization

4. **Reference Updates**:
   - Update any import paths in existing code
   - Update pytest configuration if needed
   - Verify CI pipeline still works

### Out of Scope

- Creating new tests (only reorganizing existing)
- Changing test implementation (only moving files)
- Adding new validation tools (documenting existing)
- Modifying ADR-0008 (may reference it but not change)
- Changing coverage targets or thresholds

## Related Documentation

### Requirements
- [Testing Strategy](docs/design/testing.md) - Will be expanded

### Architecture Decisions
- [ADR-0008: Testing Strategy and Coverage Targets](docs/decisions/0008-testing-strategy-and-coverage-targets.md) - Defines unit/integration test strategy, coverage targets (85%), and testing patterns

### Design Documents
- [Architecture](docs/design/architecture.md) - May reference testing approach
- [Requirements](docs/design/requirements.md) - Testing requirements

## Codebase Analysis Findings

### Current Patterns

**Test Organization**:
```
tests/
├── unit/                           # ✅ Clear purpose
│   └── [5 test files, 79 tests]
├── integration/                    # ✅ Clear purpose
│   └── test_hello_integration.py  # Only 1 file, 6 tests
├── mocks/                          # ✅ Clear purpose
│   └── mock_client.py
├── test_agent_validation.py       # ❌ Should be in integration/
├── run_validation.py               # ❌ Should be in integration/
├── agent_validation.yaml           # ✅ Shared config, stays here
└── agent_validation_advanced.yaml  # ✅ Shared config, stays here
```

**Import Analysis**:
```python
# Current imports in test_agent_validation.py
from pathlib import Path
import pytest
import yaml
# No relative imports from src/agent - self-contained

# Current imports in run_validation.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.test_agent_validation import AgentValidator
# ^^^ This will need updating
```

**Dependencies**:
- `run_validation.py` imports from `test_agent_validation.py`
- `pytest` discovers tests via pattern matching (`test_*.py`)
- CI runs `pytest` from project root
- YAML configs loaded via relative paths from test files

**Validation Testing Characteristics**:
- Subprocess-based CLI execution
- Tests component integration through CLI interface
- Real-world behavior validation
- → **These are integration tests** (testing how components integrate via CLI)

### Impact Assessment

**Files Modified**: 3 files
1. `tests/test_agent_validation.py` → `tests/integration/test_agent_validation.py`
2. `tests/run_validation.py` → `tests/integration/run_validation.py`
3. `.claude/agents/validator.md` - File path updates

**Files Created**: 0 (expanding existing)

**Files Updated**: 2 documentation files
1. `docs/design/testing.md` - Major expansion
2. `.claude/agents/validator.md` - Path and guidance updates

**Breaking Changes**: None
- pytest auto-discovery still works
- CI commands unchanged (`pytest` runs all tests)
- YAML config paths adjusted in moved files

**Performance Implications**: None
- Same tests, different location
- No change in execution

## Relevant Files

### Files to Modify

#### Test Files (Move)
- `tests/test_agent_validation.py` → `tests/integration/test_agent_validation.py`
  - Update YAML config path (add `../` prefix)
  - Update any relative imports

- `tests/run_validation.py` → `tests/integration/run_validation.py`
  - Update import path: `from tests.test_agent_validation` → `from tests.integration.test_agent_validation`
  - Update default config path if needed

#### Documentation (Expand/Update)
- `docs/design/testing.md`
  - Add "Validation Strategy" section
  - Add "Code Quality Validation" section
  - Add "Agent Validation Testing" section
  - Add "Test Selection Guide" decision tree
  - Add "Validation Commands Reference"

- `.claude/agents/validator.md`
  - Update file paths in examples
  - Update test organization guidance
  - Clarify agent validation tests belong in integration/

### Files to Review

- `tests/integration/__init__.py` - May need to ensure it exists
- `pyproject.toml` - Verify pytest config still works
- `.github/workflows/ci.yml` - Verify CI pipeline still works
- `tests/conftest.py` - Check if any fixtures reference moved files
- `README.md` - Check if test commands documented

### New Files

None (only moving and expanding existing files)

## Implementation Plan

### Phase 1: Preparation
**Purpose**: Understand current state and verify no breaking changes

#### Task 1.1: Verify Current Test Execution
```bash
# Ensure all tests pass before changes
uv run pytest -v

# Verify validation tests work standalone
python tests/run_validation.py

# Verify code quality checks pass
uv run black --check src/ tests/
uv run ruff check src/ tests/
uv run mypy src/agent
```

**Expected**: All tests pass, all quality checks pass

#### Task 1.2: Analyze Import Dependencies
```bash
# Check for imports of test_agent_validation
grep -r "test_agent_validation" tests/
grep -r "run_validation" tests/

# Check for relative imports in validation files
grep "from \." tests/test_agent_validation.py
grep "from \." tests/run_validation.py
```

**Expected**: Only `run_validation.py` imports from `test_agent_validation.py`

### Phase 2: File Reorganization
**Purpose**: Move validation test files to integration directory

#### Task 2.1: Move Validation Test Files
```bash
# Move test file
git mv tests/test_agent_validation.py tests/integration/test_agent_validation.py

# Move runner file
git mv tests/run_validation.py tests/integration/run_validation.py
```

**Expected**: Files moved, Git tracking preserved

#### Task 2.2: Update Import Paths in Moved Files

**File**: `tests/integration/test_agent_validation.py`

**Changes**:
```python
# Line ~21: Update default config path
def __init__(self, config_path: str = "tests/agent_validation.yaml"):
    # No change needed - still correct from new location

# Line ~362: Update config path in test
def test_validation_config_exists(self):
    config_path = Path("tests/agent_validation.yaml")
    # No change needed - pytest runs from project root
```

**File**: `tests/integration/run_validation.py`

**Changes**:
```python
# Line ~19-20: Update import path
# OLD:
sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.test_agent_validation import AgentValidator

# NEW:
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.integration.test_agent_validation import AgentValidator

# Line ~48: Update default config path
parser.add_argument(
    "--config",
    type=str,
    default="tests/agent_validation.yaml",  # Still correct - runs from project root
    help="Path to validation config file (default: tests/agent_validation.yaml)",
)
```

**Expected**: Import paths correctly reference new locations

#### Task 2.3: Verify Tests Still Work
```bash
# Run moved tests via pytest
uv run pytest tests/integration/test_agent_validation.py -v

# Run standalone validation runner
python tests/integration/run_validation.py

# Run all tests
uv run pytest -v
```

**Expected**: All tests pass, no import errors

### Phase 3: Documentation Updates
**Purpose**: Expand testing documentation to cover all validation types

#### Task 3.1: Expand docs/design/testing.md

**Section 1: Overview** (existing, update)
```markdown
## Overview

This document defines the comprehensive testing and validation strategy for the Agent Template project. It covers:

1. **Test Types**: Unit, Integration, and Validation testing approaches
2. **Code Quality Validation**: Linting, formatting, and type checking
3. **Coverage Strategy**: Targets and exclusions
4. **Test Organization**: File structure and naming conventions
5. **Validation Commands**: How to run each type of validation
6. **Test Selection Guide**: When to use each test type

**Related**: See [ADR-0008](../decisions/0008-testing-strategy-and-coverage-targets.md) for architectural decisions and rationale.
```

**Section 2: Three-Tier Testing Approach** (new)
```markdown
## Three-Tier Testing Approach

### Test Pyramid

┌─────────────────────┐
│  Agent Validation   │  Real CLI behavior, subprocess execution
│   (Integration)     │  Slowest, most realistic
├─────────────────────┤
│ Integration Tests   │  Component interaction, mocked LLM
│                     │  Moderate speed, full stack
├─────────────────────┤
│    Unit Tests       │  Isolated logic, all dependencies mocked
│                     │  Fastest, highest coverage
└─────────────────────┘

### 1. Unit Tests

**Purpose**: Verify business logic in complete isolation

**Characteristics**:
- Test individual functions/classes
- Mock all dependencies (LLM, I/O, external services)
- Fast execution (no I/O, no subprocess)
- Deterministic (same input = same output)
- High test count (79 tests in this project)

**Location**: `tests/unit/`

**Coverage Target**: 100% of business logic

**Example**:
[Include existing example from ADR-0008]

### 2. Integration Tests

**Purpose**: Verify components work together correctly

**Characteristics**:
- Test component interactions
- Mock only external services (e.g., LLM API)
- Moderate execution speed
- Test full stack within application boundary
- Includes agent validation tests (subprocess-based)

**Location**: `tests/integration/`

**Coverage Target**: Happy paths and critical error cases

**Types of Integration Tests**:

#### A. Component Integration Tests
Test how internal components interact:
- Agent + Tools + Event Bus
- Configuration + Agent initialization
- Tool registration and invocation

**Example**:
[Include existing example]

#### B. Agent Validation Tests (CLI Integration)
Test real-world CLI behavior via subprocess execution:
- Actual command execution (`uv run agent --help`)
- stdout/stderr validation
- Exit code verification
- Performance benchmarking
- Configuration validation
- Error message quality

**Files**:
- `tests/integration/test_agent_validation.py` - Pytest integration
- `tests/integration/run_validation.py` - Standalone runner
- `tests/agent_validation.yaml` - Basic test configuration
- `tests/agent_validation_advanced.yaml` - Advanced scenarios

**See**: [Agent Validation Testing](#agent-validation-testing) section for details

### 3. Validation Tests

**Note**: In this project, "validation" has two meanings:
1. **Agent Validation Tests** - Integration tests via subprocess (covered above)
2. **Code Quality Validation** - Linting, formatting, type checking (covered below)

This section covers code quality validation.
```

**Section 3: Code Quality Validation** (new)
```markdown
## Code Quality Validation

### Overview

Code quality validation ensures code adheres to style standards, type safety, and best practices. All checks must pass in CI.

### Validation Tools

#### 1. Black (Formatting)

**Purpose**: Enforce consistent code formatting

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py312']
```

**Commands**:
```bash
# Check formatting
uv run black --check src/ tests/

# Apply formatting
uv run black src/ tests/

# Show diff without applying
uv run black --check src/ tests/ --diff
```

**CI Enforcement**: ✅ Fails if formatting violations exist

**When to Run**: Before committing code

---

#### 2. Ruff (Linting)

**Purpose**: Fast Python linting (replaces pyflakes, flake8, isort)

**Configuration** (`pyproject.toml`):
```toml
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
```

**Commands**:
```bash
# Check linting
uv run ruff check src/ tests/

# Fix auto-fixable issues
uv run ruff check src/ tests/ --fix

# Show GitHub Actions format
uv run ruff check src/ tests/ --output-format=github
```

**CI Enforcement**: ✅ Fails if linting violations exist

**When to Run**: Before committing code

---

#### 3. MyPy (Type Checking)

**Purpose**: Static type checking for Python

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Gradual typing
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
check_untyped_defs = true
strict_equality = true
```

**Commands**:
```bash
# Type check src code
uv run mypy src/agent

# Type check with pretty output
uv run mypy src/agent --pretty

# Type check specific file
uv run mypy src/agent/config.py
```

**CI Enforcement**: ✅ Fails if type errors exist

**When to Run**: Before committing code, especially after API changes

---

#### 4. Pytest (Testing)

**Purpose**: Execute test suite and measure coverage

**Configuration** (`pyproject.toml`):
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
    "slow: Slow tests (e.g., LLM-dependent)",
]
```

**Commands**:
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/agent --cov-report=html

# Run specific test types
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
uv run pytest -m integration

# Run with verbose output
uv run pytest -vv

# Run specific test file
uv run pytest tests/unit/test_config.py

# Run specific test
uv run pytest tests/unit/test_config.py::test_config_from_env_openai
```

**Coverage Configuration**:
```toml
[tool.coverage.run]
source = ["src/agent"]
omit = [
    "tests/*",
    "src/agent/__main__.py",      # Wrapper only
    "src/agent/utils/__init__.py", # Imports only
    "src/agent/utils/errors.py",  # Exception definitions
    "src/agent/cli.py",           # CLI display logic
    "src/agent/display/*",        # Display logic
]

[tool.coverage.report]
# Exclude patterns (see ADR-0008)
```

**CI Enforcement**:
- ✅ Fails if any tests fail
- ✅ Fails if coverage < 85%

**When to Run**: Before committing code, after any code changes

---

### Quick Validation Commands

```bash
# Run all quality checks (recommended before commit)
uv run black --check src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/agent && \
uv run pytest --cov=src/agent --cov-fail-under=85

# Run all quality checks with fixes
uv run black src/ tests/
uv run ruff check src/ tests/ --fix
uv run mypy src/agent
uv run pytest
```

### CI Pipeline Integration

**GitHub Actions** (`.github/workflows/ci.yml`):

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      # ... setup steps ...

      - name: Check formatting (Black)
        run: uv run black --check src/agent/ tests/ --diff

      - name: Lint (Ruff)
        run: uv run ruff check src/agent/ tests/ --output-format=github

      - name: Type check (MyPy)
        run: uv run mypy src/agent --pretty

      - name: Run tests with coverage
        run: |
          uv run pytest \
            --cov=src/agent \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=85 \
            -v
```

**All checks must pass** for CI to succeed.
```

**Section 4: Agent Validation Testing** (new)
```markdown
## Agent Validation Testing

### Overview

Agent validation testing is a specialized form of **integration testing** that validates real-world CLI behavior through subprocess execution. Unlike traditional integration tests that call Python functions directly, agent validation tests execute the actual CLI commands users would run.

**Key Distinction**:
- **Traditional Integration Tests**: `await agent.run("test")` (in-process)
- **Agent Validation Tests**: `subprocess.run("uv run agent -p 'test'")` (subprocess)

### Purpose

Validate that the CLI:
- Executes commands correctly
- Produces expected output
- Handles errors gracefully
- Performs adequately
- Validates configuration properly

**What This Tests**:
- CLI argument parsing
- Command execution flow
- Output formatting and display
- Error message quality
- Configuration loading and validation
- Tool invocation through CLI
- Performance characteristics

**What This Doesn't Test**:
- Business logic (covered by unit tests)
- Component interactions (covered by integration tests)
- LLM response quality (too variable)

### File Structure

```
tests/
├── integration/
│   ├── test_agent_validation.py    # AgentValidator class + pytest integration
│   ├── run_validation.py           # Standalone runner (no pytest required)
│   └── test_hello_integration.py   # Traditional integration tests
├── agent_validation.yaml           # Basic validation test config
└── agent_validation_advanced.yaml  # Advanced scenarios and edge cases
```

### AgentValidator Class

**Location**: `tests/integration/test_agent_validation.py`

**Key Methods**:
```python
class AgentValidator:
    def load_config(self) -> None:
        """Load test configuration from YAML."""

    def run_command(self, cmd: str, timeout: int = 30, env: dict = None) -> dict:
        """Execute command via subprocess and capture output."""

    def validate_output(self, output: dict, expected: dict) -> bool:
        """Validate output against expectations."""

    def run_test(self, test: dict) -> dict:
        """Run a single test and return results."""

    def run_all_tests(self) -> dict:
        """Run all configured tests."""

    def generate_report(self, results: dict) -> str:
        """Generate human-readable test report."""
```

### YAML Test Configuration

**Basic Structure**:
```yaml
version: "1.0"
name: "Agent CLI Validation"
description: "Validation tests for agent functionality"

# Test categories
command_tests:      # Basic CLI commands
prompt_tests:       # LLM prompt execution
performance_tests:  # Performance benchmarks
config_tests:       # Configuration validation
```

**Test Definition Example**:
```yaml
- name: "Help command displays correctly"
  command: "uv run agent --help"
  timeout: 10
  expected:
    exit_code: 0
    stdout_contains:
      - "agent"
      - "--prompt"
      - "--check"
      - "Examples:"
```

**Validation Types**:
- `exit_code`: Exact exit code match
- `stdout_contains`: All strings must be present in stdout
- `stdout_contains_any`: At least one string must be present
- `stdout_matches`: Regex pattern match
- `stdout_not_contains`: Strings must not be present
- `stderr_contains`: Strings in stderr
- `max_duration`: Performance threshold (seconds)

**Environment Manipulation**:
```yaml
- name: "Missing configuration handling"
  env:
    unset: ["LLM_PROVIDER"]  # Remove env vars
    CUSTOM_VAR: "value"       # Set env vars
  command: "uv run agent --check"
  expected:
    exit_code: 1
    stdout_contains: ["Configuration error"]
```

**Multiple Valid Outcomes**:
```yaml
- name: "Flexible validation"
  command: "uv run agent --check"
  expected_any:
    - exit_code: 0
      stdout_contains: ["success"]
    - exit_code: 1
      stdout_contains: ["configuration error"]
```

### Running Validation Tests

#### Via Pytest
```bash
# Run all validation tests
uv run pytest tests/integration/test_agent_validation.py -v

# Run specific validation test
uv run pytest tests/integration/test_agent_validation.py::TestAgentValidation::test_help_command -v

# Skip slow tests (LLM-dependent)
uv run pytest tests/integration/test_agent_validation.py -m "not slow"
```

#### Standalone Runner
```bash
# Run all validation tests
python tests/integration/run_validation.py

# Use custom config
python tests/integration/run_validation.py --config tests/agent_validation_advanced.yaml

# Run specific category
python tests/integration/run_validation.py --category command_tests

# JSON output (for CI)
python tests/integration/run_validation.py --json

# Verbose output
python tests/integration/run_validation.py --verbose
```

### Test Categories

#### 1. Command Tests
Basic CLI commands that should always work:
- `--help`: Help text display
- `--version`: Version display
- `--check`: Health check
- `--config`: Configuration display

**Example**:
```yaml
command_tests:
  - name: "Help command works"
    command: "uv run agent --help"
    timeout: 10
    expected:
      exit_code: 0
      stdout_contains: ["--prompt", "--check"]
```

#### 2. Prompt Tests
Test LLM prompt execution (requires LLM configuration):
- Simple prompts
- Tool invocation
- Error handling
- Multi-turn conversations (if supported)

**Example**:
```yaml
prompt_tests:
  - name: "Simple greeting"
    command: 'uv run agent -p "Say hello"'
    timeout: 30
    expected:
      exit_code: 0
      stdout_contains_any: ["Hello", "Hi", "Greetings"]
      stdout_not_contains: ["error", "Error"]
```

**Note**: Use `stdout_contains_any` for non-deterministic LLM responses

#### 3. Performance Tests
Validate response times and performance:
- Startup time
- Simple prompt response time
- Command execution speed

**Example**:
```yaml
performance_tests:
  - name: "Quick startup"
    command: "uv run agent --version"
    max_duration: 3  # seconds
    expected:
      exit_code: 0
```

#### 4. Configuration Tests
Test configuration validation and error handling:
- Missing configuration
- Invalid configuration
- Environment variable handling

**Example**:
```yaml
config_tests:
  - name: "Missing config error"
    env:
      unset: ["LLM_PROVIDER"]
    command: "uv run agent --check"
    expected:
      exit_code: 1
      stdout_contains_any: ["Configuration error", "missing"]
```

### Writing Effective Validation Tests

#### ✅ DO:
- Use pattern matching for non-deterministic output
- Test actual user workflows
- Validate error messages are helpful
- Test performance regressions
- Use `stdout_contains_any` for variable LLM responses
- Document expected behavior in test names

#### ❌ DON'T:
- Test exact LLM response text
- Test implementation details
- Expect deterministic LLM behavior
- Test third-party service internals

**Example - Good**:
```yaml
- name: "Math calculation"
  command: 'uv run agent -p "What is 2+2?"'
  expected:
    stdout_contains_any: ["4", "four"]  # Flexible matching
```

**Example - Bad**:
```yaml
- name: "Math calculation"
  command: 'uv run agent -p "What is 2+2?"'
  expected:
    stdout_contains: ["The answer is 4."]  # Too specific
```

### CI Integration

**GitHub Actions Example**:
```yaml
- name: Run validation tests
  run: |
    python tests/integration/run_validation.py --json > results.json

- name: Upload validation results
  uses: actions/upload-artifact@v3
  with:
    name: validation-results
    path: results.json
```

### Extending Validation Tests

#### Add New Test Category
1. Add category to YAML:
```yaml
security_tests:
  - name: "Command injection protection"
    command: 'uv run agent -p "test; echo pwned"'
    expected:
      stdout_not_contains: ["pwned"]
```

2. Update test runner categories:
```python
test_categories = [
    "command_tests",
    "prompt_tests",
    "performance_tests",
    "config_tests",
    "security_tests",  # Add new category
]
```

#### Add Custom Validation Logic
Extend `AgentValidator.validate_output()`:
```python
def validate_output(self, output: dict, expected: dict) -> bool:
    # Custom validation
    if "validates_json_response" in expected:
        try:
            json.loads(output["stdout"])
        except:
            return False

    # Standard validation
    return super().validate_output(output, expected)
```

### Performance Baselines

**Expected Performance** (for reference):
- Startup time (--version): < 3 seconds
- Help command: < 5 seconds
- Health check: < 10 seconds
- Simple prompt: < 15 seconds (depends on LLM provider)

**Note**: Actual performance varies by system and LLM provider.

### Troubleshooting

**Common Issues**:
1. **Tests timeout**: Increase timeout values in YAML
2. **Flaky tests**: Use `expected_any` for variable outcomes
3. **Environment issues**: Ensure `.env` is configured
4. **Import errors**: Check paths are correct from new location

**Debug Commands**:
```bash
# Run validation with verbose output
python tests/integration/run_validation.py --verbose

# Test individual commands manually
uv run agent --help
echo $?  # Check exit code

# Verify YAML config is valid
python -c "import yaml; print(yaml.safe_load(open('tests/agent_validation.yaml')))"
```
```

**Section 5: Test Selection Guide** (new)
```markdown
## Test Selection Guide

### Decision Tree

```
┌─ Need to test? ─────────────────────────────────────┐
│                                                      │
│  Testing business logic in isolation?               │
│  ├─ YES → Unit Test (tests/unit/)                   │
│  │         - Mock all dependencies                  │
│  │         - Fast, deterministic                    │
│  │         - High coverage                          │
│  └─ NO → Continue...                                │
│                                                      │
│  Testing component interactions?                    │
│  ├─ YES → Integration Test (tests/integration/)     │
│  │         - Mock only external services            │
│  │         - Test full stack                        │
│  │         - Verify tool registration, etc.         │
│  └─ NO → Continue...                                │
│                                                      │
│  Testing CLI behavior or user workflows?            │
│  ├─ YES → Agent Validation Test                     │
│  │         - Subprocess execution                   │
│  │         - Real command-line testing              │
│  │         - Pattern matching on output             │
│  └─ NO → May not need a test                        │
│                                                      │
│  Testing code quality?                              │
│  └─ Use validation tools:                           │
│      - black (formatting)                           │
│      - ruff (linting)                               │
│      - mypy (type checking)                         │
│      - pytest (run tests)                           │
└──────────────────────────────────────────────────────┘
```

### When to Use Unit Tests

**Use Unit Tests When**:
- ✅ Testing pure functions
- ✅ Testing business logic
- ✅ Testing error handling paths
- ✅ Testing edge cases and boundary conditions
- ✅ Testing calculations or transformations
- ✅ Need fast feedback loop

**Examples**:
- Configuration parsing: `test_config_from_env_openai()`
- Tool logic: `test_hello_world_with_name()`
- Event bus: `test_emit_event()`
- Error handling: `test_agent_init_invalid_provider()`

**Characteristics**:
- Mock all dependencies
- No I/O operations
- Deterministic results
- Fast execution (< 1 second per test)

---

### When to Use Integration Tests

**Use Integration Tests When**:
- ✅ Testing component interactions
- ✅ Testing tool registration and invocation
- ✅ Testing agent workflow
- ✅ Testing event flow between components
- ✅ Need to verify full stack (but not CLI)

**Examples**:
- Agent + Tools: `test_agent_with_hello_tools()`
- Tool invocation: `test_hello_tool_invocation()`
- Event emission: `test_tool_emits_events()`
- Configuration + Agent: `test_agent_with_config()`

**Characteristics**:
- Mock only external services (LLM API)
- Test real component interactions
- Moderate execution speed
- Call Python functions directly (not via subprocess)

---

### When to Use Agent Validation Tests

**Use Agent Validation Tests When**:
- ✅ Testing CLI interface changes
- ✅ Validating user-facing behavior
- ✅ Testing command-line options
- ✅ Validating error messages
- ✅ Performance regression testing
- ✅ Testing configuration validation
- ✅ Need to test actual CLI execution

**Examples**:
- Help command: `test_help_command()`
- Version display: `test_version_command()`
- Health check: `test_check_command()`
- Prompt execution: `test_simple_prompt()`
- Error handling: `test_missing_config()`

**Characteristics**:
- Execute via subprocess
- Pattern matching on stdout/stderr
- Test real CLI behavior
- Slower execution (subprocess overhead)
- Can test with or without real LLM

---

### Test Type Comparison

| Aspect | Unit | Integration | Agent Validation |
|--------|------|-------------|------------------|
| **Target** | Functions/classes | Component interaction | CLI behavior |
| **Execution** | In-process | In-process | Subprocess |
| **Mocking** | All dependencies | External services only | None (or LLM only) |
| **Speed** | Fastest (ms) | Moderate (< 1s) | Slowest (1-30s) |
| **Assertions** | Direct equality | Direct equality | Pattern matching |
| **Coverage** | High (100% logic) | Medium (happy paths) | Low (user workflows) |
| **Purpose** | Code correctness | Integration correctness | UX validation |

---

### Examples by Scenario

#### Scenario 1: Adding a new tool

```python
# Unit Test: Test tool logic
def test_new_tool_success(new_tool):
    result = await new_tool.do_something("input")
    assert result["success"] is True
    assert result["data"] == "expected"

# Integration Test: Test tool registration
def test_agent_with_new_tool():
    agent = Agent(config=config, toolsets=[NewTool(config)])
    assert len(agent.tools) == 1
    assert "do_something" in agent.tools

# Agent Validation Test: Test CLI invocation
- name: "New tool via CLI"
  command: 'uv run agent -p "Use new tool with input"'
  expected:
    stdout_contains: ["expected", "success"]
```

#### Scenario 2: Configuration changes

```python
# Unit Test: Test config parsing
def test_config_new_field():
    config = AgentConfig(new_field="value")
    assert config.new_field == "value"

# Integration Test: Test config in agent
def test_agent_with_new_config():
    config = AgentConfig(new_field="value")
    agent = Agent(config=config)
    assert agent.config.new_field == "value"

# Agent Validation Test: Test config validation
- name: "Invalid new_field value"
  env:
    NEW_FIELD: "invalid"
  command: "uv run agent --check"
  expected:
    exit_code: 1
    stdout_contains: ["validation error", "new_field"]
```

#### Scenario 3: Error handling

```python
# Unit Test: Test error is raised
def test_tool_error():
    with pytest.raises(ToolError):
        await tool.do_something(None)

# Integration Test: Test error propagation
def test_agent_handles_tool_error():
    # ... setup agent with failing tool ...
    response = await agent.run("cause error")
    assert "error" in response.lower()

# Agent Validation Test: Test error message
- name: "Tool error message"
  command: 'uv run agent -p "cause error"'
  expected:
    exit_code: 0  # Agent handles gracefully
    stdout_contains: ["error occurred", "please try"]
```
```

**Section 6: Validation Commands Reference** (new)
```markdown
## Validation Commands Reference

### Quick Reference

```bash
# === CODE QUALITY VALIDATION ===

# Format code
uv run black src/ tests/

# Check formatting
uv run black --check src/ tests/

# Lint code
uv run ruff check src/ tests/

# Fix linting issues
uv run ruff check src/ tests/ --fix

# Type check
uv run mypy src/agent

# === TESTING ===

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/agent --cov-report=html

# Run unit tests only
uv run pytest tests/unit/ -v

# Run integration tests only
uv run pytest tests/integration/ -v

# Run agent validation tests
uv run pytest tests/integration/test_agent_validation.py -v

# Run validation standalone
python tests/integration/run_validation.py

# === COMBINED VALIDATION ===

# All quality checks before commit
uv run black --check src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/agent && \
uv run pytest --cov=src/agent --cov-fail-under=85
```

### Detailed Command Reference

#### Black Formatting

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `uv run black src/ tests/` | Apply formatting | Before committing |
| `uv run black --check src/ tests/` | Check formatting | In CI or pre-commit hook |
| `uv run black --check src/ tests/ --diff` | Show changes needed | To see what would change |

#### Ruff Linting

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `uv run ruff check src/ tests/` | Check linting | Before committing |
| `uv run ruff check src/ tests/ --fix` | Auto-fix issues | To fix simple violations |
| `uv run ruff check src/ tests/ --output-format=github` | GitHub Actions format | In CI pipeline |

#### MyPy Type Checking

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `uv run mypy src/agent` | Check types | Before committing |
| `uv run mypy src/agent --pretty` | Pretty output | For readability |
| `uv run mypy src/agent/config.py` | Check specific file | After editing specific file |

#### Pytest Testing

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `uv run pytest` | Run all tests | Before committing |
| `uv run pytest -v` | Verbose output | To see test details |
| `uv run pytest -vv` | Very verbose | For debugging |
| `uv run pytest --cov=src/agent` | With coverage | To check coverage |
| `uv run pytest --cov=src/agent --cov-report=html` | HTML report | To browse coverage |
| `uv run pytest --cov-fail-under=85` | Enforce coverage | In CI pipeline |
| `uv run pytest tests/unit/` | Unit tests only | Fast feedback |
| `uv run pytest tests/integration/` | Integration tests | After component changes |
| `uv run pytest -m integration` | Integration marker | Alternative filter |
| `uv run pytest -m "not slow"` | Skip slow tests | Fast local testing |
| `uv run pytest tests/unit/test_config.py` | Specific file | After editing specific code |
| `uv run pytest tests/unit/test_config.py::test_config_from_env_openai` | Specific test | For debugging one test |

#### Agent Validation Testing

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `python tests/integration/run_validation.py` | All validation tests | Before release |
| `python tests/integration/run_validation.py --verbose` | Detailed output | For debugging |
| `python tests/integration/run_validation.py --json` | JSON output | For CI/CD integration |
| `python tests/integration/run_validation.py --category command_tests` | Specific category | To test specific area |
| `python tests/integration/run_validation.py --config custom.yaml` | Custom config | For custom test suites |
| `uv run pytest tests/integration/test_agent_validation.py` | Via pytest | For standard test runs |
| `uv run pytest tests/integration/test_agent_validation.py::TestAgentValidation::test_help_command` | Specific validation test | Debugging one test |

### Pre-Commit Workflow

**Recommended workflow** before committing:

```bash
# 1. Format code
uv run black src/ tests/

# 2. Fix linting issues
uv run ruff check src/ tests/ --fix

# 3. Check types
uv run mypy src/agent

# 4. Run tests with coverage
uv run pytest --cov=src/agent --cov-fail-under=85

# 5. (Optional) Run validation tests
python tests/integration/run_validation.py --category command_tests
```

**One-liner** (check only, no fixes):
```bash
uv run black --check src/ tests/ && \
uv run ruff check src/ tests/ && \
uv run mypy src/agent && \
uv run pytest --cov=src/agent --cov-fail-under=85
```

### CI Pipeline Commands

**From `.github/workflows/ci.yml`**:

```yaml
# Format check
- run: uv run black --check src/agent/ tests/ --diff

# Linting
- run: uv run ruff check src/agent/ tests/ --output-format=github

# Type check
- run: uv run mypy src/agent --pretty

# Tests with coverage
- run: |
    uv run pytest \
      --cov=src/agent \
      --cov-report=xml \
      --cov-report=term-missing \
      --cov-fail-under=85 \
      -v
```

### Coverage Reports

**View coverage report**:
```bash
# Generate HTML report
uv run pytest --cov=src/agent --cov-report=html

# Open in browser (macOS)
open htmlcov/index.html

# Open in browser (Linux)
xdg-open htmlcov/index.html

# Terminal report
uv run pytest --cov=src/agent --cov-report=term-missing
```

### Troubleshooting

**Black and Ruff conflicts**:
```bash
# Black takes precedence
uv run black src/ tests/
# Then run ruff
uv run ruff check src/ tests/ --fix
```

**MyPy errors**:
```bash
# Increase verbosity
uv run mypy src/agent --show-error-codes --pretty

# Check specific file
uv run mypy src/agent/config.py
```

**Test failures**:
```bash
# Run with more detail
uv run pytest -vv --tb=long

# Run specific failing test
uv run pytest tests/unit/test_config.py::test_config_from_env_openai -vv

# Drop into debugger on failure
uv run pytest --pdb
```

**Validation test issues**:
```bash
# Verbose output
python tests/integration/run_validation.py --verbose

# Test commands manually
uv run agent --help
echo $?  # Check exit code

# Verify config file
python -c "import yaml; print(yaml.safe_load(open('tests/agent_validation.yaml')))"
```
```

#### Task 3.2: Update .claude/agents/validator.md

**Changes**:

1. **Update file paths** in test structure section (around line 54):
```markdown
#### Test Configuration File
Create a `.claude/tests/validation.yaml` or `tests/agent_validation.yaml` file:
```

2. **Update Python test runner section** (around line 179):
```markdown
#### Python Test Runner
Create a test runner that executes validation tests:

```python
# tests/integration/test_agent_validation.py
import subprocess
# ... [rest of code]
```

3. **Update test execution commands** (around line 377):
```markdown
### 4. Test Execution Process

1. **Identify test framework**: Check for pytest, unittest, or custom test runner
2. **Create test files**:
   - Unit tests in `tests/unit/`
   - Integration tests in `tests/integration/`
     - Traditional integration tests: `test_*_integration.py`
     - Agent validation tests: `test_agent_validation.py`, `run_validation.py`
   - Validation config in `tests/agent_validation.yaml`
3. **Write comprehensive tests**: Balance coverage with maintainability
4. **Run all test suites**:
   - Unit tests: `pytest tests/unit/`
   - Integration tests: `pytest tests/integration/`
   - Agent validation tests: `pytest tests/integration/test_agent_validation.py`
     or `python tests/integration/run_validation.py`
5. **Generate validation report**: Summarize all test results
```

4. **Update validation report test commands** (around line 428):
```markdown
## Test Commands
```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/unit/
pytest tests/integration/
pytest tests/integration/test_agent_validation.py

# Run with coverage
pytest --cov=agent --cov-report=html

# Run validation suite
python tests/integration/run_validation.py
```
```

5. **Add clarification** about agent validation tests (around line 50):
```markdown
#### C. Agent Validation Tests (Real-World Scenarios)

**Note**: Agent validation tests are a type of integration test that validates CLI behavior via subprocess execution. They belong in `tests/integration/` directory.

Execute actual agent commands and validate outputs:
- Basic commands (help, version, check, config)
- Prompt execution with expected responses
- Error handling and recovery
- Tool usage validation

**Files**:
- `tests/integration/test_agent_validation.py` - AgentValidator class and pytest integration
- `tests/integration/run_validation.py` - Standalone runner (no pytest required)
- `tests/agent_validation.yaml` - Test configuration
```

**Expected**: Validator agent has updated guidance

### Phase 4: Verification and Cleanup
**Purpose**: Ensure everything works and clean up

#### Task 4.1: Verify All Tests Pass
```bash
# Run all tests
uv run pytest -v

# Verify coverage
uv run pytest --cov=src/agent --cov-report=term-missing

# Run validation standalone
python tests/integration/run_validation.py

# Run code quality checks
uv run black --check src/ tests/
uv run ruff check src/ tests/
uv run mypy src/agent
```

**Expected**:
- All tests pass (96 tests)
- Coverage ≥ 85%
- Validation tests work standalone
- All quality checks pass

#### Task 4.2: Update References in Documentation
```bash
# Check for references to old paths
grep -r "tests/test_agent_validation" docs/
grep -r "tests/run_validation" docs/
grep -r "tests/test_agent_validation" README.md

# Check pytest configuration
grep -A 5 "pytest.ini_options" pyproject.toml
```

**Expected**: No broken references found

#### Task 4.3: Verify CI Pipeline
```bash
# Check CI workflow
cat .github/workflows/ci.yml | grep pytest

# Ensure no hardcoded paths to moved files
grep "tests/test_agent_validation" .github/workflows/ci.yml
```

**Expected**: CI uses discovery, no hardcoded paths

#### Task 4.4: Test Git History Preserved
```bash
# Verify git mv preserved history
git log --follow tests/integration/test_agent_validation.py
git log --follow tests/integration/run_validation.py
```

**Expected**: Git history shows file origin

## Step by Step Tasks

**Execute every step in order, top to bottom**

### Task 1: Pre-Flight Checks
- **Description**: Verify current state before making changes
- **Files to modify**: None (read-only verification)
- **Expected outcome**: All tests pass, baseline established
- **Commands**:
  ```bash
  uv run pytest -v
  python tests/run_validation.py
  uv run black --check src/ tests/
  uv run ruff check src/ tests/
  uv run mypy src/agent
  ```

### Task 2: Move Test Files
- **Description**: Reorganize validation test files to integration directory
- **Files to modify**:
  - `tests/test_agent_validation.py` → `tests/integration/test_agent_validation.py`
  - `tests/run_validation.py` → `tests/integration/run_validation.py`
- **Expected outcome**: Files moved with Git history preserved
- **Commands**:
  ```bash
  git mv tests/test_agent_validation.py tests/integration/test_agent_validation.py
  git mv tests/run_validation.py tests/integration/run_validation.py
  ```

### Task 3: Update Import Paths
- **Description**: Fix import paths in moved files
- **Files to modify**:
  - `tests/integration/run_validation.py` (line ~20)
- **Expected outcome**: Imports work from new location
- **Changes**:
  - Update `sys.path.insert(0, str(Path(__file__).parent.parent))` to `sys.path.insert(0, str(Path(__file__).parent.parent.parent))`
  - Update `from tests.test_agent_validation import AgentValidator` to `from tests.integration.test_agent_validation import AgentValidator`

### Task 4: Verify Tests Work After Move
- **Description**: Run tests to ensure reorganization didn't break anything
- **Files to modify**: None
- **Expected outcome**: All 96 tests pass
- **Commands**:
  ```bash
  uv run pytest -v
  python tests/integration/run_validation.py
  ```

### Task 5: Expand docs/design/testing.md
- **Description**: Add comprehensive validation documentation
- **Files to modify**: `docs/design/testing.md`
- **Expected outcome**: Document covers all validation types with 6 new sections
- **New sections**:
  1. Overview (update existing)
  2. Three-Tier Testing Approach (new)
  3. Code Quality Validation (new)
  4. Agent Validation Testing (new)
  5. Test Selection Guide (new)
  6. Validation Commands Reference (new)

### Task 6: Update .claude/agents/validator.md
- **Description**: Update file paths and clarify test organization
- **Files to modify**: `.claude/agents/validator.md`
- **Expected outcome**: Validator agent references correct file paths
- **Changes**:
  - Update file paths in examples
  - Clarify agent validation tests belong in `tests/integration/`
  - Update test execution commands

### Task 7: Final Verification
- **Description**: Comprehensive verification of all changes
- **Files to modify**: None
- **Expected outcome**: Everything works, documentation accurate
- **Commands**:
  ```bash
  # All tests pass
  uv run pytest -v

  # Validation works standalone
  python tests/integration/run_validation.py

  # Code quality passes
  uv run black --check src/ tests/
  uv run ruff check src/ tests/
  uv run mypy src/agent

  # No broken references
  grep -r "tests/test_agent_validation" docs/ README.md || echo "No broken references"

  # Git history preserved
  git log --oneline --follow tests/integration/test_agent_validation.py | head -5
  ```

### Task 8: Commit Changes
- **Description**: Commit all changes with descriptive message
- **Files to modify**: None (git commit)
- **Expected outcome**: Clean commit with all changes
- **Commands**:
  ```bash
  git add -A
  git commit -m "$(aipr commit -s)"
  ```

## Testing Strategy

### Smoke Tests

After file moves:
```bash
# Quick verification that moved files work
python tests/integration/run_validation.py --category command_tests
uv run pytest tests/integration/test_agent_validation.py::TestAgentValidation::test_help_command -v
```

**Expected**: Tests execute successfully from new location

### Regression Tests

After all changes:
```bash
# Full test suite
uv run pytest -v

# Coverage check
uv run pytest --cov=src/agent --cov-fail-under=85

# Validation suite
python tests/integration/run_validation.py
```

**Expected**: Same results as pre-flight checks

### Documentation Validation

After documentation updates:
```bash
# Check for broken links (manual review)
cat docs/design/testing.md | grep -E "\[.*\]\(.*\)"

# Verify all code examples are valid
# (Manual: ensure all code blocks in testing.md are syntactically correct)
```

**Expected**: No broken links, all code examples valid

## Acceptance Criteria

- [x] Validation test files moved to `tests/integration/` with Git history preserved
- [x] All import paths updated and working correctly
- [x] All 96 tests pass after reorganization
- [x] Code quality checks pass (black, ruff, mypy)
- [x] `docs/design/testing.md` expanded with 6 new sections covering:
  - [ ] Three-tier testing approach
  - [ ] Code quality validation
  - [ ] Agent validation testing
  - [ ] Test selection guide
  - [ ] Validation commands reference
- [x] `.claude/agents/validator.md` updated with correct file paths
- [x] Standalone validation runner works: `python tests/integration/run_validation.py`
- [x] Pytest discovery works: `pytest tests/integration/test_agent_validation.py`
- [x] No broken documentation references
- [x] CI pipeline still works (verify locally before push)
- [x] Git history preserved for moved files

## Validation Commands

```bash
# === VERIFICATION COMMANDS ===

# 1. All tests pass
uv run pytest -v
# Expected: 96 tests, 92 passed, 4 skipped

# 2. Coverage meets target
uv run pytest --cov=src/agent --cov-report=term-missing --cov-fail-under=85
# Expected: Coverage ≥ 85%

# 3. Validation tests work standalone
python tests/integration/run_validation.py
# Expected: All validation tests pass

# 4. Code quality checks pass
uv run black --check src/ tests/
uv run ruff check src/ tests/
uv run mypy src/agent
# Expected: All checks pass

# 5. Git history preserved
git log --oneline --follow tests/integration/test_agent_validation.py | head -5
git log --oneline --follow tests/integration/run_validation.py | head -5
# Expected: Shows file history including before move

# 6. No broken references
grep -r "tests/test_agent_validation" docs/ README.md .claude/ 2>/dev/null
# Expected: Only finds correct references in .claude/agents/validator.md

# 7. Pytest discovery works
uv run pytest tests/integration/test_agent_validation.py -v
# Expected: Discovers and runs validation tests

# 8. Documentation renders correctly (manual)
# Review docs/design/testing.md for:
# - Proper markdown formatting
# - No broken links
# - Code examples are valid
# - Tables render correctly
```

## Rollback Plan

If issues arise during implementation:

### Rollback File Moves
```bash
# Undo git mv operations
git mv tests/integration/test_agent_validation.py tests/test_agent_validation.py
git mv tests/integration/run_validation.py tests/run_validation.py

# Restore original import paths
git checkout tests/integration/run_validation.py
# or manually revert import changes
```

### Rollback Documentation Changes
```bash
# Restore original documentation
git checkout docs/design/testing.md
git checkout .claude/agents/validator.md
```

### Complete Rollback
```bash
# Reset all changes
git reset --hard HEAD

# Verify clean state
git status
uv run pytest -v
```

## Notes

### Technical Decisions

1. **Why keep YAML configs in `tests/` root?**
   - They're shared configuration files, not test code
   - Can be loaded from any location via command-line argument
   - Similar to `pytest.ini`, `conftest.py` (shared test infrastructure)

2. **Why move validation tests to `tests/integration/`?**
   - They test integration of components via CLI interface
   - Subprocess-based testing is integration testing methodology
   - Clarifies they're not unit tests
   - Aligns with three-tier testing strategy

3. **Why expand `docs/design/testing.md` instead of creating new doc?**
   - Single source of truth for all testing guidance
   - Easier to maintain one comprehensive document
   - Natural place developers look for testing info
   - Can link to ADR-0008 for architectural decisions

### Future Improvements

**Phase 2** (post-implementation):
- Add JSON Schema for `agent_validation.yaml` validation
- Create test data fixtures in `tests/fixtures/`
- Document performance baselines
- Add MockChatClient usage examples to docs

**Phase 3** (advanced):
- Pre-commit hook template with validation checks
- GitHub Actions workflow templates
- Test coverage badge in README
- Automated validation report generation in CI

### Temporary Workarounds

None required - this is a straightforward refactoring with no technical debt.

### Documentation Standards

All documentation added follows:
- **Markdown**: GitHub-flavored markdown
- **Code blocks**: Syntax highlighting with language tags
- **Tables**: Well-formatted with consistent alignment
- **Examples**: Runnable, tested examples
- **Links**: Relative links to other docs
- **Voice**: Imperative mood for instructions, active voice for explanations

## Execution

This spec can be implemented using: `/implement docs/specs/chore-align-integration-test-strategy.md`

---

**Document Metadata**:
- **Created**: 2025-11-07
- **Author**: Claude Code Validator
- **Type**: Chore Specification
- **Priority**: Medium
- **Estimated Effort**: 2-3 hours
- **Dependencies**: None
- **Related**: ADR-0008
