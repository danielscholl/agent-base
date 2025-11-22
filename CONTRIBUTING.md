# Contributing

Development guide for Agent Base contributors.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/danielscholl/agent-base.git
cd agent-base
uv sync --all-extras

# 2. Configure
uv run agent config init

# 3. Verify
uv run agent --check

# For environment variable configuration, see:
# docs/design/config.md
```

## Development Workflow

### 1. Run Tests Before Changes

```bash
# Run all free tests (CI equivalent)
uv run pytest -m "not llm" -n auto

# Should complete in ~10 seconds with ~966 tests passing
```

### 2. Make Your Changes

Follow the patterns in existing code and see [docs/design/architecture.md](docs/design/architecture.md) for architectural guidelines.

### 3. Run Tests After Changes

```bash
# Run tests with coverage
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# Run code quality checks
uv run black src/agent/ tests/
uv run ruff check --fix src/agent/ tests/
uv run mypy src/agent/
```

### 4. Commit and Push

```bash
# Use conventional commits format
git commit -m "feat(tools): add new capability"

# Push and create PR
git push origin feat/your-feature
```

## Testing

### Test Organization

Tests are organized by type with clear cost implications:

| Type | Location | Cost | Speed | When to Run |
|------|----------|------|-------|-------------|
| **Unit** | `tests/unit/` | Free | Fast (~2s) | During development |
| **Integration** | `tests/integration/` | Free | Fast (~2s) | Before commit |
| **Validation** | `tests/validation/` | Free | Moderate | Before commit |
| **LLM** | `tests/integration/llm/` | **Costs money** | Slow (~30s) | Opt-in only |

**Key Point:** Only LLM tests make real API calls. All others use mocks and are completely free.

### Common Test Commands

```bash
# Fast feedback loop (unit tests only)
uv run pytest -m unit -n auto

# CI equivalent (all free tests with coverage)
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# Specific feature area
uv run pytest -m tools      # Tool tests
uv run pytest -m agent      # Agent core tests
uv run pytest -m cli        # CLI tests

# Run one test file
uv run pytest tests/unit/tools/test_hello_tools.py -v

# Run one specific test
uv run pytest tests/unit/tools/test_hello_tools.py::test_hello_world -v

# Real LLM tests (requires API key)
### $$$ (Costs Money)
uv run pytest -m llm -n auto
```

### Test Markers

Combine markers to run specific subsets:

```bash
# Unit tests for tools only
uv run pytest -m "unit and tools"

# All tests except LLM and slow tests
uv run pytest -m "not llm and not slow"

# Integration tests for middleware
uv run pytest -m "integration and middleware"
```

**Available markers:**
- **Type:** `unit`, `integration`, `validation`, `llm`
- **Area:** `agent`, `tools`, `cli`, `middleware`, `display`, `config`, `events`, `persistence`, `memory`
- **Speed:** `fast`, `slow`
- **Provider:** `requires_openai`, `requires_anthropic`, `requires_azure`

### Writing Tests

Use templates as starting points:

```bash
# Copy template
cp tests/templates/test_tool_template.py tests/unit/tools/test_my_tool.py

# Edit and add appropriate markers
@pytest.mark.unit
@pytest.mark.tools
async def test_my_feature(tool_config):
    tool = MyTool(tool_config)
    result = await tool.my_function("input")
    assert_success_response(result)  # Helper validates response format
```

**Test utilities:**
- `assert_success_response(result)` - Validate `{"success": True, "result": ...}`
- `assert_error_response(result, "error_code")` - Validate error format
- `build_test_config(provider)` - Create test configurations
- `mock_config` - Fixture for AgentConfig
- `mock_chat_client` - Fixture for mocked LLM
- `agent_instance` - Fixture for pre-configured Agent

See [tests/README.md](tests/README.md) for comprehensive testing guide.

### Coverage Requirements

- **Minimum:** 85% overall coverage (enforced by CI)
- **Excluded:** CLI orchestration (`cli/app.py`), display rendering, error definitions
- **View report:** `uv run pytest --cov=src/agent --cov-report=html && open htmlcov/index.html`

## Code Style

**Type hints required** for all public APIs:

```python
async def my_tool(
    self,
    input: Annotated[str, Field(description="User input")]
) -> dict:
    """Brief tool description for LLM. Include key constraints and defaults."""
    ...
```

**Tool docstrings** should be concise for LLM consumption (see [ADR-0017](docs/decisions/0017-tool-docstring-optimization.md)):

```python
# GOOD - Simple tool (10-20 tokens)
"""Say hello to someone. Returns greeting message."""

# GOOD - Complex tool (25-40 tokens)
"""Read text file within workspace by line range. Paths relative to workspace root. Default: first 200 lines. Returns content with truncation flag for large files."""

# BAD - Verbose (200+ tokens)
"""Read text file contents by line range with chunking support.

Reads text files with UTF-8 encoding, provides pagination for large files,
and detects binary files automatically.

Args:
    path: File path relative to workspace root
    start_line: Starting line number (1-based, default: 1)
    max_lines: Maximum lines to read (capped at 1000, default: 200)

Returns:
    Success response with file content:
    {
        "success": True,
        "result": {
            "path": str,
            "start_line": int,
            # ... 50 more lines
        }
    }

Example:
    >>> result = await tools.read_file("src/main.py", start_line=1, max_lines=50)
    >>> if result["success"]:
    ...     print(result["result"]["content"])
"""
```

**What to include in tool docstrings:**
- What the tool does (first sentence)
- Critical constraints ("Paths relative to workspace root")
- Required prerequisites ("Requires filesystem_writes_enabled")
- Key defaults ("Default: first 200 lines")
- ✗ Code examples (`>>> usage`)
- ✗ Complete response format structures
- ✗ Detailed parameter documentation (use `Field(description="...")` instead)
- ✗ Implementation details
- ✗ Multi-line Args/Returns/Example sections

**Move comprehensive documentation to:**
- Class docstrings (for detailed tool guides)
- Module docstrings (for implementation notes)
- Separate documentation files
- Code comments (for inline complexity)

**Structured responses** for all tools:

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

**Line length:** 100 characters (enforced by Black)

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `test` - Tests
- `chore` - Maintenance

**Examples:**
```bash
git commit -m "feat(tools): add language parameter to hello_world"
git commit -m "fix(agent): handle empty tool list gracefully"
git commit -m "docs(architecture): add memory architecture ADR"
```

## Pull Request Process

1. **Create branch:** `git checkout -b feat/your-feature`
2. **Make changes** following code style
3. **Run quality checks** (see above)
4. **Commit** using conventional format
5. **Push:** `git push origin feat/your-feature`
6. **Create PR** with clear description

**PR Requirements:**
- All CI checks pass
- Coverage ≥ 85%
- Type hints on public APIs
- Docstrings for public functions
- Conventional commit format

## Architecture Decisions

For significant architectural changes, document decisions in `docs/decisions/`:

**When to create an ADR:**
- Adding new architectural patterns
- Choosing between design alternatives
- Making technology/library selections
- Changing core system behaviors

**Process:**

```bash
# 1. Copy template
cp docs/decisions/adr-template.md docs/decisions/NNNN-your-decision.md

# 2. Fill in sections:
#    - Context and Problem Statement
#    - Decision Drivers
#    - Considered Options
#    - Decision Outcome
#    - Consequences

# 3. Commit with decision
git commit -m "docs(adr): add ADR for [decision topic]"
```

See existing ADRs in `docs/decisions/` for examples:
- [ADR-0006](docs/decisions/0006-class-based-toolset-architecture.md) - Toolset design
- [ADR-0013](docs/decisions/0013-memory-architecture.md) - Memory patterns
- [ADR-0014](docs/decisions/0014-observability-integration.md) - OpenTelemetry

## Releases

Releases use [release-please](https://github.com/googleapis/release-please):
- `feat:` → minor version bump
- `fix:` → patch version bump
- `BREAKING CHANGE:` → major version bump

Merging the release PR automatically creates a GitHub release.

## License

By contributing, you agree your contributions will be licensed under the MIT License.
