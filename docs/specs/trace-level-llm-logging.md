# Feature: Trace-Level LLM Request/Response Logging

## Feature Description

Add comprehensive trace-level logging to capture detailed LLM request/response data with token counts in session-specific trace logs. This feature enables detailed analysis and optimization of LLM interactions by providing granular visibility into what data is sent to and received from language models.

When `AGENT_LOG_LEVEL=trace` is set, the agent will create a separate trace log file (`~/.agent/logs/session-{name}-trace.log`) that captures:
- Complete request messages (with message count)
- Complete response content
- Token usage (input tokens, output tokens, total tokens)
- Response latency and timing
- Model information
- Structured JSON format for easy parsing and analysis

This complements the existing OpenTelemetry observability (ADR-0014) by providing human-readable, session-specific trace logs that persist alongside conversation threads for offline analysis and debugging.

## User Story

**As a** developer optimizing agent performance
**I want to** capture detailed LLM request/response data with token counts at trace level
**So that** I can analyze token usage patterns, identify optimization opportunities, and debug conversation flows without relying on external observability platforms

## Problem Statement

Currently, agent-base provides excellent observability through OpenTelemetry integration (ADR-0014), which sends telemetry to external platforms like Azure Application Insights or Aspire Dashboard. However, there are scenarios where developers need:

1. **Offline analysis**: Reviewing LLM interactions without running observability infrastructure
2. **Session-based debugging**: Examining specific conversation traces alongside saved sessions
3. **Token optimization**: Analyzing exact token usage patterns to reduce costs
4. **Development workflow**: Quick access to request/response data without dashboard setup
5. **Historical analysis**: Persistent trace logs that survive beyond telemetry retention windows

The current logging infrastructure (`AGENT_LOG_LEVEL=debug`) provides some information but lacks:
- Complete request/response content capture
- Token count extraction from LLM responses
- Structured format for parsing and analysis
- Session-specific trace log files

## Solution Statement

Implement a trace-level logging feature that:

1. **Extends existing log levels** - Add `trace` as a new log level (more verbose than `debug`)
2. **Creates session-specific trace logs** - Generate `session-{name}-trace.log` files alongside existing session logs
3. **Captures LLM interactions** - Log complete request/response data in structured JSON format
4. **Extracts token counts** - Parse and log input/output token usage from LLM responses
5. **Maintains structure** - Use existing patterns from session persistence and middleware
6. **Remains optional** - Only active when `LOG_LEVEL=trace` is explicitly set
7. **Preserves security** - Follows existing `ENABLE_SENSITIVE_DATA` patterns for content capture

The solution integrates with:
- Existing middleware (`agent_run_logging_middleware` in src/agent/middleware.py:36-90)
- Session management (`setup_session_logging()` in src/agent/cli/session.py:19-73)
- Configuration patterns (`AgentConfig` in src/agent/config/schema.py)
- Persistence layer (`ThreadPersistence` in src/agent/persistence.py)

## Related Documentation

### Requirements
- [docs/design/architecture.md](../design/architecture.md) - Middleware and event-driven patterns
- [docs/design/requirements.md](../design/requirements.md) - Base requirements

### Architecture Decisions
- [ADR-0014: Observability Integration](../decisions/0014-observability-integration.md) - OpenTelemetry patterns and sensitive data handling
- [ADR-0012: Middleware Integration Strategy](../decisions/0012-middleware-integration-strategy.md) - Middleware lifecycle and interception
- [ADR-0011: Session Management Architecture](../decisions/0011-session-management-architecture.md) - Session persistence patterns

## Codebase Analysis Findings

### Architecture Patterns to Follow

**1. Session-Specific Logging Pattern** (src/agent/cli/session.py:19-73):
```python
def setup_session_logging(session_name: str | None = None, config: AgentConfig | None = None) -> str:
    """Setup session-specific logging to file (not console)."""
    log_dir = Path.home() / ".agent" / "logs"
    log_file = log_dir / f"session-{session_name}.log"
```
- File-only logging (no console output to avoid UI pollution)
- Session-specific log files with sanitized names

**2. Middleware Interception Pattern** (src/agent/middleware.py:36-90):
```python
async def agent_run_logging_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Log agent execution lifecycle and emit LLM request/response events."""
    # Before LLM call
    logger.debug("Agent run starting...")
    start_time = time.time()

    await next(context)  # LLM call happens here

    duration = time.time() - start_time
    # After LLM call
    logger.debug(f"Agent run completed in {duration:.2f}s")
```
- Middleware wraps LLM calls with timing
- Access to both request (`context.messages`) and response data
- Integration point for trace logging

**3. Configuration Schema Pattern** (src/agent/config/schema.py:224-231):
```python
class TelemetryConfig(BaseModel):
    """Telemetry and observability configuration."""
    enabled: bool = False
    enable_sensitive_data: bool = False
```
- Pydantic models for type-safe configuration
- Boolean flags for feature enablement
- Environment variable loading through `from_env()`

**4. File Persistence Pattern** (src/agent/persistence.py:339-356):
```python
# Security-first approach
safe_name = _sanitize_conversation_name(name)

# JSON serialization with indent
with open(file_path, "w") as f:
    json.dump(conversation_data, f, indent=2)
```
- Name sanitization for security
- JSON with indentation for readability
- Atomic file writes

### Naming Conventions

- **Log files**: `session-{name}-trace.log` (follows existing `session-{name}.log` pattern)
- **Config fields**: `enable_trace_logging`, `trace_log_level` (snake_case)
- **Functions**: `setup_trace_logger()`, `log_llm_trace()` (snake_case, verb_noun pattern)
- **Classes**: `TraceLogger` (PascalCase)

### Similar Implementations

**Session Persistence** (src/agent/persistence.py:246-356):
- Template for creating session-specific files
- Metadata tracking pattern
- Security sanitization approach

**OpenTelemetry Integration** (src/agent/observability.py):
- Conditional feature enablement pattern
- Token count extraction (though not currently used in logging)
- Sensitive data toggle pattern

### Integration Patterns

**Middleware Enhancement**:
- Add trace logging to existing `agent_run_logging_middleware`
- Extract token counts from `context.response` after `await next(context)`
- Use separate logger for trace output to avoid mixing with standard logs

**Configuration Integration**:
- Add `TraceLoggingConfig` to schema.py
- Load from environment variables (`ENABLE_TRACE_LOGGING`)
- Validate at startup in `AgentConfig.validate()`

**Session Integration**:
- Create trace log file in `setup_session_logging()`
- Include trace log in session auto-save
- List trace logs in session management commands

## Archon Project

**Project ID**: `8d51bf1e-3712-42c6-96ef-2e0dc360c90a`

Tasks will be created during implementation phase using `/sdlc:implement`.

## Relevant Files

### Existing Files

**Core Integration Points**:
- `src/agent/middleware.py` (lines 36-90) - Add trace logging to `agent_run_logging_middleware`
- `src/agent/cli/session.py` (lines 19-73) - Extend `setup_session_logging()` for trace logs
- `src/agent/config/schema.py` (lines 224-231) - Add `TraceLoggingConfig` to schema
- `src/agent/persistence.py` (lines 246-356) - Include trace logs in session persistence

**Supporting Files**:
- `src/agent/config/manager.py` - Configuration loading and validation
- `src/agent/config/legacy.py` (line 480) - Environment variable loading in `from_combined()`
- `src/agent/cli/session.py` (lines 76-154) - Session auto-save logic
- `.env.example` - Add trace logging environment variables

**Testing Infrastructure**:
- `tests/unit/middleware/test_middleware.py` - Add trace logging tests
- `tests/unit/cli/test_health_check_logging.py` - Pattern for logging tests
- `tests/unit/config/test_schema.py` - Configuration validation tests
- `tests/integration/test_session_persistence.py` - Session integration tests

### New Files

**Primary Implementation**:
- `src/agent/trace_logger.py` - TraceLogger class for structured trace logging
  - Purpose: Encapsulate trace logging logic with JSON formatting
  - Responsibilities: Create trace log files, format LLM data, extract token counts

**Testing**:
- `tests/unit/trace/__init__.py` - Test package initialization
- `tests/unit/trace/test_trace_logger.py` - Unit tests for TraceLogger class
- `tests/integration/test_trace_logging.py` - End-to-end trace logging tests

## Implementation Plan

### Phase 1: Foundation (Configuration and Core Logger)

**Goal**: Establish trace logging configuration and create the core TraceLogger utility.

1. **Add trace logging configuration to schema**
   - Extend `TelemetryConfig` or create `TraceLoggingConfig` in `src/agent/config/schema.py`
   - Add fields: `enable_trace_logging: bool`, `trace_include_messages: bool`
   - Add validation for trace level conflicts with OTEL sensitive data

2. **Create TraceLogger utility class**
   - New file: `src/agent/trace_logger.py`
   - Implement structured JSON logging for LLM interactions
   - Methods: `log_request()`, `log_response()`, `log_token_usage()`
   - Handle file creation, rotation considerations

3. **Update environment variable loading**
   - Modify `.env.example` to document trace logging variables
   - Add `ENABLE_TRACE_LOGGING`, `TRACE_INCLUDE_MESSAGES` variables
   - Update `from_combined()` in `src/agent/config/legacy.py` if needed

### Phase 2: Core Implementation (Middleware Integration)

**Goal**: Integrate trace logging into the LLM request/response pipeline.

1. **Extend middleware for trace logging**
   - Modify `agent_run_logging_middleware` in `src/agent/middleware.py`
   - Add trace logger initialization (conditional on config)
   - Log request data before `await next(context)`
   - Extract and log response data + tokens after LLM call

2. **Extract token usage from responses**
   - Access `context.response.usage` (or equivalent) in middleware
   - Handle different response formats from various providers
   - Parse input_tokens, output_tokens, total_tokens
   - Add fallback for providers that don't report tokens

3. **Format trace log entries**
   - Use TraceLogger to create structured JSON entries
   - Include: timestamp, request_id, messages (if enabled), tokens, latency
   - Ensure sensitive data respects existing `enable_sensitive_data` config

### Phase 3: Integration (Session Management)

**Goal**: Integrate trace logs into session lifecycle and persistence.

1. **Create trace logs in session setup**
   - Modify `setup_session_logging()` in `src/agent/cli/session.py`
   - Create `session-{name}-trace.log` file when trace level enabled
   - Configure trace logger with session-specific file path

2. **Include trace logs in session auto-save**
   - Modify `auto_save_session()` in `src/agent/cli/session.py` (lines 76-154)
   - Copy trace log file to session directory (if exists)
   - Update session metadata to include trace log reference

3. **Add trace log management commands**
   - Extend session list output to show trace log availability
   - Add option to view/export trace logs
   - Consider `agent session show <name> --trace` command

### Phase 4: Testing and Documentation

**Goal**: Comprehensive testing and clear documentation.

1. **Unit tests for TraceLogger**
   - Test JSON formatting
   - Test file creation and writing
   - Test token extraction logic
   - Test error handling

2. **Integration tests for middleware**
   - Test trace logging with mocked LLM responses
   - Verify trace log file creation
   - Validate JSON structure
   - Test with various providers (OpenAI, Anthropic, etc.)

3. **Update documentation**
   - Add usage section to README.md
   - Create ADR for trace logging design decisions
   - Update docs/design/usage.md with trace logging examples
   - Document trace log format and fields

## Step by Step Tasks

### Task 1: Add Trace Logging Configuration Schema
- **Description**: Extend configuration schema with trace logging settings
- **Files to modify**:
  - `src/agent/config/schema.py` (add TraceLoggingConfig)
  - `.env.example` (document new variables)
- **Archon task**: Will be created during implementation

### Task 2: Create TraceLogger Utility Class
- **Description**: Implement core TraceLogger class for structured JSON logging
- **Files to modify**:
  - `src/agent/trace_logger.py` (new file)
  - `src/agent/__init__.py` (export TraceLogger if needed)
- **Archon task**: Will be created during implementation

### Task 3: Integrate Trace Logging into Middleware
- **Description**: Add trace logging to agent_run_logging_middleware
- **Files to modify**:
  - `src/agent/middleware.py` (lines 36-90, enhance middleware)
- **Archon task**: Will be created during implementation

### Task 4: Extract Token Usage from LLM Responses
- **Description**: Parse token counts from various LLM provider responses
- **Files to modify**:
  - `src/agent/middleware.py` (add token extraction logic)
  - `src/agent/trace_logger.py` (add token formatting methods)
- **Archon task**: Will be created during implementation

### Task 5: Create Trace Logs in Session Setup
- **Description**: Modify session logging setup to create trace log files
- **Files to modify**:
  - `src/agent/cli/session.py` (lines 19-73, extend setup_session_logging)
- **Archon task**: Will be created during implementation

### Task 6: Include Trace Logs in Session Persistence
- **Description**: Save trace logs alongside session data
- **Files to modify**:
  - `src/agent/cli/session.py` (lines 76-154, modify auto_save_session)
  - `src/agent/persistence.py` (add trace log handling if needed)
- **Archon task**: Will be created during implementation

### Task 7: Write Unit Tests for TraceLogger
- **Description**: Create comprehensive unit tests for TraceLogger class
- **Files to modify**:
  - `tests/unit/trace/__init__.py` (new file)
  - `tests/unit/trace/test_trace_logger.py` (new file)
- **Archon task**: Will be created during implementation

### Task 8: Write Integration Tests for Trace Logging
- **Description**: End-to-end tests for trace logging with middleware
- **Files to modify**:
  - `tests/integration/test_trace_logging.py` (new file)
- **Archon task**: Will be created during implementation

### Task 9: Update Configuration Tests
- **Description**: Add tests for trace logging configuration validation
- **Files to modify**:
  - `tests/unit/config/test_schema.py` (add TraceLoggingConfig tests)
- **Archon task**: Will be created during implementation

### Task 10: Create ADR for Trace Logging
- **Description**: Document architectural decisions for trace logging feature
- **Files to modify**:
  - `docs/decisions/0018-trace-level-llm-logging.md` (new file)
- **Archon task**: Will be created during implementation

### Task 11: Update Documentation
- **Description**: Add usage examples and update user-facing documentation
- **Files to modify**:
  - `README.md` (add trace logging section)
  - `docs/design/usage.md` (add examples)
  - `CONTRIBUTING.md` (update if needed)
- **Archon task**: Will be created during implementation

## Testing Strategy

### Unit Tests

**TraceLogger Class** (`tests/unit/trace/test_trace_logger.py`):
- Test JSON formatting for requests and responses
- Test file creation and path handling
- Test token extraction from different response formats
- Test error handling for missing data
- Test sanitization and security features
- Mock file I/O to avoid filesystem dependencies

**Configuration** (`tests/unit/config/test_schema.py`):
- Test TraceLoggingConfig loading from environment
- Test validation of trace logging settings
- Test conflicts between trace and OTEL sensitive data
- Test default values and optional fields

**Middleware** (`tests/unit/middleware/test_middleware.py`):
- Test trace logging conditional activation
- Test request/response capture logic
- Test token extraction with mocked responses
- Test timing and latency calculation
- Use existing middleware test patterns

### Integration Tests

**End-to-End Trace Logging** (`tests/integration/test_trace_logging.py`):
- Test complete flow from config → middleware → trace log
- Test with MockChatClient (various response formats)
- Verify trace log file creation and content
- Test session persistence includes trace logs
- Test with different providers (OpenAI, Anthropic, Gemini)
- Validate JSON structure and completeness

**Session Integration** (`tests/integration/test_session_persistence.py`):
- Test trace log creation during session setup
- Test trace log included in auto-save
- Test trace log restoration with sessions
- Test session cleanup includes trace logs

### Edge Cases

**Configuration Edge Cases**:
- Both `AGENT_LOG_LEVEL=trace` and `ENABLE_TRACE_LOGGING=false` (precedence)
- Trace logging enabled but no session active
- Invalid log directory permissions
- Disk space exhaustion during trace logging

**Response Format Edge Cases**:
- LLM response missing token usage data
- Empty or null responses
- Streaming responses (chunked data)
- Error responses from LLM providers
- Timeout scenarios

**Session Management Edge Cases**:
- Session name with special characters (sanitization)
- Very long conversation traces (file size limits)
- Concurrent trace logging (multiple sessions)
- Session resume with existing trace log

**Provider-Specific Edge Cases**:
- Different token count field names across providers
- Providers that don't report token usage
- Gemini vs OpenAI vs Anthropic response format differences
- Local models with limited telemetry

### Performance Considerations

**Test Performance Impact**:
- Measure overhead of trace logging (target: <5% latency increase)
- Test with large message histories (100+ messages)
- Test trace log file growth over extended conversations
- Verify async I/O doesn't block LLM responses

## Acceptance Criteria

- [ ] Configuration schema includes trace logging settings
- [ ] `ENABLE_TRACE_LOGGING` and `AGENT_LOG_LEVEL=trace` environment variables work
- [ ] TraceLogger class successfully creates session-specific trace log files
- [ ] Trace logs capture complete LLM request data (when configured)
- [ ] Trace logs capture complete LLM response data
- [ ] Token counts (input, output, total) extracted and logged
- [ ] Response latency and timing information logged
- [ ] Model name and provider information included
- [ ] Structured JSON format for easy parsing
- [ ] Trace logging respects `ENABLE_SENSITIVE_DATA` configuration
- [ ] Trace logs included in session auto-save
- [ ] Session management commands show trace log availability
- [ ] Middleware integration doesn't affect normal operation when disabled
- [ ] Unit tests achieve >85% coverage for new code
- [ ] Integration tests validate end-to-end trace logging
- [ ] All existing tests pass without modification
- [ ] Documentation includes usage examples and trace log format
- [ ] ADR documents architectural decisions
- [ ] Performance overhead <5% when trace logging enabled

## Validation Commands

```bash
# 1. Run all tests (exclude LLM tests)
cd /Users/danielscholl/source/github/danielscholl/agent-base
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# 2. Run trace logging specific tests
uv run pytest tests/unit/trace/ -v
uv run pytest tests/integration/test_trace_logging.py -v

# 3. Run configuration tests
uv run pytest tests/unit/config/test_schema.py -v -k trace

# 4. Run middleware tests
uv run pytest tests/unit/middleware/test_middleware.py -v -k trace

# 5. Code quality checks
uv run black src/agent/ tests/
uv run ruff check --fix src/agent/ tests/
uv run mypy src/agent/

# 6. Manual verification
export LOG_LEVEL=trace
export ENABLE_TRACE_LOGGING=true
uv run agent -p "Say hello"
# Check for trace log file creation at ~/.agent/logs/

# 7. Verify trace log format
cat ~/.agent/logs/session-*-trace.log | jq .
# Should be valid JSON with request/response/tokens fields

# 8. Test with different providers
export AGENT_PROVIDER=openai
uv run agent -p "Test with OpenAI"

export AGENT_PROVIDER=anthropic
uv run agent -p "Test with Anthropic"

# 9. Integration with session persistence
uv run agent  # Start interactive mode
# Say hello
# exit
# Check that trace log is saved with session

# 10. Performance benchmark (optional)
uv run pytest tests/integration/test_trace_logging.py::test_performance_overhead -v
```

## Notes

### Design Decisions

**Why Separate Trace Log Files?**
- Keeps standard logs clean and focused on operational events
- Allows trace logs to be very verbose without cluttering debug logs
- Easier to parse and analyze structured LLM data separately
- Session-specific trace logs align with session persistence model

**Why JSON Format for Trace Logs?**
- Machine-readable for automated analysis and tooling
- Easy to parse with standard tools (jq, Python json module)
- Structured data enables token analysis and optimization scripts
- Follows existing patterns in session persistence

**Why Respect ENABLE_SENSITIVE_DATA?**
- Consistent with OpenTelemetry observability patterns (ADR-0014)
- Security-first approach: content capture is opt-in
- Allows basic trace logging (tokens, timing) without exposing prompts
- Clear separation between debugging and privacy concerns

### Future Considerations

**Potential Enhancements**:
- Trace log rotation (size or time-based)
- Trace log aggregation across sessions
- CLI command to analyze trace logs (`agent trace analyze`)
- Export trace logs to CSV or Excel for analysis
- Integration with token cost calculators
- Visual trace viewer (web UI or TUI)
- Trace log compression for long-term storage

**Performance Optimizations**:
- Async file I/O to avoid blocking LLM responses
- Buffered writes to reduce I/O operations
- Optional trace log sampling (e.g., every 10th request)
- Trace log level gradations (basic vs detailed)

**Integration Opportunities**:
- Export to OpenTelemetry Collector for unified observability
- Integration with token optimization tools
- Hooks for custom trace processors
- Trace log search and filtering CLI

### Related Work

**OpenTelemetry (ADR-0014)**:
- Trace logging complements OpenTelemetry, not replaces it
- OTEL provides real-time observability dashboard
- Trace logs provide offline analysis and historical records
- Both can be enabled simultaneously for comprehensive coverage

**Session Persistence (ADR-0011)**:
- Trace logs follow same lifecycle as session data
- Stored in session directory for easy access
- Included in session metadata for discovery

**Middleware Architecture (ADR-0012)**:
- Trace logging uses same middleware patterns
- Minimal invasiveness to existing middleware chain
- Follows conditional instrumentation pattern

## Execution

This specification can be implemented using:

```bash
/sdlc:implement docs/specs/trace-level-llm-logging.md
```

The implementation will:
1. Create Archon tasks for each implementation step
2. Use the codebase-analyst agent for pattern validation
3. Use the validator agent for test creation
4. Follow the step-by-step tasks in order
5. Ensure all acceptance criteria are met
6. Run validation commands to verify zero regressions
