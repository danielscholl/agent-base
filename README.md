# Agent Base

A functional agent base for building AI agents with multi-provider LLM support and built-in observability.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Overview

Build conversational AI agents with enterprise-grade features: session management, observability, and extensible toolsets.

```bash
agent

Agent - Conversational Assistant
Version 0.1.0 • OpenAI/gpt-5-mini

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

Supports OpenAI, Anthropic, Azure OpenAI, and Azure AI Foundry. Includes session persistence, conversation memory, and local observability.

## Prerequisites

### Cloud Resources (LLM Provider)

**Required - Choose one:**
- [OpenAI API](https://platform.openai.com/api-keys) - Direct OpenAI access
- [Anthropic API](https://console.anthropic.com/) - Direct Anthropic access
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource) - Azure-hosted OpenAI
- [Azure AI Foundry](https://ai.azure.com) - Managed AI platform

**Optional (for observability):**
- [Azure Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) - Cloud telemetry

### Local Tools (Development)

**Required:**
- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager

**Optional (enhances experience):**
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) - Simplifies Azure auth
- [Docker](https://docs.docker.com/get-docker/) - For local observability dashboard

## Quick Setup

```bash
# 1. Install
uv tool install --prerelease=allow git+https://github.com/danielscholl/agent-base.git

# Upgrade
uv tool upgrade agent

# 2. Configure required credentials
cp .env.example .env
```

**Authenticate with CLI tools** (recommended):
```bash
az login  # For Azure providers (OpenAI, AI Foundry)
```

**OR use API keys** (if CLI not available):
```bash
# AZURE_OPENAI_API_KEY=your-key
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key
```

**3. Verify setup**
```bash
agent --check   # Validate configuration
```

## Usage

```bash
# Interactive chat mode (with memory and session management)
agent

# Single query
agent -p "Say hello to Alice"

# Get help
agent --help
```

### Local Observability

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
