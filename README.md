# Agent Base

A functional agent base for building AI agents with multi-provider LLM support and built-in observability.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

Build conversational AI agents with enterprise-grade features: session persistence, conversation memory, observability, and extensible toolsets.

Supports Local (Docker Models), GitHub Models, OpenAI, Anthropic, Google Gemini, Azure OpenAI, and Azure AI Foundry.

```bash
agent

Agent - Conversational Assistant
Version 0.1.0 • Local/ai/phi4

> Say hello to Alice

● Thinking...

Hello, Alice! ◉‿◉

> What was the name I just mentioned?

● Thinking...

You mentioned "Alice."

> exit
Saved 4 memories
Session auto-saved as '2025-11-10-11-38-07'

Goodbye!
```

## Prerequisites

### Required

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager


### LLM Providers

**Local (Docker Models)**  
Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) for local model serving.

> **Note:** Docker-based local models work on Windows, but performance is significantly slower due to Windows virtualization overhead. For best results, use a hosted provider or run Docker only on Linux/macOS.

**Hosted Providers**

| Provider | Auth Method |
|----------|-------------|
| GitHub Models | GitHub CLI (`gh auth login`) |
| OpenAI | API Key |
| Anthropic | API Key |
| Google Gemini | API Key |
| Azure OpenAI | Azure CLI (`az login`) |
| Azure AI Foundry | Azure CLI (`az login`) |

#### Azure Provider Prerequisites

Use these when selecting Azure OpenAI or Azure AI Foundry providers:

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) – authentication (`az login`)
- [Azure Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) – observability (optional but recommended) 


## Quick Setup

```bash
# 1. Install agent
uv tool install --prerelease=allow git+https://github.com/danielscholl/agent-base.git

# 2. Start agent
agent

# Get help
agent --help
```

### Configuration

Agent uses a configuration file at `~/.agent/settings.json` for managing providers, memory, and observability settings.

**Configuration Commands:**

```bash
# Interactive setup wizard
agent config init

# View current configuration
agent config show

# Manage providers
agent config provider local       # Enable/configure local (Docker)
agent config provider github      # Enable/configure GitHub Models
agent config provider openai      # Enable/configure OpenAI

# Configure memory backend
agent config memory               # Switch between in_memory and mem0
```

> **Advanced:** For CI/CD and development, see [CONTRIBUTING.md](CONTRIBUTING.md) for environment variable configuration.

## Usage

```bash
# Interactive chat mode
agent

# Check the agent configuration
agent --check

# Single query (clean output for scripting)
agent -p "Say hello to Alice"

# Single query with verbose execution details
agent -p "Analyze this text" --verbose

# Switch providers on the fly
agent --provider openai -p "Hello"

# Switch models on the fly
agent --provider anthropic --model claude-sonnet-4-5-20250929 -p "Hello"
```

**Note:** Single prompt mode (`-p`) outputs clean text by default, perfect for piping or scripting. Use `--verbose` to see execution details.

### Observability

Monitor your agent's performance with Telemetry:

```bash
# Start local dashboard (requires Docker)
# View at http://localhost:18888
agent --telemetry start
```

See [USAGE.md](USAGE.md) for complete examples.

## Skills

agent-base supports a plugin system for domain-specific capabilities through **skills** - self-contained packages that extend the agent with specialized tools without bloating the core codebase.

### What are Skills?

Skills are git-based packages combining:
- **Python Toolsets**: Testable, type-safe tool classes for frequent operations
- **Standalone Scripts**: PEP 723 scripts for context-heavy operations (progressive disclosure)
- **SKILL.md Manifest**: YAML front matter + markdown instructions

### Using Skills

**Bundled skills are auto-discovered and enabled by default.** No configuration needed!

```bash
# List all available skills (shows token cost per skill)
agent skill list

# Manage skills interactively (enable/disable/update/remove)
agent skill manage

# Check what tools are loaded
agent --tools
```

### Available Tools

When skills are loaded, you get:
- **Skill toolset methods** - Direct tool calls (e.g., `greet_in_language`)
- **Script wrapper tools** - Progressive disclosure pattern:
  - `script_list` - List available scripts
  - `script_help` - Get help for a script
  - `script_run` - Execute a script with arguments

### Example: Installing and Using Skills

**Install from git repository (supports monorepos):**

```bash
# Install plugins from agent-skills repository
# This installs both web-access and kalshi-markets
agent skill install https://github.com/danielscholl/agent-skills

# View installed skills with token costs
agent skill list
# Output:
#   Bundled:
#     ◉ hello-extended (core/hello-extended) · 206 tokens
#
#   Plugins:
#     ◉ web-access (agent-skills, main@eb3cb56) · 280 tokens
#     ◉ kalshi-markets (agent-skills, main@eb3cb56) · 250 tokens

# Use the skills naturally in conversation
agent -p "Search for Python 3.13 features"  # Uses web-access
agent -p "Check Kalshi exchange status"      # Uses kalshi-markets
```

### Bundled Skill

**hello-extended** - Extended greeting capabilities (example skill)
- Python toolset: `greet_in_language`, `greet_multiple`
- Script: Advanced greeting with time-awareness
- Demonstrates hybrid skill architecture (toolset + script)
- Auto-enabled by default (206 tokens)

### Plugin Skills

**Available at https://github.com/danielscholl/agent-skills:**

**web-access** - Internet search and web content retrieval
- `fetch.py` - Retrieve web pages as markdown
- `search.py` - Brave Search API integration
- Requires `BRAVE_API_KEY` environment variable
- 280 tokens

**kalshi-markets** - Access Kalshi prediction market data
- Market prices, orderbooks, trades (10 scripts)
- Event and series information
- Progressive disclosure
- 250 tokens

### Managing Skills

**Installation:**
```bash
# Install plugins (supports single-skill and monorepo)
agent skill install https://github.com/danielscholl/agent-skills

# Interactive install (prompts for URL)
agent skill install

# View all skills with token costs and commit SHA
agent skill list
```

**Management:**
```bash
# Interactive management (enable/disable/update/remove)
agent skill manage

# Select skill → Choose action → Done
```

**Discovery:**
Skills are automatically discovered from git repos:
- SKILL.md at root → Single skill
- skill/SKILL.md → Skill in subdirectory
- */SKILL.md → Monorepo (multiple skills)

### Creating Custom Skills

See [docs/design/skills.md](docs/design/skills.md) for the complete skill development guide.

Minimal skill structure:
```
my-skill/
├── SKILL.md              # Manifest with YAML front matter
├── toolsets/             # Optional: Python toolset classes
│   └── mytools.py
└── scripts/              # Optional: PEP 723 standalone scripts
    └── myscript.py
```

Example SKILL.md:
```yaml
---
name: my-skill
description: Brief description of what this skill does
toolsets:
  - toolsets.mytools:MyToolset
---

# Usage instructions in markdown...
```

### Context Efficiency

Skills use progressive disclosure to maintain <5K token overhead:
- Only SKILL.md manifest loaded into context
- Scripts discovered but NOT loaded (just metadata)
- Execute scripts on-demand via `script_run`
- 10+ tools available with minimal context usage

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality guidelines, and contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-services/ai-studio)
