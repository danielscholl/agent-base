# Agent Base - GitHub Copilot Instructions

This repository contains a production-ready conversational AI agent framework optimized for GitHub Copilot use.
The following guidelines ensure code quality, consistency, and efficiency in development practices.

## Project Overview

Agent Base is a production-ready conversational AI agent framework built with Python 3.12+. It provides multi-provider LLM support (OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry) with enterprise features including session management, memory, observability, and extensible toolsets.

**Key Technologies**:
* **Language**: Python 3.12+
* **Framework**: Microsoft Agent Framework
* **Package Manager**: uv (NOT pip)
* **Line Length**: 100 characters (Black enforced)
* **Test Coverage**: 85% minimum (enforced)

---

## Repository Structure

* **Important Branches**:
  * `main`: Protected production branch (semantic releases via release-please)
  * Feature branches: `feat/description`, `fix/description`, `chore/description`

* **Key Directories**:
  * `src/agent/`: Core framework code
  * `tests/`: Unit, integration, and validation tests
  * `docs/specs/`: Feature implementation specifications
  * `docs/decisions/`: Architecture Decision Records (ADRs)
  * `.github/workflows/`: CI/CD automation

---

## CRITICAL: Always Run Validation Checks

Before considering any code change complete, you MUST run these validation commands in order. These are not optional - they are enforced by CI and will cause PR failures if skipped.

### 1. Format Code (REQUIRED)
```bash
uv run black src/agent/ tests/
```

### 2. Lint and Auto-Fix (REQUIRED)
```bash
uv run ruff check --fix src/agent/ tests/
```

### 3. Type Check (REQUIRED)
```bash
uv run mypy src/agent/
```

### 4. Run Tests with Coverage (REQUIRED)
```bash
# Run all free tests (CI equivalent) - MUST pass
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# Should complete in ~4 seconds with ~220 tests passing
```

### Complete Validation Sequence
Run all checks together before committing:
```bash
uv run black src/agent/ tests/ && \
uv run ruff check --fix src/agent/ tests/ && \
uv run mypy src/agent/ && \
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85
```

**ALL CHECKS MUST PASS** before code is considered complete. Do not skip or ignore failures.

## Build and Run

```bash
# Install dependencies (use uv, not pip)
uv sync --all-extras

# Run agent interactively
uv run agent

# Verify configuration
uv run agent --check

# Run with observability
ENABLE_OTEL=true uv run agent
```

## Architecture Patterns (MUST FOLLOW)

### 1. Dependency Injection (No Global State)
**Always** use constructor injection for dependencies:
```python
class MyTool(AgentToolset):
    def __init__(self, config: AgentConfig):
        self.config = config  # Inject, never use globals
```

### 2. Structured Responses (REQUIRED Format)
All tools MUST return structured responses:
```python
# Success
return self._create_success_response(
    result=data,
    message="Operation completed"
)

# Error
return self._create_error_response(
    error="invalid_input",
    message="Input validation failed"
)
```

### 3. Type Hints (REQUIRED)
All public functions MUST have complete type hints:
```python
async def my_tool(
    self,
    input: Annotated[str, Field(description="User input")]
) -> dict:
    """Tool description for LLM.

    Args:
        input: Description of input parameter

    Returns:
        Structured response dict with success status
    """
    ...
```

### 4. Async First
All I/O operations MUST use async/await:
```python
async def my_function(self) -> dict:
    result = await some_async_call()
    return result
```

## Testing Requirements

### Test Organization
- **Unit Tests** (`tests/unit/`): Fast, isolated, mocked dependencies
- **Integration Tests** (`tests/integration/`): Component interaction, MockChatClient
- **Validation Tests** (`tests/validation/`): CLI subprocess tests
- **LLM Tests** (`tests/integration/llm/`): Real API calls (COSTS MONEY, opt-in only)

### Writing Tests
**Always** add appropriate markers:
```python
import pytest
from tests.helpers import assert_success_response

@pytest.mark.unit
@pytest.mark.tools
async def test_my_function(mock_config):
    tool = MyTool(mock_config)
    result = await tool.my_function("input")
    assert_success_response(result)
```

### Test Utilities
- `assert_success_response(result)` - Validate success format
- `assert_error_response(result, "error_code")` - Validate error format
- `mock_config` - Fixture for AgentConfig
- `mock_chat_client` - Fixture for mocked LLM
- `agent_instance` - Fixture for pre-configured Agent

### Coverage Requirements
- Minimum 85% coverage (enforced by CI)
- Use `uv run pytest --cov=src/agent --cov-report=html` to view report
- Excluded: CLI orchestration, display rendering, error definitions

## Naming Conventions

- **Modules**: `snake_case` (e.g., `memory_manager.py`)
- **Classes**: `PascalCase` (e.g., `MemoryManager`, `InMemoryStore`)
- **Functions**: `snake_case` (e.g., `save_memory_state`, `restore_memory`)
- **Private**: `_leading_underscore` (e.g., `_create_client`)
- **Line length**: 100 characters maximum

---

## Commit Standards

### Conventional Commit Format

Commits **must** follow the [Conventional Commits](https://www.conventionalcommits.org) standard:

```text
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

**Valid Types**:
* `feat`: New feature
* `fix`: Bug fix
* `docs`: Documentation only
* `test`: Tests only
* `refactor`: Code refactoring
* `chore`: Maintenance (dependencies, configs)
* `ci`: CI/CD configuration

**Valid Scopes**: `tools`, `agent`, `cli`, `memory`, `middleware`, `display`, `config`, `tests`

### Rules

* **MUST** use lowercase type with colon and space (`feat: add feature`)
* **MUST** use imperative mood ("add feature", not "added feature")
* **MUST NOT** use emojis, brackets, or special characters
* **MUST NOT** exceed 100 characters in subject line
* Breaking changes **MUST** include `BREAKING CHANGE:` in footer or use `!` after type

**PREFERRED**: Use aipr tool to generate commit messages:
```bash
git commit -m "$(aipr commit -s)"
```

**Examples**:
```bash
# CORRECT
feat(tools): add weather lookup capability
fix(agent): handle empty tool list gracefully
docs(architecture): add memory architecture ADR

# INCORRECT (do not use these formats)
[feat] add feature          # No brackets
Feat: Add Feature           # No capitalization
feat : add feature          # No space before colon
added feature               # Not imperative, no type
feat: ✨ add feature        # No emojis
```

---

## Branch Naming

Descriptive naming aligned to conventional commits:

```bash
feat/add-auth-middleware
fix/memory-leak-in-session
chore/update-dependencies
docs/improve-api-documentation
test/add-integration-tests
```

---

## Pull Request Workflow

* Create PRs using `gh pr create`
* PR title **must** follow conventional commit format
* PR body **must** use aipr tool: `gh pr create --body "$(aipr pr -s)"`
* Reference issues clearly (e.g., `Fixes #123`, `Closes #456`)
* Ensure all CI checks pass before requesting review
* All validation checks must pass (Black, Ruff, MyPy, PyTest with 85% coverage)

---

## Automation Workflows

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| `ci.yml` | Build, lint, type check, test with coverage | Push, PR |
| `security.yml` | CodeQL security scanning | Schedule, PR |
| `release.yml` | Automated semantic version releases | PR merge to main |

**CI Requirements** (all must pass):
* Black formatting check
* Ruff linting check
* MyPy type checking
* PyTest with 85%+ coverage (excluding LLM tests)

---

## Testing Standards

* **Test-Driven Development**: Write tests alongside code
* **Coverage Target**: 85%+ (enforced by CI)
* **Test Speed**: ~4 seconds for full suite (excluding LLM tests)
* **Mock Everything**: Never make real LLM calls in tests (except explicit `@pytest.mark.llm` tests)

**Local Test Commands**:
```bash
# Fast feedback loop
uv run pytest -m unit -n auto

# Full validation (CI equivalent)
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# View coverage report
uv run pytest --cov=src/agent --cov-report=html
open htmlcov/index.html
```

---

## Project Layout

```
src/agent/
├── agent.py              # Core Agent class (multi-provider LLM support)
├── config.py             # Multi-provider configuration
├── tools/
│   ├── toolset.py        # Base class (inherit from AgentToolset)
│   └── hello.py          # Example tool implementation
├── memory/               # ContextProvider-based memory
│   ├── manager.py        # Abstract MemoryManager interface
│   ├── store.py          # In-memory implementation
│   └── context_provider.py  # Framework integration
├── cli/                  # Interactive CLI (Typer + prompt_toolkit)
│   ├── app.py            # Main application
│   ├── commands.py       # Command handlers
│   └── session.py        # Session management
├── events.py             # Event bus pattern
├── middleware.py         # Tool execution middleware
├── display/              # Rich-based visualization
└── observability.py      # OpenTelemetry integration

tests/
├── unit/                 # Fast isolated tests (use mocks)
├── integration/          # Component interaction tests
├── validation/           # CLI subprocess tests
├── fixtures/             # Shared test fixtures
├── helpers/              # Test utilities (assert_success_response, etc.)
└── templates/            # Templates for new tests

docs/
├── design/               # Architecture and requirements
├── decisions/            # Architecture Decision Records (ADRs)
└── specs/                # Feature implementation specifications
```

## Common Errors and Solutions

### Error: "No module named 'agent'"
**Solution**: Always use `uv run` prefix for commands, not direct python:
```bash
# CORRECT
uv run pytest
uv run agent

# INCORRECT
pytest
python -m agent
```

### Error: Type checking failures
**Solution**: Ensure all public functions have complete type hints including return types:
```python
# CORRECT
async def my_function(self, input: str) -> dict:
    ...

# INCORRECT (missing return type)
async def my_function(self, input: str):
    ...
```

### Error: Test failures due to real LLM calls
**Solution**: Use MockChatClient for testing, never real LLM clients:
```python
# CORRECT - Testing with mock
from tests.mocks import MockChatClient
agent = Agent(config, chat_client=MockChatClient(response="test"))

# INCORRECT - Real LLM in tests
agent = Agent(config)  # Will make real API calls
```

### Error: Coverage below 85%
**Solution**: Add unit tests for new functionality. Check excluded files in pyproject.toml:
```bash
uv run pytest --cov=src/agent --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Code Quality Checklist

Before considering any code change complete, verify:

- [ ] All type hints present on public functions
- [ ] Docstrings for all public functions and classes
- [ ] Structured responses for all tool functions
- [ ] Dependencies injected via constructor (no globals)
- [ ] Async/await used for all I/O operations
- [ ] Tests written with appropriate markers
- [ ] `uv run black` passes (formatting)
- [ ] `uv run ruff check` passes (linting)
- [ ] `uv run mypy` passes (type checking)
- [ ] `uv run pytest -m "not llm" --cov --cov-fail-under=85` passes (tests + coverage)

## Additional Notes

- Use Microsoft Agent Framework patterns (ContextProvider, not middleware for memory)
- Follow event bus pattern for loose coupling (middleware emits, display subscribes)
- Never use global state - always dependency injection
- Security: Never log credentials, sanitize file paths, validate all inputs
- See docs/design/architecture.md for detailed architectural guidelines
- See docs/decisions/ for Architecture Decision Records (ADRs)
- Reference CONTRIBUTING.md for complete development workflow

## Documentation

- README.md - Project overview and quick start
- CONTRIBUTING.md - Development guide
- docs/design/architecture.md - Architecture patterns
- docs/design/requirements.md - Base requirements
- docs/decisions/ - Architecture Decision Records
- tests/README.md - Testing guide
