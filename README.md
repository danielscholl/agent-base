# Agent Template

A generic chatbot agent with extensible tool architecture, built on Microsoft Agent Framework

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

Agent Template is a production-ready foundation for building AI agents with custom tools. It demonstrates clean architectural patterns including dependency injection, event-driven design, and comprehensive testing strategies.

The MVP implementation includes a HelloTools example that demonstrates the complete tool lifecycle: registration, invocation, error handling, and testing patterns that future tools will follow.

**Key architectural patterns:**
- Class-based toolsets with dependency injection (no global state)
- Multi-provider LLM support (OpenAI, Anthropic, Azure AI Foundry)
- Event bus for loose coupling between components
- Comprehensive testing with mocked dependencies
- Rich CLI with execution visualization

**[📖 Full Usage Guide](USAGE.md)** | **[🚀 Quick Start](#quick-setup)**

## Features

### Core Architecture
- **Clean tool registration** via factory pattern (no global state)
- **Type-safe tool initialization** via class constructors
- **Loose coupling** via event bus pattern for middleware/display communication
- **High test coverage** (85%+ target) via mockable dependencies
- **Modular design** with clear separation of concerns

### Multi-Provider LLM Support
- **OpenAI**: Direct OpenAI API (gpt-4o, gpt-4-turbo, etc.)
- **Anthropic**: Direct Anthropic API (claude-sonnet-4-5, claude-opus-4, etc.)
- **Azure AI Foundry**: Microsoft's managed AI platform with access to 1,800+ models

### Developer Experience
- **Typer + Rich CLI**: Modern command-line interface with automatic formatting, colored output, and example extraction from docstrings (see [ADR-0009](docs/decisions/0009-cli-framework-selection.md))
- **Execution visualization**: Real-time display of tool calls and responses
- **Configuration validation**: Health checks and environment validation
- **Flexible modes**: Interactive and single-prompt execution
- **Comprehensive documentation**: Examples and architecture guides

## Prerequisites

### Required
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- One of the supported LLM providers (OpenAI, Anthropic, or Azure AI Foundry)

### Optional
- Git (for version control)
- Docker (for containerized deployments)

## Quick Setup

```bash
# Clone repository
git clone https://github.com/danielscholl/agent-template.git
cd agent-template

# Install dependencies with uv
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your LLM provider credentials

# Verify installation
uv run agent --check
uv run agent --config

# Test with single prompt
uv run agent -p "Say hello to Alice"
```

## Usage

### Single Prompt Mode

```bash
# Execute a single prompt and exit
uv run agent -p "Your prompt here"

# Example: Use the hello_world tool
uv run agent -p "Say hello to Bob"
```

### Configuration Check

```bash
# Verify configuration is valid
uv run agent --check
```

### Show Configuration

```bash
# Display current configuration
uv run agent --config
```

For more detailed usage examples, see [USAGE.md](USAGE.md).

## Architecture

This project demonstrates several important architectural patterns:

1. **Dependency Injection**: Tools receive configuration through constructors, enabling easy testing
2. **Event Bus Pattern**: Loose coupling between middleware and display layers
3. **Class-based Toolsets**: Avoid global state, support multiple instances
4. **Structured Error Responses**: Consistent error handling across all tools
5. **Comprehensive Testing**: Unit and integration tests with mocked dependencies

See `docs/architecture/tool-architecture.md` for detailed architecture documentation.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and contribution guidelines.

### Quick Development Setup

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/agent --cov-report=html

# Code quality checks
uv run black --check src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
```

## Project Structure

```
agent-template/
├── src/agent/              # Main package
│   ├── __init__.py        # Package initialization
│   ├── agent.py           # Agent class with framework integration
│   ├── config.py          # Configuration management
│   ├── cli.py             # CLI entry point
│   ├── events.py          # Event bus implementation
│   ├── tools/             # Tool implementations
│   │   ├── toolset.py     # Base toolset class
│   │   └── hello.py       # HelloTools (MVP example)
│   └── utils/             # Utilities
│       └── errors.py      # Custom exceptions
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests (includes agent validation)
│   └── mocks/             # Test mocks
├── docs/                   # Documentation
│   ├── architecture/      # Architecture docs
│   └── decisions/         # ADRs (Architecture Decision Records)
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- CLI powered by [Rich](https://rich.readthedocs.io/) and [Typer](https://typer.tiangolo.com/)
- Testing with [pytest](https://pytest.org/)
