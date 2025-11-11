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
agent --continue         # Resume last session
```

### Interactive Commands

```
/help                    # Show help
/clear                   # Clear conversation context
/continue                # Select previous session
/purge                   # Delete all agent data
/telemetry start/stop    # Start Open Telemetry
!command                 # Execute shell command
exit                     # Quit
```

### Keyboard Shortcuts

```
ESC                      # Clear current prompt (before pressing Enter)
Ctrl+C                   # Interrupt running operation (after pressing Enter)
Ctrl+D                   # Exit interactive mode
↑/↓                      # Navigate command history
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
  ◉ Anthropic (claude-haiku-4-5-20251001) · ****yEPQAA
  ○ Azure OpenAI - Not configured
  ○ Azure AI Foundry - Not configured
  ○ Google Gemini - Not configured
```

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

Delete all agent data:

```bash
> /purge
⚠ This will delete ALL agent data (7 sessions, memory files, log files, metadata).
Continue? (y/n): y

Delete 7 sessions?
  (y/n): y
  ✓ Deleted 7 sessions

Delete memory files?
  (y/n): y
  ✓ Deleted memory files

Delete log files?
  (y/n): y
  ✓ Deleted log files

Delete metadata (last_session, command history)?
  (y/n): y
  ✓ Deleted metadata

✓ Purge complete
```

## Execution Modes

### Default Mode

Shows completion summary with timing:

```bash
$ agent -p "say hello"

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

### Persistent Configuration

Add to your `.env` file:

```bash
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1    # Default DMR endpoint
AGENT_MODEL=ai/qwen3                                          # Recommended for tool calling
```
