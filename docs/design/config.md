# Configuration

Configuration system for Agent Base with JSON-based settings and environment variable overrides.

## Overview

Agent Base uses a dual-layer configuration system prioritizing user-friendly JSON files with environment variable overrides for deployment flexibility.

### Configuration Flow

```
┌─────────────────────────────────────┐
│   Environment Variables (Highest)   │
│   Runtime overrides for CI/CD       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   ~/.agent/settings.json (Primary)  │
│   User configuration via CLI        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   config/defaults.py (Fallback)     │
│   Built-in sensible defaults        │
└─────────────────────────────────────┘
```

### Priority Order

1. **Environment Variables** - Override everything (CI/CD, containers)
2. **Settings File** - Primary user configuration (`~/.agent/settings.json`)
3. **Defaults** - Built-in fallback values

**Example:** `AGENT_MODEL=gpt-5-mini` overrides `settings.json` value.

## Primary Configuration Method

### Interactive Setup

```bash
agent config init
```

Launches wizard to configure providers, memory, and observability. Creates `~/.agent/settings.json`.

### Management Commands

```bash
agent config show              # View current configuration
agent config provider openai   # Enable/configure provider
agent config memory            # Configure memory backend
```

### Settings File Structure

**Location:** `~/.agent/settings.json`

**Minimal example:**
```json
{
  "version": "1.0",
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "api_key": "sk-...",
      "model": "gpt-5-mini"
    }
  }
}
```

**Features:**
- Progressive disclosure (only shows configured providers)
- Type-safe validation via Pydantic models
- Human-readable and git-friendly

## Environment Variables

### When to Use

- **CI/CD pipelines** - No settings.json file in repo
- **Docker/Kubernetes** - Container configuration
- **Runtime overrides** - Temporary testing different models
- **Secrets management** - API keys from vault/secrets manager

### Provider Selection

| Variable | Values | Description |
|----------|--------|-------------|
| `LLM_PROVIDER` | `local`, `openai`, `anthropic`, `azure`, `foundry`, `gemini`, `github` | Active provider |
| `AGENT_MODEL` | Model name | Override default model for any provider |

### Provider Credentials

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| **OpenAI** | `OPENAI_API_KEY` | Required |
| **Anthropic** | `ANTHROPIC_API_KEY` | Required |
| **Gemini** | `GEMINI_API_KEY` | Required (or use Vertex AI) |
| **GitHub** | `GITHUB_TOKEN` | Optional (uses `gh auth` if not set) |
| **Azure** | `AZURE_OPENAI_API_KEY` | Optional (uses `az login` if not set) |
| **Local** | None | No credentials needed |

### Azure Provider Configuration

| Variable | Description | Provider |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Resource endpoint URL | Azure OpenAI |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Deployment name | Azure OpenAI |
| `AZURE_OPENAI_API_VERSION` | API version (default: 2025-03-01-preview) | Azure OpenAI |
| `AZURE_PROJECT_ENDPOINT` | Project endpoint URL | Azure AI Foundry |
| `AZURE_MODEL_DEPLOYMENT` | Model deployment name | Azure AI Foundry |

### Gemini Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | API key | Yes (API mode) |
| `GEMINI_USE_VERTEXAI` | Use Vertex AI (`true`/`false`) | No |
| `GEMINI_PROJECT_ID` | GCP project ID | Yes (Vertex AI) |
| `GEMINI_LOCATION` | GCP region | Yes (Vertex AI) |

### Agent Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_DATA_DIR` | `~/.agent` | Data directory for sessions and memory |
| `LOG_LEVEL` | `info` | Logging level (`info`, `debug`, `trace`) |

**Note:** `LOG_LEVEL=trace` enables detailed LLM request/response logging with token counts in `~/.agent/logs/session-{name}-trace.log`.

### Memory Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_ENABLED` | `true` | Enable conversation memory |
| `MEMORY_TYPE` | `in_memory` | Memory backend (`in_memory`, `mem0`) |
| `MEMORY_HISTORY_LIMIT` | `20` | Number of messages to retain |
| `MEM0_STORAGE_PATH` | None | Chroma DB path (if using mem0) |

### Observability Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_OTEL` | `false` | Enable OpenTelemetry tracing |
| `ENABLE_SENSITIVE_DATA` | `false` | Include prompts/responses in logs |
| `OTLP_ENDPOINT` | `http://localhost:4317` | Telemetry export endpoint |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | None | Azure Application Insights connection |

### Filesystem Tools Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKSPACE_ROOT` | Current directory | Root directory for file operations |
| `FILESYSTEM_WRITES_ENABLED` | `false` | Enable write operations (safety) |
| `FILESYSTEM_MAX_READ_BYTES` | `10485760` | Max file read size (10MB) |
| `FILESYSTEM_MAX_WRITE_BYTES` | `1048576` | Max file write size (1MB) |

## Configuration Patterns

### Local Development

Use `agent config init` to create `settings.json`. No environment variables needed.

### CI/CD Deployment

Set environment variables only. No settings.json file.

**Minimal CI/CD setup:**
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
agent -p "Run analysis"
```

### Hybrid Configuration

Combine settings.json for base config with environment variables for runtime overrides:

```json
// settings.json - base configuration
{
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "model": "gpt-5-mini"
    }
  }
}
```

```bash
# Override at runtime for testing
export AGENT_MODEL=gpt-4o
export OPENAI_API_KEY=sk-different-key
agent
```

## See Also

- [README.md](../../README.md) - Quick start and setup
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development configuration
- [architecture.md](architecture.md) - System architecture
- [ADR-0020](../decisions/0020-legacy-config-deprecation-plan.md) - Legacy config deprecation
