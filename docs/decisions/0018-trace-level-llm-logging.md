---
status: accepted
contact: danielscholl
date: 2025-11-20
deciders: danielscholl
---

# Trace-Level LLM Request/Response Logging

## Context and Problem Statement

While Agent Base provides excellent observability through OpenTelemetry integration (ADR-0014), developers need complementary capabilities for offline analysis and session-based debugging. Current limitations include:

- **Offline Analysis**: Cannot review LLM interactions without running observability infrastructure
- **Session-Based Debugging**: No way to examine specific conversation traces alongside saved sessions
- **Token Optimization**: Difficult to analyze exact token usage patterns to reduce costs
- **Development Workflow**: Requires dashboard setup for quick access to request/response data
- **Historical Analysis**: Telemetry retention windows may not preserve long-term traces

How can we provide developers with persistent, human-readable trace logs of LLM interactions without duplicating or replacing OpenTelemetry?

## Decision Drivers

- **Complementary to OpenTelemetry**: Enhance, not replace, existing observability
- **Session-Specific**: Trace logs should align with session persistence lifecycle
- **Developer-Friendly**: Human-readable JSON format for easy parsing and analysis
- **Security-First**: Follow existing `ENABLE_SENSITIVE_DATA` patterns
- **Optional**: Zero impact when disabled, minimal overhead when enabled
- **Token Visibility**: Capture input/output/total token counts for cost analysis
- **Offline Access**: Persistent trace logs independent of external infrastructure

## Considered Options

1. **Enhance OpenTelemetry Export** - Extend OTEL to write local files
2. **Session-Specific Trace Logs** - Create separate trace log files per session
3. **Unified Debug Log** - Add trace data to existing session log files
4. **Database-Backed Traces** - Store traces in SQLite database
5. **No Trace Logging** - Rely exclusively on OpenTelemetry

## Decision Outcome

Chosen option: **"Session-Specific Trace Logs"**, because:

- **Clean Separation**: Keeps operational logs and trace data separate
- **Session Alignment**: Trace logs follow session persistence lifecycle
- **Easy Analysis**: Structured JSON per line enables streaming parsers and jq
- **Storage Efficiency**: Session-specific files keep traces manageable
- **Developer Workflow**: Can analyze traces without running dashboards
- **Pattern Consistency**: Follows existing session management patterns (ADR-0011)

### Implementation Details

**Architecture:**

1. **TraceLogger Class** (`src/agent/trace_logger.py`):
   - Core utility for structured JSON logging
   - Methods: `log_interaction()`, `log_request()`, `log_response()`
   - Handles file creation, JSON serialization, error handling
   - Respects `include_messages` configuration for content capture

2. **Configuration Integration**:
   - Uses existing `LOG_LEVEL` environment variable (set to `trace`)
   - Uses existing `ENABLE_SENSITIVE_DATA` for message content inclusion
   - No separate configuration schema needed - follows standard logging patterns

3. **Middleware Integration** (`src/agent/middleware.py`):
   - Enhanced `agent_run_logging_middleware` with trace logging
   - Global `_trace_logger` instance set by session setup
   - Logs request data before LLM call with unique request_id
   - Logs response data with token usage and latency after LLM call
   - Handles errors with partial trace logging

4. **Session Management** (`src/agent/cli/session.py`):
   - `setup_session_logging()`: Creates trace logger when enabled
   - Trace log file: `~/.agent/logs/session-{name}-trace.log`
   - `auto_save_session()`: Copies trace log to session directory
   - Trace logs included in session persistence lifecycle

**Configuration:**

```bash
# Enable trace logging (uses standard log level)
export LOG_LEVEL=trace

# Optional: Include full request/response messages
export ENABLE_SENSITIVE_DATA=true

# Run agent
agent -p "Say hello"

# View trace logs
cat ~/.agent/logs/session-*-trace.log | jq .
```

**Design Simplification**: Trace logging uses the standard `LOG_LEVEL` environment variable instead of separate configuration. When `LOG_LEVEL=trace`, trace log files are automatically created. Message content inclusion follows the existing `ENABLE_SENSITIVE_DATA` pattern for consistency.

**Trace Log Format:**

Each line is a JSON object. **Request entries** (when `ENABLE_SENSITIVE_DATA=true`):

```json
{
  "timestamp": "2025-11-20T10:30:45.123456",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "request",
  "model": "claude-sonnet-4-5",
  "provider": "anthropic",
  "message_count": 5,
  "messages": [{"role": "user", "contents": [...]}],
  "system_instructions": "Full system prompt text...",
  "system_instructions_length": 21435,
  "system_instructions_tokens_est": 5358,
  "tools": {
    "count": 14,
    "tools": [{"name": "tool1", "description": "...", "estimated_tokens": 150}],
    "total_estimated_tokens": 2491
  }
}
```

**Response entries:**

```json
{
  "timestamp": "2025-11-20T10:30:45.123456",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "response",
  "model": "claude-sonnet-4-5",
  "response": "Full response text...",
  "tokens": {
    "input": 8662,
    "output": 121,
    "total": 8783
  },
  "latency_ms": 1842.56
}
```

**Enhanced Fields** (when `ENABLE_SENSITIVE_DATA=true`):
- `system_instructions`: Complete system prompt sent to LLM
- `system_instructions_length`: Character count
- `system_instructions_tokens_est`: Estimated token count (chars / 4)
- `tools`: Per-tool breakdown with names, descriptions, and token estimates
- `tools.total_estimated_tokens`: Sum of all tool definition tokens

**Token Extraction:**

The middleware extracts token counts from LLM responses using provider-agnostic attribute access:

```python
if hasattr(context.response, "usage"):
    usage = context.response.usage
    if hasattr(usage, "input_tokens"):
        input_tokens = usage.input_tokens
    # ... similar for output_tokens, total_tokens
```

This handles different response formats across providers (OpenAI, Anthropic, Gemini, etc.).

## Positive Consequences

- **Offline Analysis**: Developers can analyze LLM interactions without external infrastructure
- **Session Debugging**: Trace logs persist alongside conversation sessions
- **Token Optimization**: Easy to identify high-token requests and optimize prompts
- **Cost Analysis**: Track token usage trends over time for budget planning
- **Development Speed**: Quick access to request/response data during development
- **Historical Record**: Persistent traces beyond telemetry retention windows
- **Parsing Friendly**: JSON-per-line format works with jq, Python, and streaming parsers

## Negative Consequences

- **Storage Usage**: Trace logs consume disk space (mitigated by session-specific files)
- **Maintenance Overhead**: Additional code to maintain and test
- **Configuration Complexity**: Another set of environment variables to document
- **Potential Confusion**: Users might think it replaces OpenTelemetry (clarify in docs)

## Compliance

### Security and Privacy

- **Sensitive Data Toggle**: `TRACE_INCLUDE_MESSAGES` requires `ENABLE_SENSITIVE_DATA=true`
- **Content Capture**: By default, only metadata (tokens, timing) is logged
- **Opt-In Model**: Full message content is opt-in, matching OTEL patterns (ADR-0014)
- **Local Storage**: Trace logs stay on developer's machine (no cloud upload)

### Performance Impact

- **Minimal Overhead**: Async file I/O, non-blocking writes
- **Conditional Execution**: Trace logging code only runs when enabled
- **JSON Streaming**: One JSON object per line, no buffering
- **Target: <5% latency increase** when trace logging enabled

## Related Decisions

- **ADR-0014 (Observability Integration)**: Trace logging complements OpenTelemetry
  - OTEL provides real-time dashboards and metrics
  - Trace logs provide offline analysis and historical records
  - Both can be enabled simultaneously for comprehensive observability

- **ADR-0011 (Session Management Architecture)**: Trace logs follow session lifecycle
  - Session-specific trace files align with session persistence
  - Trace logs copied to session directory during auto-save
  - Included in session metadata for discovery

- **ADR-0012 (Middleware Integration Strategy)**: Trace logging uses middleware patterns
  - Minimal invasiveness to existing middleware chain
  - Conditional instrumentation when trace logging enabled
  - Follows middleware best practices for context access

## Implementation Notes

### File Structure

```
~/.agent/
├── logs/
│   ├── session-2025-11-20-10-30-45.log         # Standard log
│   └── session-2025-11-20-10-30-45-trace.log   # Trace log
└── sessions/
    └── 2025-11-20-10-30-45/
        ├── thread.json                          # Session data
        ├── 2025-11-20-10-30-45-trace.log       # Trace log copy
        └── metadata.json                        # Session metadata
```

### Token Usage Analysis Example

```bash
# Extract token counts from trace logs
cat ~/.agent/logs/session-*-trace.log | \
  jq -r 'select(.tokens) | [.timestamp, .tokens.total] | @csv'

# Calculate total tokens used
cat ~/.agent/logs/session-*-trace.log | \
  jq -s 'map(select(.tokens)) | map(.tokens.total) | add'

# Find high-token requests
cat ~/.agent/logs/session-*-trace.log | \
  jq 'select(.tokens.input > 5000) | {timestamp, model, input_tokens: .tokens.input}'
```

### Future Enhancements

- **Trace Log Rotation**: Size or time-based rotation for long-running sessions
- **Trace Log Aggregation**: CLI command to merge traces across sessions
- **Analysis Tools**: Built-in CLI commands for token analysis (`agent trace analyze`)
- **Export Formats**: CSV or Excel export for non-technical stakeholders
- **Cost Calculator**: Integration with provider pricing for cost estimates
- **Visual Trace Viewer**: Web UI or TUI for interactive trace exploration

## References

- [OpenTelemetry GenAI Semantic Conventions](https://github.com/open-telemetry/semantic-conventions/tree/main/docs/gen-ai)
- [Specification: Trace-Level LLM Logging](../specs/trace-level-llm-logging.md)
- [ADR-0014: Observability Integration](./0014-observability-integration.md)
- [ADR-0011: Session Management Architecture](./0011-session-management-architecture.md)
- [ADR-0012: Middleware Integration Strategy](./0012-middleware-integration-strategy.md)
