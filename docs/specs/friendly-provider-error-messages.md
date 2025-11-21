# Bug: Unfriendly Provider API Error Messages

## Bug Description

When LLM provider APIs experience errors (500 Internal Server Error, rate limiting, network issues), the agent displays cryptic error messages that don't help users distinguish between:
- **Provider API issues** (Anthropic/OpenAI servers down)
- **Agent configuration issues** (invalid API key, wrong model name)
- **Agent code bugs** (bugs in agent-base code)

**Current Error Message (Bad):**
```
Error: Error code: 500 - {'type': 'error', 'error': {'type': 'api_error', 'message': 'Internal server error'}, 'request_id': 'req_011CVMUEd98qkKALzBMJ7tNu'}
```

**Desired Error Message (Good):**
```
[!] Provider API Error (Anthropic)

The Anthropic API returned an internal server error (500). This is a temporary issue on Anthropic's side.

Troubleshooting:
  • Try again in a few minutes
  • Switch to a different provider: agent --provider openai
  • Check Anthropic status: https://status.anthropic.com

Request ID: req_011CVMUEd98qkKALzBMJ7tNu
Model: claude-haiku-4-5-20251001
```

## User Story

As a **user of the agent**
I want to **see clear, actionable error messages when providers fail**
So that **I can quickly understand if the issue is with the provider, my configuration, or the agent code, and know what to do about it**

## Problem Statement

The current error handling has multiple issues:

1. **No Exception Handler in Interactive Loop**
   - `src/agent/cli/interactive.py` catches `KeyboardInterrupt`, `EOFError`, and `ValueError`
   - BUT does NOT catch generic `Exception` for API errors
   - API errors bubble up as raw exceptions

2. **Middleware Logging Only**
   - `src/agent/middleware.py` line 329 logs: `logger.error(f"Agent run failed: {e}")`
   - Then re-raises the exception without context
   - No user-friendly formatting

3. **No Error Classification**
   - HTTP 500 errors (provider server issues)
   - HTTP 429 errors (rate limiting)
   - HTTP 401 errors (auth issues)
   - HTTP 404 errors (model not found)
   - Network errors (connection timeout)
   - All treated the same way

4. **No Actionable Guidance**
   - Users don't know what to do
   - Can't distinguish transient vs permanent errors
   - No suggestion to switch providers

## Solution Statement

Implement a comprehensive error handling system that:

1. **Catches all API exceptions** in the interactive loop
2. **Classifies errors** by type (provider issue, config issue, code bug)
3. **Formats errors** with clear, friendly messages
4. **Provides troubleshooting steps** specific to the error type
5. **Suggests alternatives** (switch provider, retry, fix config)
6. **Preserves technical details** for debugging (request ID, model, provider)

## Related Documentation

### Requirements
- [Architecture](../design/architecture.md) - Error handling patterns

### Architecture Decisions
- [ADR-0003: Multi-Provider LLM Architecture](../decisions/0003-multi-provider-llm-architecture.md) - Provider abstraction
- [ADR-0014: Observability Integration](../decisions/0014-observability-integration.md) - Error tracking

## Codebase Analysis Findings

### Current Error Flow
1. **Provider SDK** (anthropic, openai, etc.) raises exception (e.g., `anthropic.APIStatusError`)
2. **Middleware** (`src/agent/middleware.py:329`) catches, logs, and re-raises
3. **Display** (`src/agent/cli/display.py`) does NOT catch (just re-raises `KeyboardInterrupt`)
4. **Interactive Loop** (`src/agent/cli/interactive.py`) does NOT catch general exceptions
5. **Result**: Raw exception printed to console by Python's default handler

### Error Types by Provider

**Anthropic:**
- `anthropic.APIStatusError` - HTTP error with status code
  - 500: Internal server error
  - 529: Overloaded
  - 401: Invalid API key
  - 404: Model not found
  - 429: Rate limit exceeded

**OpenAI:**
- `openai.APIError` - Base class
  - `openai.APIConnectionError` - Network issues
  - `openai.RateLimitError` - Rate limiting
  - `openai.AuthenticationError` - Invalid API key

**Azure:**
- Similar to OpenAI (uses openai SDK)

**Google Gemini:**
- `google.api_core.exceptions` - Various errors

### Files to Modify

1. **src/agent/exceptions.py** (NEW) - Custom exception classes
2. **src/agent/cli/error_handler.py** (NEW) - Error classification and formatting
3. **src/agent/cli/interactive.py** - Add exception handler in loop
4. **src/agent/cli/execution.py** - Add exception handler for single-prompt mode
5. **src/agent/middleware.py** - Wrap exceptions with context
6. **tests/unit/cli/test_error_handler.py** (NEW) - Test error formatting

## Implementation Plan

### Phase 1: Foundation (Exception Hierarchy)
**Goal**: Create custom exception classes with metadata

1. **Create Exception Hierarchy**
   - Base `AgentError` exception
   - `ProviderAPIError` - API failures (500, 503, 529)
   - `ProviderAuthError` - Authentication failures (401, 403)
   - `ProviderRateLimitError` - Rate limiting (429)
   - `ProviderModelNotFoundError` - Invalid model (404)
   - `ProviderTimeoutError` - Network timeouts
   - `AgentConfigError` - Configuration issues

2. **Add Error Metadata**
   - Provider name (anthropic, openai, etc.)
   - HTTP status code
   - Error code from provider
   - Request ID (for debugging)
   - Model name
   - Original exception

### Phase 2: Error Classification
**Goal**: Classify provider exceptions into our exception hierarchy

1. **Create Error Classifier**
   - Parse Anthropic exceptions
   - Parse OpenAI exceptions
   - Parse Azure exceptions
   - Parse Gemini exceptions
   - Parse network errors

2. **Wrap Exceptions in Middleware**
   - Catch provider exceptions in middleware
   - Classify and wrap in our exception types
   - Preserve stack trace and context
   - Re-raise wrapped exception

### Phase 3: User-Friendly Formatting
**Goal**: Display beautiful, actionable error messages

1. **Create Error Formatter**
   - Format `ProviderAPIError` with troubleshooting
   - Format `ProviderAuthError` with config help
   - Format `ProviderRateLimitError` with retry guidance
   - Format `ProviderModelNotFoundError` with valid models list
   - Format unknown errors with fallback message

2. **Add Troubleshooting Logic**
   - Suggest switching providers
   - Suggest checking status pages
   - Suggest configuration fixes
   - Provide retry timing guidance

### Phase 4: Integration
**Goal**: Integrate error handling into CLI

1. **Update Interactive Loop**
   - Add `except Exception` handler
   - Format and display errors
   - Continue loop (don't crash)

2. **Update Single-Prompt Mode**
   - Add exception handler
   - Format and display errors
   - Exit with appropriate code

3. **Update Middleware**
   - Wrap exceptions before re-raising
   - Add provider context

## Step by Step Tasks

### Task 1: Create Exception Hierarchy
- **Description**: Create `src/agent/exceptions.py` with custom exception classes
- **Files to create**: `src/agent/exceptions.py`
- **Pattern**:
  ```python
  class AgentError(Exception):
      """Base exception for agent errors."""
      pass

  class ProviderAPIError(AgentError):
      """Provider API error (500, 503, 529)."""
      def __init__(self, provider: str, status_code: int, message: str,
                   request_id: str | None = None, model: str | None = None,
                   original_error: Exception | None = None):
          self.provider = provider
          self.status_code = status_code
          self.request_id = request_id
          self.model = model
          self.original_error = original_error
          super().__init__(message)
  ```
- **Validation**: Import exceptions in other modules

### Task 2: Create Error Classifier
- **Description**: Create `src/agent/cli/error_handler.py` with classification logic
- **Files to create**: `src/agent/cli/error_handler.py`
- **Functions**:
  - `classify_anthropic_error()` - Parse anthropic exceptions
  - `classify_openai_error()` - Parse openai exceptions
  - `classify_provider_error()` - Dispatch to provider-specific classifier
- **Validation**: Unit tests for classification

### Task 3: Create Error Formatter
- **Description**: Add error formatting functions to `error_handler.py`
- **Files to modify**: `src/agent/cli/error_handler.py`
- **Functions**:
  - `format_provider_api_error()` - Format 500 errors with troubleshooting
  - `format_provider_auth_error()` - Format 401 errors with config help
  - `format_provider_rate_limit_error()` - Format 429 errors with retry guidance
  - `format_error()` - Main dispatch function
- **Validation**: Manual testing with mock errors

### Task 4: Add Exception Wrapping to Middleware
- **Description**: Wrap provider exceptions in middleware before re-raising
- **Files to modify**: `src/agent/middleware.py`
- **Location**: Line 328-345 (exception handler in `agent_run_logging_middleware`)
- **Pattern**:
  ```python
  except Exception as e:
      logger.error(f"Agent run failed: {e}")

      # Wrap in our exception types
      from agent.cli.error_handler import classify_provider_error
      wrapped = classify_provider_error(e, config)
      if wrapped:
          raise wrapped from e
      else:
          raise  # Unknown error, re-raise as-is
  ```
- **Validation**: Check that wrapped exceptions have metadata

### Task 5: Add Exception Handler to Interactive Loop
- **Description**: Catch and format exceptions in interactive mode
- **Files to modify**: `src/agent/cli/interactive.py`
- **Location**: Line 517-528 (execute agent query)
- **Pattern**:
  ```python
  try:
      # Execute agent query
      response = await _execute_agent_query(...)
      # Track conversation...
      # Print response...
  except KeyboardInterrupt:
      console.print("\n[yellow]Use Ctrl+D to exit or type 'exit'[/yellow]")
      continue
  except AgentError as e:
      # Our custom errors - format nicely
      from agent.cli.error_handler import format_error
      error_message = format_error(e)
      console.print(f"\n{error_message}\n")
      continue  # Don't crash, continue loop
  except Exception as e:
      # Unknown errors - show generic message
      console.print(f"\n[red]Unexpected error:[/red] {e}\n")
      logger.exception("Unexpected error in interactive mode")
      continue
  ```
- **Validation**: Test with various error scenarios

### Task 6: Add Exception Handler to Single-Prompt Mode
- **Description**: Catch and format exceptions in single-prompt execution
- **Files to modify**: `src/agent/cli/execution.py`
- **Location**: Around line 92 (where agent runs)
- **Pattern**: Similar to interactive mode but exit instead of continue
- **Validation**: Test with `agent -p "query"`

### Task 7: Create Troubleshooting Messages
- **Description**: Add provider-specific troubleshooting guidance
- **Files to modify**: `src/agent/cli/error_handler.py`
- **Content**:
  - Provider status page URLs
  - Alternative provider suggestions
  - Retry timing recommendations
  - Configuration fix instructions
- **Validation**: Manual testing of different error types

### Task 8: Write Unit Tests
- **Description**: Test error classification and formatting
- **Files to create**: `tests/unit/cli/test_error_handler.py`
- **Test cases**:
  - Classify Anthropic 500 error
  - Classify OpenAI rate limit error
  - Format provider API error
  - Format auth error
  - Format unknown error (fallback)
- **Validation**: All tests pass

### Task 9: Write Integration Tests
- **Description**: Test end-to-end error handling
- **Files to create**: `tests/integration/test_error_handling.py`
- **Test cases**:
  - Mock provider 500 error in interactive mode
  - Mock provider 401 error in single-prompt mode
  - Verify error message format
  - Verify loop continues after error
- **Validation**: All integration tests pass

### Task 10: Add Retry Logic (Optional Enhancement)
- **Description**: Automatically retry on transient errors (500, 503)
- **Files to modify**: `src/agent/middleware.py`
- **Pattern**: Exponential backoff with max retries
- **Validation**: Test with mock transient errors

### Task 11: Update Documentation
- **Description**: Document error handling behavior
- **Files to modify**:
  - `README.md` - Add troubleshooting section
  - `docs/design/architecture.md` - Document error handling
  - `CONTRIBUTING.md` - Error handling patterns
- **Validation**: Documentation is clear and accurate

### Task 12: Manual Testing - All Error Types
- **Description**: Manually test each error type
- **Test cases**:
  - Invalid API key (401)
  - Rate limiting (429) - requires hitting rate limit
  - Server error (500) - mock or wait for real error
  - Model not found (404) - use invalid model name
  - Network timeout - disconnect network
  - Unknown error - intentionally trigger bug
- **Validation**: All errors display friendly messages

## Testing Strategy

### Unit Tests

#### Exception Classification
- **Test**: `test_classify_anthropic_500_error`
  - Create mock Anthropic 500 error
  - Classify with `classify_anthropic_error()`
  - Assert returns `ProviderAPIError` with correct metadata

- **Test**: `test_classify_openai_rate_limit`
  - Create mock OpenAI rate limit error
  - Classify with `classify_openai_error()`
  - Assert returns `ProviderRateLimitError`

- **Test**: `test_classify_unknown_error`
  - Create generic Exception
  - Classify with `classify_provider_error()`
  - Assert returns None (can't classify)

#### Error Formatting
- **Test**: `test_format_provider_api_error`
  - Create `ProviderAPIError` with Anthropic metadata
  - Format with `format_provider_api_error()`
  - Assert message contains:
    - "Provider API Error"
    - Provider name
    - Status code
    - Troubleshooting steps
    - Request ID

- **Test**: `test_format_auth_error`
  - Create `ProviderAuthError`
  - Format with `format_provider_auth_error()`
  - Assert message contains:
    - "Authentication Error"
    - Configuration fix steps
    - Command to set API key

### Integration Tests

#### End-to-End Error Handling
- **Test**: `test_interactive_mode_handles_500_error`
  - Start interactive mode
  - Mock provider to raise 500 error
  - Send query
  - Assert:
    - Friendly error message displayed
    - Loop continues (doesn't crash)
    - User can send another query

- **Test**: `test_single_prompt_handles_auth_error`
  - Run with invalid API key
  - Mock provider to raise 401 error
  - Assert:
    - Friendly error message displayed
    - Exit code is appropriate
    - Suggests configuration fix

### Edge Cases

- **Nested exceptions**: Provider raises exception within exception
- **Missing metadata**: Exception doesn't have request_id
- **Invalid provider**: Unknown provider name
- **Empty error message**: Provider error has no message
- **Long error messages**: Truncate appropriately

## Acceptance Criteria

### Error Classification
- [ ] Anthropic exceptions classified correctly (500, 529, 401, 404, 429)
- [ ] OpenAI exceptions classified correctly
- [ ] Azure exceptions classified correctly
- [ ] Gemini exceptions classified correctly
- [ ] Network errors (timeouts, connection refused) classified
- [ ] Unknown errors handled gracefully (fallback message)

### Error Formatting
- [ ] Provider API errors (500) show:
  - Clear title "Provider API Error"
  - Provider name and model
  - Explanation that it's a provider issue
  - Troubleshooting steps (retry, switch provider, check status)
  - Technical details (request ID, status code)
- [ ] Auth errors (401) show:
  - Clear title "Authentication Error"
  - Provider name
  - Configuration fix steps
  - Command to set API key
- [ ] Rate limit errors (429) show:
  - Clear title "Rate Limit Exceeded"
  - Provider name
  - Retry timing guidance
  - Upgrade suggestion (if applicable)
- [ ] Model not found errors (404) show:
  - Clear title "Model Not Found"
  - Invalid model name
  - List of valid models

### User Experience
- [ ] Errors display in rich format (colors, boxes)
- [ ] Troubleshooting steps are actionable
- [ ] Technical details available but not prominent
- [ ] Interactive mode continues after errors (doesn't crash)
- [ ] Single-prompt mode exits with appropriate code
- [ ] Error messages fit in terminal width (wrap nicely)

### Code Quality
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage >80% for error handling code
- [ ] No regression in existing functionality
- [ ] Error handling doesn't impact performance

## Validation Commands

```bash
# Run unit tests
cd /Users/danielscholl/source/github/danielscholl/agent-base
uv run pytest tests/unit/cli/test_error_handler.py -v

# Run integration tests
uv run pytest tests/integration/test_error_handling.py -v

# Full test suite
uv run pytest -v

# Manual testing: Invalid API key (401)
export ANTHROPIC_API_KEY=invalid-key
agent -p "Hello"
# Should show: Authentication Error with config fix steps

# Manual testing: Invalid model (404)
agent --model invalid-model-name -p "Hello"
# Should show: Model Not Found error

# Manual testing: Network timeout
# Disconnect network and run:
agent -p "Hello"
# Should show: Network error with troubleshooting

# Manual testing: 500 error
# Wait for Anthropic API to have issues, or mock
# Should show: Provider API Error with retry guidance
```

## Notes

### Error Message Format

**Template for Provider API Error (500):**
```
┌─ Provider API Error (Anthropic) ─────────────────────────┐
│                                                           │
│ The Anthropic API returned an internal server error.     │
│ This is a temporary issue on Anthropic's side.           │
│                                                           │
│ Troubleshooting:                                          │
│   • Try again in a few minutes                            │
│   • Switch to a different provider:                       │
│     agent --provider openai                               │
│   • Check status: https://status.anthropic.com           │
│                                                           │
│ Technical Details:                                        │
│   Status: 500 Internal Server Error                      │
│   Model: claude-haiku-4-5-20251001                       │
│   Request ID: req_011CVMUEd98qkKALzBMJ7tNu               │
└───────────────────────────────────────────────────────────┘
```

**Template for Auth Error (401):**
```
┌─ Authentication Error (Anthropic) ───────────────────────┐
│                                                           │
│ The Anthropic API rejected your API key.                 │
│                                                           │
│ Fix:                                                      │
│   1. Get your API key from:                               │
│      https://console.anthropic.com/settings/keys         │
│   2. Configure it:                                        │
│      agent config provider anthropic                      │
│   3. Or set environment variable:                         │
│      export ANTHROPIC_API_KEY=your-key-here              │
│                                                           │
│ Technical Details:                                        │
│   Status: 401 Unauthorized                               │
│   Model: claude-haiku-4-5-20251001                       │
└───────────────────────────────────────────────────────────┘
```

### Provider Status Pages

- **Anthropic**: https://status.anthropic.com
- **OpenAI**: https://status.openai.com
- **Azure**: https://status.azure.com
- **Google Gemini**: https://status.cloud.google.com

### Alternative Providers

When suggesting provider switches:
- If Anthropic fails → suggest OpenAI or GitHub Models
- If OpenAI fails → suggest Anthropic or GitHub Models
- If Azure fails → suggest Anthropic or OpenAI
- Always include GitHub Models as free alternative

### Retry Strategy (Optional Enhancement)

For transient errors (500, 503, 529):
1. **First retry**: Wait 1 second
2. **Second retry**: Wait 2 seconds
3. **Third retry**: Wait 4 seconds
4. **Give up**: Show error message

This can be added in Task 10 as an enhancement.

### Technical Details Visibility

Technical details (request ID, status code, model) should be:
- Present in the error message (for bug reports)
- But visually de-emphasized (dim color, small text)
- Easy to copy for support tickets

### Error Logging

All errors should still be logged to:
- Session log file (`~/.agent/logs/session-{name}.log`)
- With full stack trace
- With timestamp
- With all metadata

This ensures we can debug issues even if user doesn't report full error.

## Archon Project

**Project ID**: `ba35d044-bd19-404c-922c-d98cdc109e17`

Tasks will be created during implementation phase.

## Execution

This spec can be implemented using: `/sdlc:implement docs/specs/friendly-provider-error-messages.md`

Or execute tasks manually in Archon by creating tasks from this specification.
