# Agent Base

A functional agent base for building AI agents with multi-provider LLM support and built-in observability.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

Build conversational AI agents with enterprise-grade features: session persistence, conversation memory, observability, and extensible toolsets.

```bash
agent

Agent - Conversational Assistant
Version 0.1.0 • Local/phi4

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

Supports Local (Docker Models), OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, and Google Gemini.

## Prerequisites

### Required

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager

### LLM Provider (Choose One)

**Local:**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) - Local model serving (phi4, qwen3, etc.)

**Cloud Alternatives:**
- [OpenAI API](https://platform.openai.com/api-keys) - Direct OpenAI access
- [Anthropic API](https://console.anthropic.com/) - Direct Anthropic access
- [Google Gemini API](https://aistudio.google.com/apikey) - Direct Gemini access
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource) - Azure-hosted OpenAI
- [Azure AI Foundry](https://ai.azure.com) - Managed AI platform


### Optional Enhancements

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) - Simplifies Azure auth
- [Azure Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) - Cloud observability

## Quick Setup

### Local Model Setup

Run locally with Docker Models:

```bash
# Enable Model Runner and pull phi4
docker desktop enable model-runner --tcp=12434
docker model pull phi4
```

### Agent Setup

```bash
# Install agent
uv tool install --prerelease=allow git+https://github.com/danielscholl/agent-base.git

# Verify setup
agent --check
```

### Cloud Provider Setup

For cloud-based models (OpenAI, Anthropic, Azure, Gemini):

```bash
# 1. Install agent
uv tool install --prerelease=allow git+https://github.com/danielscholl/agent-base.git

# 2. Configure credentials
cp .env.example .env
# Edit .env: Set LLM_PROVIDER and add API keys

# Option A: Use CLI authentication (Azure only)
az login  # For Azure providers (OpenAI, AI Foundry)

# Option B: Use API keys
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key

# 3. Verify setup
agent --check
```

## Usage

```bash
# Interactive chat mode (with memory and session management)
agent

# Single query
agent -p "Say hello to Alice"

# Switch providers on the fly
agent --provider openai --model gpt-5-mini -p "Hello"
agent --provider local --model ai/qwen3 -p "Hello"
agent --provider anthropic -p "Hello"

# Start interactive session with specific provider
agent --provider local --model ai/phi4

# Get help
agent --help
```

### Observability

Monitor your agent's performance with OpenTelemetry:

```bash
# Run agent with telemetry enabled
ENABLE_OTEL=true

# Start local dashboard (requires Docker)
agent --telemetry start

# View at http://localhost:18888
# - Traces: Full execution hierarchy
# - Metrics: Token usage and costs
# - Logs: Structured application logs
```

See [USAGE.md](USAGE.md) for complete examples.


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality guidelines, and contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-services/ai-studio)
