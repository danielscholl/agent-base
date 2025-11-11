---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Title: Module and Package Naming Conventions

## Context and Problem Statement

We need to establish consistent naming conventions for the agent-template project. The project requires a Python package structure that follows community best practices while being intuitive for developers. We must decide on package naming, module organization, and file naming patterns.

## Decision Drivers

- **Python conventions**: Follow PEP 8 and community standards
- **Clarity**: Names should clearly indicate purpose
- **Simplicity**: Avoid complex hierarchies
- **Discoverability**: Easy to find relevant code
- **Tool compatibility**: Work well with IDEs and build tools

## Considered Options

1. **src-layout with `agent` package name**
2. **Flat layout with `agent_template` package name**
3. **src-layout with `agent_template` package name**

## Decision Outcome

Chosen option: **"src-layout with `agent` package name"**

This provides the best balance of simplicity, clarity, and Python best practices. The `src` layout prevents accidental imports during development, and the simple `agent` name is clean and memorable.

### Package Structure

```
agent-template/                 # Repository name (descriptive, with dash)
├── src/agent/                  # Package name (simple, importable)
│   ├── __init__.py
│   ├── agent.py                # Core agent class
│   ├── config.py               # Configuration
│   ├── cli.py                  # CLI entry point
│   ├── events.py               # Event bus
│   ├── tools/                  # Tool implementations
│   │   ├── __init__.py
│   │   ├── toolset.py          # Base class
│   │   └── hello.py            # HelloTools
│   └── utils/                  # Utilities
│       ├── __init__.py
│       └── errors.py           # Custom exceptions
├── tests/                      # Test suite
└── docs/                       # Documentation
```

### Naming Rules

**Package and Module Names:**
- **Package name**: `agent` (simple, lowercase, no underscores)
- **Module names**: `agent.py`, `config.py`, `cli.py` (lowercase, descriptive)
- **Subpackages**: `tools/`, `utils/` (plural for collections)

**Import Pattern:**
```python
from agent import Agent, AgentConfig
from agent.tools.hello import HelloTools
from agent.utils.errors import AgentError
```

**Repository name**: `agent-template` (with dash for GitHub URL)

### Consequences

**Good:**
- Clean imports: `from agent import Agent`
- src-layout prevents import confusion during development
- Follows Python packaging best practices (PEP 420, PEP 517)
- Simple hierarchy, easy to navigate
- Compatible with all Python tools (uv, pip, setuptools)

**Neutral:**
- Repository name differs from package name (common pattern)
- Requires understanding src-layout vs flat-layout

**Bad:**
- Generic `agent` name may conflict with other packages (mitigated by using unique distribution name `agent-template`)

## Pros and Cons of the Options

### Option 1: src-layout with `agent` package name

- Good: Clean imports (`from agent import Agent`)
- Good: Prevents accidental imports during development
- Good: Follows modern Python packaging standards
- Good: Simple, memorable package name
- Neutral: Repository vs package name difference
- Bad: Generic name could conflict (but namespace is `agent_template` on PyPI)

### Option 2: Flat layout with `agent_template` package name

- Good: Package name matches repository
- Good: More explicit, no ambiguity
- Bad: Longer imports (`from agent_template import Agent`)
- Bad: Underscore in package name (less common)
- Bad: No isolation during development (can import unpacked code)
- Bad: Old-school pattern, discouraged by modern tools

### Option 3: src-layout with `agent_template` package name

- Good: src-layout benefits
- Good: Unique package name
- Bad: Longer, less clean imports
- Bad: Underscore makes it feel less polished
- Neutral: More explicit but more verbose

## Implementation Notes

### pyproject.toml Configuration

```toml
[project]
name = "agent-template"          # Distribution name (PyPI)
version = "0.1.0"

[project.scripts]
agent = "agent.cli:app"          # CLI entry point

[tool.hatchling.build.targets.wheel]
packages = ["src/agent"]         # Package location
```

### Import Examples

**Public API:**
```python
from agent import Agent, AgentConfig
```

**Internal imports:**
```python
from agent.tools.hello import HelloTools
from agent.utils.errors import ConfigurationError
```

**Test imports:**
```python
from agent.agent import Agent
from tests.mocks.mock_client import MockChatClient
```

## References

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 420 - Implicit Namespace Packages](https://peps.python.org/pep-0420/)
- [PEP 517 - A build-system independent format](https://peps.python.org/pep-0517/)
- [Python Packaging User Guide - src-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [Hynek Schlawack - Testing & Packaging](https://hynek.me/articles/testing-packaging/)

## Related Decisions

- ADR-0002: Repository Infrastructure and DevOps Setup (build system configuration)
- ADR-0003: Configuration Management Strategy (module organization for config)
