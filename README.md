# Agent Base

A functional agent base for building AI agents with multi-provider LLM support and built-in observability.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

Build conversational AI agents with enterprise-grade features: session persistence, conversation memory, observability, and extensible toolsets.

Supports Local (Docker Models), OpenAI, Anthropic, Google Gemini, Azure OpenAI, and Azure AI Foundry.

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

**Hosted Providers**  

| Provider | Auth Method | Notes |
|----------|-------------|-------|
| OpenAI | API Key | `OPENAI_API_KEY` |
| Anthropic | API Key | `ANTHROPIC_API_KEY` |
| Google Gemini | API Key | `GOOGLE_API_KEY` |
| Azure OpenAI | Azure CLI  | az login |
| Azure AI Foundry | Azure CLI | az login |

#### Azure Provider Prerequisites

Use these when selecting Azure OpenAI or Azure AI Foundry providers:

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) – authentication (`az login`)
- [Azure Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) – observability (optional but recommended) 


## Quick Setup

```bash
# Install agent
uv tool install --prerelease=allow git+https://github.com/danielscholl/agent-base.git

# Upgrade agent
uv tool upgrade agent-base

# Pull model
docker desktop enable model-runner --tcp=12434
docker model pull phi4

# Start agent
agent
```


### Hosted Providers

To use hosted providers instead, set required credentials as environment settings:

> `.env-example` lists required configuration; export to shell.

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

# Get help
agent --help
```

**Note:** Single prompt mode (`-p`) outputs clean text by default, perfect for piping or scripting. Use `--verbose` to see execution details.

### Observability

Monitor your agent's performance with OpenTelemetry:

```bash
# Start local dashboard (requires Docker)
# View at http://localhost:18888
agent --telemetry start
```

See [USAGE.md](USAGE.md) for complete examples.


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality guidelines, and contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-services/ai-studio)
