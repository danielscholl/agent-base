# Usage Guide

Comprehensive guide for using the Agent Template.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Configuration](#configuration)
3. [Command Reference](#command-reference)
4. [Examples](#examples)
5. [Troubleshooting](#troubleshooting)

## Basic Usage

### Single Prompt Mode

The simplest way to use the agent is with a single prompt:

```bash
uv run agent -p "your prompt here"
```

This will:
1. Load configuration from environment
2. Initialize the agent with configured LLM provider
3. Execute the prompt
4. Display the response
5. Exit

**Example:**
```bash
uv run agent -p "Say hello to Alice"
```

### Interactive Mode

Interactive mode is not yet implemented in the MVP. Use single-prompt mode for now.

### Output Modes

The agent supports different verbosity levels (planned for Phase 3):

- **Default**: Summary with timing information
- **Quiet** (`-q`): Minimal output, response only
- **Verbose** (`-v`): Full execution tree with tool calls

## Configuration

### Environment Variables

The agent uses environment variables for configuration. Create a `.env` file in the project root:

```bash
cp .env.example .env
```

#### LLM Provider Configuration

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `LLM_PROVIDER` | Yes | LLM provider to use | `openai`, `anthropic`, `azure_ai_foundry` |

#### OpenAI Configuration (when `LLM_PROVIDER=openai`)

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | Yes | OpenAI API key | - |
| `OPENAI_MODEL` | No | Model to use | `gpt-4o` |

#### Anthropic Configuration (when `LLM_PROVIDER=anthropic`)

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key | - |
| `ANTHROPIC_MODEL` | No | Model to use | `claude-sonnet-4-5-20250929` |

#### Azure AI Foundry Configuration (when `LLM_PROVIDER=azure_ai_foundry`)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_PROJECT_ENDPOINT` | Yes | Azure AI project endpoint | `https://your-project.services.ai.azure.com/api/projects/your-project-id` |
| `AZURE_MODEL_DEPLOYMENT` | Yes | Model deployment name | `gpt-4o` |

**Note**: Azure AI Foundry uses `AzureCliCredential` for authentication. You must be logged in via `az login`.

#### Agent Settings

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `AGENT_DATA_DIR` | No | Data directory for sessions | `~/.agent` |
| `LOG_LEVEL` | No | Logging level | `info` |

### Provider Setup

#### OpenAI Setup

1. Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set environment variables:
   ```bash
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-...your-key...
   OPENAI_MODEL=gpt-4o  # Optional, this is the default
   ```

#### Anthropic Setup

1. Get API key from [Anthropic Console](https://console.anthropic.com/)
2. Set environment variables:
   ```bash
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-...your-key...
   ANTHROPIC_MODEL=claude-sonnet-4-5-20250929  # Optional, this is the default
   ```

#### Azure AI Foundry Setup

1. Create Azure AI project in [Azure Portal](https://portal.azure.com/)
2. Deploy a model to your project
3. Login with Azure CLI:
   ```bash
   az login
   ```
4. Set environment variables:
   ```bash
   LLM_PROVIDER=azure_ai_foundry
   AZURE_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project-id
   AZURE_MODEL_DEPLOYMENT=gpt-4o
   ```

## Command Reference

### CLI Arguments

```bash
agent [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-p, --prompt TEXT` | Execute a single prompt and exit |
| `--check` | Run health check for dependencies and configuration |
| `--config` | Show current configuration |
| `--version` | Show version number |
| `-h, --help` | Show help message |

### Interactive Commands (Future)

Interactive mode will support the following commands:

- `/help` - Show available commands
- `/exit` or `/quit` - Exit interactive mode
- `/clear` - Clear screen
- `/config` - Show configuration
- `/session` - Session management

## Examples

### Example 1: Basic Hello World

```bash
uv run agent -p "Say hello"
```

**Expected output:**
```
User: Say hello

Agent: Hello! How can I assist you today?
```

### Example 2: Using HelloTools

```bash
uv run agent -p "Say hello to Bob"
```

The agent will use the `hello_world` tool to generate a personalized greeting.

### Example 3: Multi-language Greeting

```bash
uv run agent -p "Greet Alice in Spanish"
```

The agent will use the `greet_user` tool with the Spanish language option.

### Example 4: Configuration Check

```bash
uv run agent --check
```

**Expected output:**
```
✓ Configuration valid
  Provider: openai
  Model: OpenAI/gpt-4o
```

### Example 5: Show Configuration

```bash
uv run agent --config
```

**Expected output:**
```
Agent Configuration

LLM Provider:
 • Provider: openai
 • Model: gpt-4o
 • API Key: ****abc123 (last 6 chars)

Agent Settings:
 • Data Directory: ~/.agent
 • Session Directory: ~/.agent/sessions
 • Log Level: info
```

## Troubleshooting

### Common Issues

#### Issue: "Configuration validation failed"

**Symptom:**
```
Error: Configuration validation failed
Missing required environment variable: OPENAI_API_KEY
```

**Solution:**
1. Ensure `.env` file exists in project root
2. Verify `LLM_PROVIDER` is set correctly
3. Verify provider-specific API keys are set
4. Run `uv run agent --check` to diagnose

#### Issue: "Unknown LLM provider"

**Symptom:**
```
Error: Unknown LLM provider: azure
```

**Solution:**
- Valid providers are: `openai`, `anthropic`, `azure_ai_foundry`
- Check spelling in `LLM_PROVIDER` environment variable

#### Issue: "Azure authentication failed"

**Symptom:**
```
Error: Azure authentication failed
```

**Solution:**
1. Ensure you're logged in: `az login`
2. Verify your account has access to the Azure AI project
3. Check `AZURE_PROJECT_ENDPOINT` is correct

#### Issue: "Module 'agent' has no attribute 'Agent'"

**Symptom:**
```
ImportError: cannot import name 'Agent' from 'agent'
```

**Solution:**
1. Ensure dependencies are installed: `uv sync`
2. Verify you're using Python 3.12+: `python --version`
3. Check package is installed correctly: `uv run python -c "import agent; print(agent.__version__)"`

### Debug Mode

To enable verbose logging for debugging:

```bash
LOG_LEVEL=debug uv run agent -p "your prompt"
```

This will show detailed information about:
- Configuration loading
- LLM provider initialization
- Tool registration
- Request/response cycles

### Getting Help

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/danielscholl/agent-template/issues)
2. Review the [Architecture Documentation](docs/architecture/tool-architecture.md)
3. Create a new issue with:
   - Your environment (OS, Python version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs (with sensitive data removed)

## Performance Tips

1. **Use appropriate models**: `gpt-4o` is faster than `gpt-4`, `claude-sonnet` is faster than `claude-opus`
2. **Minimize tool complexity**: Keep tool functions simple and focused
3. **Cache when possible**: Future versions will support caching for expensive operations

## Security Considerations

1. **Never commit `.env` file**: Contains sensitive API keys
2. **Use environment variables**: Don't hardcode credentials
3. **Rotate keys regularly**: If keys are compromised, rotate immediately
4. **Review tool permissions**: Ensure tools only have necessary access
5. **Monitor usage**: Track API usage to detect anomalies
