# Contributing to Agent Template

Thank you for your interest in contributing to Agent Template!

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- One of the supported LLM providers (OpenAI, Anthropic, or Azure AI Foundry)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/danielscholl/agent-template.git
cd agent-template

# Install dependencies with dev extras
uv sync --all-extras

# Configure environment
cp .env.example .env
# Edit .env with required values for your LLM provider

# Verify installation
uv run agent --help
uv run agent --check
```

### Environment Configuration

Create a `.env` file with your configuration:

```bash
cp .env.example .env
```

**For OpenAI:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-api-key
```

**For Anthropic:**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key
```

**For Azure AI Foundry:**
```bash
LLM_PROVIDER=azure_ai_foundry
AZURE_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-id
AZURE_MODEL_DEPLOYMENT=gpt-4o
# Then run: az login
```

## Code Quality

### Quality Checks

Before submitting PRs, run all quality checks:

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

1. **Black**: Code formatting verification
2. **Ruff**: Linting and import sorting
3. **MyPy**: Type checking
4. **PyTest**: Tests with 85% coverage requirement
5. **CodeQL**: Security scanning (weekly)

All checks must pass for merge.

### Testing

```bash
# Run full test suite
uv run pytest

# Run with coverage report
uv run pytest --cov=src/agent --cov-report=html
open htmlcov/index.html

# Run specific test file
uv run pytest tests/unit/test_agent.py

# Run specific test
uv run pytest tests/unit/test_agent.py::test_agent_initialization

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

### Code Coverage

We maintain a minimum of 85% code coverage. When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure new code has test coverage
3. Run coverage report to verify
4. Update tests if coverage drops below threshold

Files excluded from coverage:
- Display logic (`src/agent/display/`) - hard to test, will be addressed in Phase 3
- Test files themselves

## Commit Guidelines

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning and changelog generation.

### Commit Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Commit Types

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feat` | New feature | Minor (0.x.0) | `feat(tools): add WebTools for scraping` |
| `fix` | Bug fix | Patch (0.0.x) | `fix(config): handle missing env vars` |
| `docs` | Documentation only | None | `docs: update USAGE.md examples` |
| `style` | Code style changes | None | `style: format with black` |
| `refactor` | Code refactoring | None | `refactor(agent): extract session logic` |
| `test` | Add/update tests | None | `test: add HelloTools edge cases` |
| `chore` | Maintenance | None | `chore: update dependencies` |
| `ci` | CI/CD changes | None | `ci: add CodeQL workflow` |
| `perf` | Performance improvements | Patch | `perf(tools): cache API responses` |

### Scopes

Common scopes in this project:
- `agent`: Agent class and core functionality
- `config`: Configuration management
- `tools`: Tool implementations
- `cli`: CLI interface
- `events`: Event bus
- `tests`: Test infrastructure

### Breaking Changes

For breaking changes, add `!` after type and include `BREAKING CHANGE:` in footer:

```
feat(config)!: redesign configuration system

BREAKING CHANGE: Configuration now uses dataclasses instead of dict.
Update code to use AgentConfig.from_env() instead of load_config().
```

### Examples

```bash
# New feature
git commit -m "feat(tools): add greet_user tool with language support"

# Bug fix
git commit -m "fix(agent): handle empty tool list gracefully"

# Documentation
git commit -m "docs: add architecture decision record for event bus"

# Multiple changes
git commit -m "feat(cli): add interactive mode

- Implement prompt_toolkit shell
- Add session management
- Support command history"

# Breaking change
git commit -m "feat(config)!: switch to pydantic for validation

BREAKING CHANGE: AgentConfig now requires pydantic models.
Update imports from agent.config import AgentConfig."
```

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/bug-description
```

Branch naming:
- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test additions/fixes

### 2. Make Changes

1. Write tests first (TDD approach)
2. Implement feature/fix
3. Ensure all quality checks pass
4. Update documentation if needed

### 3. Commit Changes

Use conventional commits:

```bash
git add .
git commit -m "feat(scope): description"
```

### 4. Push and Create PR

```bash
git push origin feat/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title following conventional commits
- Description of changes
- Link to related issues
- Screenshots/examples if applicable

### 5. Address Review Feedback

1. Make requested changes
2. Add new commits (don't force push during review)
3. Re-request review when ready

### 6. Merge

Maintainers will merge when:
- All CI checks pass
- Code review approved
- Conflicts resolved

## Architecture Decision Records

For significant architectural decisions, create an ADR in `docs/decisions/`:

### When to Create an ADR

Create an ADR when deciding:
- Architecture patterns (tool registration, event bus, etc.)
- Technology choices (frameworks, libraries)
- Design patterns (observer, factory, dependency injection)
- API designs (method signatures, response formats)
- Testing strategies (mocking patterns, coverage targets)

### ADR Process

1. **Copy template:**
   ```bash
   cp docs/decisions/adr-template.md docs/decisions/0XXX-your-decision.md
   ```

2. **Fill in content:**
   - Status: `proposed`
   - Context and problem statement
   - Decision drivers
   - Considered options
   - Decision outcome
   - Consequences

3. **Include in PR:**
   - ADRs should be included in the same PR as the implementation
   - Update status to `accepted` once PR is merged

4. **Example ADRs:**
   - See existing ADRs in `docs/decisions/`
   - Follow the template structure

See [docs/decisions/README.md](docs/decisions/README.md) for complete ADR documentation.

## Code Style

### Python Style Guide

We follow PEP 8 with these specifications:

- **Line length**: 100 characters (configured in black/ruff)
- **Imports**: Sorted by isort via ruff
- **Type hints**: Required for public APIs
- **Docstrings**: Google style for public functions/classes

### Docstring Example

```python
def hello_world(name: str = "World") -> dict:
    """Say hello to someone.

    Args:
        name: Name of person to greet (default: "World")

    Returns:
        Success response with greeting message

    Raises:
        ValueError: If name is empty string

    Example:
        >>> tools = HelloTools(config)
        >>> result = await tools.hello_world("Alice")
        >>> print(result)
        {'success': True, 'result': 'Hello, Alice!', 'message': ''}
    """
    ...
```

### Type Hints

```python
# Required for public APIs
def process_data(data: list[dict[str, Any]]) -> tuple[int, list[str]]:
    ...

# Optional for private functions (but recommended)
def _helper(x: int) -> int:
    ...

# Use Protocol for interfaces
from typing import Protocol

class ToolProvider(Protocol):
    def get_tools(self) -> list[Callable]: ...
```

## CLI Development

This project uses **Typer** with **Rich** formatting for all agent CLIs. This provides modern, user-friendly command-line interfaces with automatic help formatting, colored output, and example extraction.

### CLI Framework Standards

**Default: Typer + Rich** (recommended for all agent CLIs)
- Modern command-line interface framework
- Automatic Rich formatting when `rich` is installed
- Examples extracted from docstrings
- Type-safe argument parsing with Python type hints
- See [ADR-0009](docs/decisions/0009-cli-framework-selection.md) for rationale

**Alternative: argparse** (only for specific use cases)
- Use only when stdlib-only is critical
- Minimal utility scripts
- Traditional Unix tool aesthetic required
- CI/CD tools where dependencies must be minimal

### Creating a New CLI

**1. Basic Typer CLI Structure:**

```python
"""CLI entry point for YourAgent."""

import typer
from rich.console import Console

app = typer.Typer(help="YourAgent - Brief description")
console = Console()

@app.command()
def main(
    prompt: str = typer.Option(None, "-p", "--prompt", help="Execute a single prompt"),
    check: bool = typer.Option(False, "--check", help="Run health check"),
    config_flag: bool = typer.Option(False, "--config", help="Show configuration"),
):
    """YourAgent - Detailed description here.

    Examples:
        # Run health check
        youragent --check

        # Execute single prompt
        youragent -p "Do something"

        # Show configuration
        youragent --config
    """
    if check:
        run_health_check()
    elif config_flag:
        show_configuration()
    elif prompt:
        run_single_prompt(prompt)

if __name__ == "__main__":
    app()
```

**2. Update pyproject.toml Entry Points:**

```toml
[project.scripts]
youragent = "youragent.cli:app"  # Points to Typer app object, not function
```

**3. Required Dependencies:**

```toml
dependencies = [
    "typer>=0.12.0",  # CLI framework
    "rich>=14.1.0",   # Formatting (auto-detected by Typer)
]
```

### Docstring Format for CLI Examples

Typer automatically extracts examples from docstrings. Follow this pattern:

```python
@app.command()
def main(
    option: str = typer.Option(None, "--opt", help="An option"),
):
    """Brief one-line description.

    Longer description if needed. Can span multiple lines.
    Explain what the command does and its purpose.

    Examples:
        # Example 1: Brief description
        command --opt value

        # Example 2: Another use case
        command --other-flag

        # Example 3: Complex example
        command --opt "value with spaces" --flag
    """
    pass
```

**Best practices:**
- Start each example with a `#` comment explaining what it does
- Show real command usage (not pseudo-code)
- Include common use cases and edge cases
- Use proper argument formatting (quotes for spaces, etc.)
- Examples appear in `--help` output automatically

### CLI Options Patterns

**Boolean flags:**
```python
verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
```

**String options:**
```python
config_path: str = typer.Option("config.yaml", "--config", "-c", help="Config file path")
```

**Optional strings:**
```python
prompt: str = typer.Option(None, "--prompt", "-p", help="Prompt to execute")
```

**Enums for choices:**
```python
from enum import Enum

class Provider(str, Enum):
    openai = "openai"
    anthropic = "anthropic"

provider: Provider = typer.Option(Provider.openai, "--provider", help="LLM provider")
```

### Rich Console Output

Use Rich console for all output:

```python
from rich.console import Console

console = Console()

# Success messages
console.print("[green]✓[/green] Operation successful")

# Errors
console.print("[red]✗[/red] Error occurred")

# Warnings
console.print("[yellow]⚠[/yellow] Warning message")

# Info
console.print("[blue]ℹ[/blue] Information")

# Formatted text
console.print("[bold]Section Title[/bold]")
console.print("Regular text with [yellow]highlighted[/yellow] parts")
```

### Exit Codes

Follow standard Unix exit codes:

```python
import typer

# Success
return  # or sys.exit(0)

# General error
raise typer.Exit(1)

# Configuration error
raise typer.Exit(1)

# User interrupt (Ctrl+C)
raise typer.Exit(130)
```

### Testing CLIs

```python
from typer.testing import CliRunner
from youragent.cli import app

runner = CliRunner()

def test_help_output():
    """Test --help displays correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "YourAgent" in result.stdout
    assert "Examples:" in result.stdout

def test_check_command():
    """Test --check runs health check."""
    result = runner.invoke(app, ["--check"])
    assert result.exit_code == 0
    assert "Health Check" in result.stdout
```

### When to Use Argparse

Only use argparse when:
- **Stdlib-only requirement is critical** (no external dependencies allowed)
- **Building minimal utility scripts** (not primary agent CLIs)
- **Traditional Unix tool aesthetic** is explicitly required
- **CI/CD tools** where dependency management is constrained

If using argparse, document why in code comments:

```python
# Using argparse instead of Typer due to stdlib-only requirement for CI deployment
import argparse

def main():
    parser = argparse.ArgumentParser(description="Utility script")
    # ... rest of implementation
```

### CLI Checklist

When creating a new CLI, ensure:

- [ ] Uses Typer framework (unless exception applies)
- [ ] Rich is in dependencies for automatic formatting
- [ ] Entry point in `pyproject.toml` points to Typer app object
- [ ] Function docstring includes `Examples:` section
- [ ] Examples follow format: `# Comment\n    command args`
- [ ] All options have clear help text
- [ ] Boolean flags use `--flag` (not `--flag VALUE`)
- [ ] Uses Rich console for all output
- [ ] Proper exit codes (0 for success, >0 for errors)
- [ ] Tests verify help output and basic functionality
- [ ] Documented in README.md if user-facing

## Testing Guidelines

### Test Organization

```
tests/
├── unit/              # Unit tests (isolated components)
│   ├── test_agent.py
│   ├── test_config.py
│   └── test_tools.py
├── integration/       # Integration tests (full stack)
│   └── test_hello_integration.py
├── mocks/            # Test mocks
│   └── mock_client.py
└── conftest.py       # Shared fixtures
```

### Writing Tests

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
    assert "World" in result["message"]

@pytest.mark.asyncio
async def test_hello_world_custom_name(hello_tools):
    """Test hello_world with custom name."""
    result = await hello_tools.hello_world("Alice")

    assert result["success"] is True
    assert "Alice" in result["result"]

@pytest.mark.asyncio
async def test_greet_user_unsupported_language(hello_tools):
    """Test greet_user with unsupported language returns error."""
    result = await hello_tools.greet_user("Bob", "de")

    assert result["success"] is False
    assert result["error"] == "unsupported_language"
    assert "de" in result["message"]
```

### Test Coverage Targets

- **Unit tests**: 100% coverage for business logic
- **Integration tests**: Cover happy path and major error cases
- **Overall**: Minimum 85% coverage (enforced by CI)

### Mocking Guidelines

```python
# Use fixtures for common mocks
@pytest.fixture
def mock_config():
    """Mock AgentConfig for testing."""
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4o",
    )

@pytest.fixture
def mock_chat_client():
    """Mock chat client."""
    from tests.mocks.mock_client import MockChatClient
    return MockChatClient(response="Mock response")

# Use dependency injection
def test_agent_with_mocks(mock_config, mock_chat_client):
    """Test agent with mocked dependencies."""
    agent = Agent(config=mock_config, chat_client=mock_chat_client)
    assert agent is not None
```

## Release Process

Releases are automated using [release-please](https://github.com/googleapis/release-please):

1. **Commit with conventional commits** - Version bumps calculated automatically
2. **PR created automatically** - Merge to trigger release
3. **GitHub Release created** - Changelog generated from commits
4. **Package published** - Artifacts uploaded to GitHub Releases

### Version Bumping

Based on commit types:
- `feat:` → Minor version (0.x.0)
- `fix:` → Patch version (0.0.x)
- `feat!:` or `BREAKING CHANGE:` → Major version (x.0.0)

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/danielscholl/agent-template/discussions)
- **Bugs**: Open an [Issue](https://github.com/danielscholl/agent-template/issues)
- **Security**: Email security@example.com (private disclosure)

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). By participating, you agree to uphold this code.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
