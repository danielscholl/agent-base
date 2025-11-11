# Usage Guide

Complete reference for Agent Base features and workflows.

## Command Reference

### CLI Commands

```bash
agent                    # Interactive mode
agent --help             # Display help
agent --check            # Show configuration and connectivity
agent -p "prompt"        # Single query
agent --verbose          # Show execution details
agent --quiet            # Minimal output
agent --continue         # Resume last session
```

### Interactive Commands

```
/help                    # Show help
/clear                   # Clear conversation context
/continue                # Select previous session
/purge                   # Delete all sessions
!command                 # Execute shell command
exit                     # Quit
```

### Keyboard Shortcuts

```
ESC                      # Clear prompt
Ctrl+D                   # Exit
Ctrl+C                   # Interrupt
↑/↓                      # Command history
```

## Getting Started

### Verify Configuration

Before using the agent, verify your setup:

```bash
$ agent --check

System:
  ◉ Python 3.12.10
  ◉ Platform: macOS-26.1-arm64-arm-64bit
  ◉ Data: /Users/johndoe/.agent

Agent:
  ◉ Log Level: INFO
  ◉ System Prompt: Default

Docker:
  ◉ Running (28.5.1) · 10 cores, 15.4 GiB

LLM Providers:
✓ ◉ OpenAI (gpt-5-mini) · ****R02TAA
  ◉ Anthropic (claude-sonnet-4-5-20250929) · ****yEPQAA
  ○ Azure OpenAI - Not configured
  ○ Azure AI Foundry - Not configured
  ○ Google Gemini - Not configured
```

The unified `--check` command shows:
- System information and data directory
- Agent settings (log level, system prompt)
- Docker status and resources
- All LLM providers with connectivity tests
- Green ✓ indicates active provider

**If you see issues:**
- Missing credentials → Edit `.env` file
- Azure providers → Run `az login`
- Docker not running → Start Docker Desktop

### First Run

Once configuration is verified, start an interactive session:

```bash
$ agent

Agent - Conversational Assistant
Version 0.1.0 • OpenAI/gpt-5-mini

 ~/project [⎇ main]                              OpenAI/gpt-5-mini · v0.1.0
────────────────────────────────────────────────────────────────────────

> Say hello to Alice

● Thinking...

Hello, Alice! ◉‿◉

────────────────────────────────────────────────────────────────────────

> exit
Session auto-saved as '2025-11-10-11-38-07'

Goodbye!
```

### Single Query Mode

Execute one prompt and exit:

```bash
$ agent -p "say hello to Alice"

● Thinking...

Hello, Alice!
```



## Session Management

Sessions save automatically when you exit:

```bash
$ agent
> say hello
> exit
Session auto-saved as '2025-11-08-11-15-30'
```

Resume the most recent session:

```bash
$ agent --continue
✓ Loaded '2025-11-08-11-15-30' (2 messages)
```

Select from saved sessions:

```bash
$ agent
> /continue

Available Sessions:
  1. 2025-11-08-11-15-30 (5m ago) "say hello"
  2. 2025-11-08-10-30-45 (1h ago) "greet Alice"

Select session [1-2]: 1
✓ Loaded '2025-11-08-11-15-30' (2 messages)
```

Clear context without exiting:

```bash
> /clear
```

Delete all sessions:

```bash
> /purge
⚠ This will delete ALL 5 saved sessions.
Continue? (y/n): y
✓ Deleted 5 sessions
```

## Execution Modes

### Default Mode

Shows completion summary with timing:

```bash
$ agent -p "say hello"
✓ Complete (2.0s) - msg:1 tool:1

Hello, World!
```

### Verbose Mode

Shows full execution tree:

```bash
$ agent -p "say hello to Alice" --verbose

• Phase 1: hello_world (6.1s)
├── • Thinking (1 messages) - Response received (6.2s)
└── • → hello_world (Alice) - Complete (0.0s)

Hello, Alice!
```

### Quiet Mode

Response only, no metadata:

```bash
$ agent -p "say hello" --quiet
Hello, World!
```

## Using Local Models with Docker

Run agent-base completely offline using Docker Desktop's model serving:

### Setup

```bash
# 1. Install Docker Desktop (includes Model Runner)
# Download from https://www.docker.com/products/docker-desktop/

# 2. Enable Model Runner with TCP support
docker desktop enable model-runner --tcp=12434

# 3. Pull a model (Qwen3 recommended for best tool calling)
docker model pull ai/qwen3
# Alternative: docker model pull ai/phi4

# 4. Verify model is available and note the model ID
curl http://localhost:12434/engines/llama.cpp/v1/models
# Returns: {"object":"list","data":[{"id":"ai/qwen3:latest",...}]}

# 5. Configure agent-base (use full model ID from step 4)
export LLM_PROVIDER=local
export AGENT_MODEL=ai/qwen3

# 6. Run agent
agent
```

### Configuration

Add to your `.env` file:

```bash
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1  # Default DMR endpoint
AGENT_MODEL=ai/qwen3                                         # Recommended for tool calling
# Alternative: AGENT_MODEL=ai/phi4                            # General purpose
```

### Benefits

- **No API costs** - Completely free to run
- **Offline operation** - Works without internet
- **Data privacy** - All data stays on your machine
- **Fast iteration** - No network latency

### Limitations

- Requires Docker Desktop with Model Runner enabled
- Requires sufficient RAM (8GB+ recommended)
- Model quality varies (phi4 is capable but not GPT-4 level)
- Function calling support depends on model
- First run downloads large model files (~5GB+ per model)
- TCP support must be enabled: `docker desktop enable model-runner --tcp 12434`

### Supported Models

Docker Desktop supports various models via `docker model pull`:

- **qwen3** - Qwen 3 (8B/14B parameters) - **RECOMMENDED for tool calling** - Use `ai/qwen3` in config
- **phi4** - Microsoft's phi-4 model (14B parameters) - Good general purpose - Use `ai/phi4` in config
- **llama3.2** - Meta's Llama 3.2 (very capable) - Use `ai/llama3.2` in config
- **mistral** - Mistral AI (strong multilingual support) - Use `ai/mistral` in config
- **codellama** - Meta's Code Llama (optimized for code) - Use `ai/codellama` in config

**Model Selection for Tool Calling**: According to [Docker's evaluation](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/), Qwen 3 (8B or 14B) provides the best tool-calling accuracy among local models. Use `ai/qwen3` for maximum tool calling reliability.

**Important**: When configuring `AGENT_MODEL`, use the full model ID format (e.g., `ai/qwen3`, not just `qwen3`). Check available models with:
```bash
curl http://localhost:12434/engines/llama.cpp/v1/models
```

### Example Session

```bash
$ export LLM_PROVIDER=local
$ export AGENT_MODEL=ai/qwen3
$ agent --check

LLM Providers:
✓ ◉ Local (ai/qwen3) · http://localhost:12434/engines/llama.cpp/v1

$ agent

Agent - Conversational Assistant
Version 0.1.0 • Local/ai/qwen3

> Say hello to Alice

● Thinking...

Hello, Alice! ◉‿◉  ← Tool was called (notice the ◉‿◉ emoji from hello_world tool)

> exit
Session auto-saved

Goodbye!
```
