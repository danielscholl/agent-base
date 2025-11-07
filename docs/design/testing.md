# Testing and Validation Strategy

## Overview

This document defines the comprehensive testing and validation strategy for the Agent Template project. It covers:

1. **Test Types**: Unit, Integration, and Validation testing approaches
2. **Code Quality Validation**: Linting, formatting, and type checking
3. **Coverage Strategy**: Targets and exclusions
4. **Test Organization**: File structure and naming conventions
5. **Validation Commands**: How to run each type of validation
6. **Test Selection Guide**: When to use each test type

**Related**: See [ADR-0008](../decisions/0008-testing-strategy-and-coverage-targets.md) for architectural decisions and rationale.

## Three-Tier Testing Approach

### Test Pyramid

```
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
```

### 1. Unit Tests

**Purpose**: Verify business logic in complete isolation

**Characteristics**:
- Test individual functions/classes
- Mock all dependencies (LLM, I/O, external services)
- Fast execution (no I/O, no subprocess)
- Deterministic (same input = same output)
- High test count (92 tests in this project)

**Location**: `tests/unit/`

**Coverage Target**: 100% of business logic

**Example**:
```python
def test_config_from_env_openai():
    """Test configuration loads OpenAI settings from environment."""
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-key",
        "OPENAI_MODEL": "gpt-4"
    }):
        config = AgentConfig.from_env()
        assert config.provider == "openai"
        assert config.openai_api_key == "test-key"
        assert config.openai_model == "gpt-4"
```

**When to Use**:
- Testing pure functions
- Testing business logic
- Testing error handling paths
- Testing edge cases and boundary conditions
- Need fast feedback loop

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
```python
@pytest.mark.asyncio
async def test_agent_with_hello_tools():
    """Test agent can use hello tools via mock LLM."""
    config = AgentConfig(provider="openai", openai_api_key="test")
    tools = HelloTools(config)

    with patch("agent.agent.create_openai_client") as mock_create:
        mock_client = MockChatClient()
        mock_create.return_value = mock_client

        agent = Agent(config=config, toolsets=[tools])

        # Verify tools are registered
        assert len(agent.tools) == 2
        assert any("hello_world" in str(t) for t in agent.tools)
```

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
- `tests/integration/agent_validation.yaml` - Basic test configuration
- `tests/integration/agent_validation_advanced.yaml` - Advanced scenarios

**See**: [Agent Validation Testing](#agent-validation-testing) section for details

### 3. Code Quality Validation

**Note**: In this project, "validation" has two meanings:
1. **Agent Validation Tests** - Integration tests via subprocess (covered above)
2. **Code Quality Validation** - Linting, formatting, type checking (covered below)

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
│   ├── test_hello_integration.py   # Traditional integration tests
│   ├── agent_validation.yaml       # Basic validation test config
│   └── agent_validation_advanced.yaml  # Advanced scenarios and edge cases
├── unit/                            # Unit tests
└── mocks/                           # Test mocks
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
uv run python tests/integration/run_validation.py

# Use custom config
uv run python tests/integration/run_validation.py --config tests/integration/agent_validation_advanced.yaml

# Run specific category
uv run python tests/integration/run_validation.py --category command_tests

# JSON output (for CI)
uv run python tests/integration/run_validation.py --json

# Verbose output
uv run python tests/integration/run_validation.py --verbose
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
    uv run python tests/integration/run_validation.py --json > results.json

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
uv run python tests/integration/run_validation.py --verbose

# Test individual commands manually
uv run agent --help
echo $?  # Check exit code

# Verify YAML config is valid
python -c "import yaml; print(yaml.safe_load(open('tests/agent_validation.yaml')))"
```

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
uv run python tests/integration/run_validation.py

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
| `uv run python tests/integration/run_validation.py` | All validation tests | Before release |
| `uv run python tests/integration/run_validation.py --verbose` | Detailed output | For debugging |
| `uv run python tests/integration/run_validation.py --json` | JSON output | For CI/CD integration |
| `uv run python tests/integration/run_validation.py --category command_tests` | Specific category | To test specific area |
| `uv run python tests/integration/run_validation.py --config custom.yaml` | Custom config | For custom test suites |
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
uv run python tests/integration/run_validation.py --category command_tests
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
uv run python tests/integration/run_validation.py --verbose

# Test commands manually
uv run agent --help
echo $?  # Check exit code

# Verify config file
python -c "import yaml; print(yaml.safe_load(open('tests/agent_validation.yaml')))"
```

## Summary

This testing strategy provides comprehensive coverage through:

1. **Unit Tests** - Fast, isolated testing of business logic (85%+ coverage target)
2. **Integration Tests** - Component interaction validation (mocked LLM)
3. **Agent Validation Tests** - Real-world CLI behavior testing (subprocess)
4. **Code Quality Validation** - Formatting, linting, and type checking

All tests must pass and code quality checks must succeed before merging code. Use the test selection guide to choose the appropriate test type for your changes.
