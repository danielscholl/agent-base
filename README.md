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
| Google Gemini | API Key | `GEMINI_API_KEY` |
| Azure OpenAI | Azure CLI  | az login |
| Azure AI Foundry | Azure CLI | az login |

#### Azure Provider Prerequisites

Use these when selecting Azure OpenAI or Azure AI Foundry providers:

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) – authentication (`az login`)
- [Azure Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/app-insights-overview) – observability (optional but recommended) 


## Quick Setup

```bash
# 1. Install agent
uv tool install --prerelease=allow git+https://github.com/danielscholl/agent-base.git

# 2. Configure (choose one method)

# Option A: Interactive setup (recommended)
agent config init

# Option B: Enable local provider (no API keys needed)
# The command below will automatically set up Docker and pull the model
agent config enable local

# Option C: Environment variables (for CI/CD)
export LLM_PROVIDER=local
# OR
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# 3. Start agent
agent
```

### Configuration

Agent supports two configuration methods:

**1. Interactive Configuration (Recommended)**

```bash
# First-time setup wizard
agent config init

# View current configuration
agent config show

# Enable additional providers
agent config enable openai
agent config enable anthropic

# Edit configuration file
agent config edit

# Validate configuration
agent config validate
```

**2. Environment Variables**

Environment variables override file settings and work for CI/CD:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
agent
```

> See `.env.example` for all available environment variables.

**Configuration Precedence:**
1. CLI arguments (highest priority)
2. Environment variables
3. Configuration file (`~/.agent/settings.json`)
4. Default values (lowest priority)

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


## Configuration Guide

### Configuration File Structure

Agent stores configuration in `~/.agent/settings.json`:

```json
{
  "version": "1.0",
  "providers": {
    "enabled": ["local"],
    "local": {
      "enabled": true,
      "base_url": "http://localhost:12434/engines/llama.cpp/v1",
      "model": "ai/phi4"
    },
    "openai": {
      "enabled": false,
      "api_key": null,
      "model": "gpt-5-mini"
    }
  },
  "agent": {
    "data_dir": "~/.agent",
    "log_level": "info"
  },
  "telemetry": {
    "enabled": false,
    "otlp_endpoint": "http://localhost:4317"
  },
  "memory": {
    "enabled": true,
    "type": "in_memory",
    "history_limit": 20
  }
}
```

### Configuration Commands

```bash
# Interactive setup wizard
agent config init

# View current settings
agent config show

# Enable providers
agent config enable openai      # Prompts for API key
agent config enable anthropic   # Prompts for API key
agent config enable azure       # Prompts for endpoint and deployment
agent config enable gemini      # Prompts for API key or Vertex AI

# Disable providers (opens interactive menu; select "Disable" when prompted)
agent config disable openai
# Note: This command opens a menu with options including "Disable provider".
# It does not immediately disable; follow the prompts to complete the action.

# Edit configuration file directly
agent config edit               # Opens in VSCode, vim, or nano

# Validate configuration
agent config validate
```

### Provider Configuration

**Local (Docker Models)**
- No API keys required
- Enabled by default
- Uses Docker Desktop Model Runner

**OpenAI**
```bash
agent config enable openai
# Enter API key when prompted
```

**Anthropic**
```bash
agent config enable anthropic
# Enter API key when prompted
```

**Azure OpenAI**
```bash
agent config enable azure
# Enter endpoint, deployment, and optionally API key
# Uses Azure CLI credentials if no API key provided
```

**Google Gemini**
```bash
agent config enable gemini
# Choose between API key or Vertex AI
# Enter credentials when prompted
```

### Environment Variable Overrides

Environment variables always override file settings:

```bash
# Override provider
export LLM_PROVIDER=openai

# Override API key
export OPENAI_API_KEY=sk-new-key

# Override model
export AGENT_MODEL=gpt-4o

# Run agent (uses overrides)
agent
```

### Troubleshooting

**Configuration not found**
```bash
# Create new configuration
agent config init
```

**Provider not connecting**
```bash
# Validate configuration
agent config validate

# Check connectivity
agent --check
```

**Want to use environment variables only**
```bash
# Just set environment variables - file is optional
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
agent
```


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code quality guidelines, and contribution workflow.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by [Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-services/ai-studio)
