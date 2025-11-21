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

Agent uses a JSON configuration file at `~/.agent/settings.json` for managing providers, memory, and observability settings.

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

> **Advanced:** For CI/CD, Docker, Kubernetes, and environment variable configuration, see [docs/design/configuration.md](docs/design/configuration.md).

## Usage

```bash
# Interactive chat mode
agent

# Check the agent configuration
agent --check

# Check the tools being exposed to the agent
agent --tools

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

**Trace-Level Logging**: Capture detailed LLM request/response data with token counts for offline analysis:

```bash
# Enable trace logging (creates session-specific trace log files)
export LOG_LEVEL=trace

# Optional: Include full message content in traces
export ENABLE_SENSITIVE_DATA=true

# Run agent
agent -p "Say hello"

# View trace logs (JSON format)
cat ~/.agent/logs/session-*-trace.log | jq .

# Analyze token usage
cat ~/.agent/logs/session-*-trace.log | jq -s 'map(select(.tokens)) | map(.tokens.total) | add'
```

Trace logs include token usage, timing, and model info. Full message content requires `ENABLE_SENSITIVE_DATA=true`.

See [USAGE.md](USAGE.md) for complete examples.

## Skills

Skills are lightweight extensions that add domain-specific capabilities to an agent without increasing the core footprint. They’re automatically discovered at runtime and come in two forms: bundled skills that ship with the agent, and plugin skills that can install from any git repository. Each skill loads only its minimal metadata by default, with additional tools or scripts activated on demand to keep token usage low.

### Installing Skills

Agent Base supports installing skills directly from any git repository:

```bash
agent skill install <git-url>
```

Once installed, skills are automatically discovered and integrated into the agent runtime.

### Managing Skills

Use the built-in management commands to view, enable/disable, or update installed skills:

```bash
agent skill show
agent skill manage
```

See [SKILLS.md](docs/design/skills.md) for additional details and information on constructing skills.


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality guidelines, and contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-services/ai-studio)
