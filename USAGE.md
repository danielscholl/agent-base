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
