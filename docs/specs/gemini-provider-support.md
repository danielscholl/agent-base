# Feature: Google Gemini Provider Support

## Feature Description

Add support for Google Gemini models (running on Google Cloud Platform) as a new LLM provider in the agent-base framework. This feature will enable users to leverage Google's Gemini 2.0 and 2.5 models for conversational AI tasks, providing an additional choice alongside existing OpenAI, Anthropic, and Azure providers.

The implementation will create a custom `GeminiChatClient` that integrates with the Microsoft Agent Framework's `BaseChatClient` interface, following the same patterns used for OpenAI and Anthropic providers. This ensures consistency in the codebase while enabling Gemini-specific features like function calling, streaming responses, and both API key and Vertex AI authentication methods.

## User Story

As a **developer building AI agents**
I want to **use Google Gemini models as my LLM provider**
So that **I can leverage Gemini's capabilities, benefit from GCP integration, and have flexibility in choosing the best model for my use case**

## Problem Statement

Currently, agent-base supports four LLM providers (OpenAI, Anthropic, Azure OpenAI, and Azure AI Foundry), but does not support Google's Gemini models. This limits users who:

1. Prefer Google Cloud Platform for infrastructure
2. Want to use Gemini-specific features (e.g., multimodal capabilities, long context windows)
3. Need GCP integration with existing Google Cloud services
4. Have existing Google Cloud credits or contracts
5. Want to compare Gemini's performance against other providers

While the Microsoft Agent Framework doesn't have an official `agent-framework-gemini` package yet, the framework's `BaseChatClient` interface and `ChatClientProtocol` make it possible to implement custom providers. The Google Gen AI SDK provides all necessary capabilities (chat completions, function calling, streaming) to create a fully-functional Gemini integration.

## Solution Statement

Implement a custom `GeminiChatClient` class that extends `BaseChatClient` and implements the required `_inner_get_response()` and `_inner_get_streaming_response()` methods. This implementation will:

1. **Use the google-genai SDK** - Leverage the official Python SDK for Gemini API access
2. **Follow existing patterns** - Mirror the architecture used for OpenAI and Anthropic providers
3. **Support dual authentication** - Enable both API key (Gemini Developer API) and GCP credentials (Vertex AI)
4. **Handle message conversion** - Translate between agent-framework's `ChatMessage` format and Gemini's format
5. **Enable function calling** - Support tool/function invocation for agent capabilities
6. **Provide streaming** - Implement streaming responses for real-time interaction
7. **Maintain testability** - Support dependency injection and mocking for tests

The solution will be implemented as a new module `src/agent/providers/gemini/` containing:
- `chat_client.py` - Main GeminiChatClient implementation
- `__init__.py` - Public API exports
- Supporting utilities for message conversion and error handling

Configuration will be added to `AgentConfig` to support Gemini-specific settings (API key, project ID, location, model name).

## Relevant Files

### Existing Files to Modify

- **src/agent/config.py** (lines 1-210)
  - Add Gemini configuration fields: `gemini_api_key`, `gemini_model`, `gemini_project_id`, `gemini_location`
  - Update `from_env()` to load Gemini environment variables
  - Add Gemini validation in `validate()` method
  - Update `get_model_display_name()` to include Gemini provider

- **src/agent/agent.py** (lines 105-186)
  - Add Gemini case to `_create_chat_client()` method
  - Import `GeminiChatClient` from new provider module
  - Handle Gemini-specific client initialization

- **pyproject.toml** (lines 21-35)
  - Add `google-genai>=0.8.0` to dependencies
  - Ensure compatibility with existing packages

- **.env.example** (lines 1-62)
  - Add Gemini configuration template with comments
  - Document authentication options (API key vs Vertex AI)

- **README.md** (lines 41-47)
  - Add Gemini to list of supported providers
  - Update provider count in overview

- **docs/design/usage.md** (lines 60-65)
  - Add Gemini to provider list in `--check` command example

### New Files to Create

#### Foundation Files

- **src/agent/providers/__init__.py**
  - New package for provider implementations
  - Exports common utilities

- **src/agent/providers/gemini/__init__.py**
  - Package initialization for Gemini provider
  - Export `GeminiChatClient` as public API

- **src/agent/providers/gemini/chat_client.py**
  - Main `GeminiChatClient` class extending `BaseChatClient`
  - Implement `_inner_get_response()` for non-streaming
  - Implement `_inner_get_streaming_response()` for streaming
  - Message format conversion utilities
  - Error handling and exception mapping

- **src/agent/providers/gemini/types.py**
  - Type definitions for Gemini-specific data structures
  - Message conversion helpers
  - Tool/function definition converters

#### Test Files

- **tests/unit/providers/__init__.py**
  - Test package initialization

- **tests/unit/providers/test_gemini_chat_client.py**
  - Unit tests for GeminiChatClient
  - Test message conversion
  - Test error handling
  - Test configuration
  - Mock Gemini SDK responses

- **tests/integration/llm/test_gemini_integration.py**
  - Real Gemini API integration test (marked with `@pytest.mark.llm`)
  - Test basic chat completion
  - Test streaming responses
  - Test function calling
  - Requires `GEMINI_API_KEY` environment variable

- **tests/fixtures/gemini.py**
  - Shared fixtures for Gemini tests
  - Mock Gemini client
  - Test configurations

#### Documentation Files

- **docs/decisions/0015-gemini-provider-integration.md**
  - ADR documenting the decision to add Gemini support
  - Rationale for implementation approach
  - Alternatives considered (OpenAI compatibility layer vs custom client)
  - Trade-offs and consequences

## Implementation Plan

### Phase 1: Foundation

**Objective**: Set up the provider infrastructure and dependencies

1. Create the provider package structure (`src/agent/providers/`)
2. Install and configure the google-genai SDK dependency
3. Add Gemini configuration fields to `AgentConfig`
4. Update environment file template with Gemini settings
5. Create basic type definitions for message conversion

**Deliverables**:
- Provider package structure exists
- google-genai is added to dependencies
- Configuration supports Gemini provider
- Environment template includes Gemini variables

### Phase 2: Core Implementation

**Objective**: Implement the GeminiChatClient with full functionality

1. Implement `GeminiChatClient` class extending `BaseChatClient`
2. Create message conversion utilities (ChatMessage ↔ Gemini format)
3. Implement `_inner_get_response()` for synchronous chat completion
4. Implement `_inner_get_streaming_response()` for streaming responses
5. Add function calling support with tool definition conversion
6. Implement error handling and exception mapping
7. Add support for both authentication methods (API key and Vertex AI)

**Deliverables**:
- Fully functional GeminiChatClient
- Message conversion working bidirectionally
- Streaming and non-streaming responses supported
- Function calling operational
- Proper error handling

### Phase 3: Integration

**Objective**: Integrate Gemini provider into the agent framework

1. Update `Agent._create_chat_client()` to support "gemini" provider
2. Add Gemini to configuration validation logic
3. Update model display name formatting
4. Create comprehensive unit tests with mocked SDK
5. Create LLM integration tests for real API validation
6. Update documentation (README, USAGE, ADR)
7. Test end-to-end with example agent session

**Deliverables**:
- Gemini provider selectable via `LLM_PROVIDER=gemini`
- All tests passing (unit and integration)
- Documentation updated
- End-to-end validation complete

## Step by Step Tasks

### 1. Create Provider Package Structure

- Create `src/agent/providers/` directory
- Create `src/agent/providers/__init__.py` with docstring
- Create `src/agent/providers/gemini/` directory
- Create `src/agent/providers/gemini/__init__.py` placeholder
- Create `tests/unit/providers/` directory
- Create `tests/unit/providers/__init__.py`
- Create `tests/fixtures/gemini.py` for test fixtures

### 2. Add Dependencies and Configuration

- Run `uv add google-genai>=0.8.0` to install Google Gen AI SDK
- Edit `src/agent/config.py`:
  - Add gemini configuration fields to `AgentConfig` dataclass
  - Add default values: `gemini_model = "gemini-2.0-flash-exp"`
  - Add optional fields: `gemini_api_key`, `gemini_project_id`, `gemini_location`, `gemini_use_vertexai`
- Update `AgentConfig.from_env()` method:
  - Load `GEMINI_API_KEY`, `GEMINI_PROJECT_ID`, `GEMINI_LOCATION`, `GEMINI_USE_VERTEXAI`
  - Support `AGENT_MODEL` override for Gemini
- Update `.env.example`:
  - Add Gemini configuration section with inline documentation
  - Include both API key and Vertex AI examples
- Write unit tests for Gemini configuration loading

### 3. Implement Message Conversion Utilities

- Create `src/agent/providers/gemini/types.py`
- Implement `to_gemini_message()` function:
  - Convert `ChatMessage` to Gemini's message format
  - Handle role mapping (user, assistant, system)
  - Convert `TextContent`, `FunctionCallContent`, `FunctionResultContent`
- Implement `from_gemini_message()` function:
  - Convert Gemini response to `ChatMessage`
  - Extract text content from Gemini parts
  - Handle function calls in response
- Implement `to_gemini_tools()` function:
  - Convert agent-framework tool definitions to Gemini function declarations
  - Map parameter types correctly
- Write unit tests for message conversion utilities

### 4. Implement GeminiChatClient Base Structure

- Create `src/agent/providers/gemini/chat_client.py`
- Define `GeminiChatClient` class extending `BaseChatClient`:
  - Add `__init__()` method accepting `model_id`, `api_key`, `project_id`, `location`, `use_vertexai`
  - Initialize Google Gen AI client (with proper auth method)
  - Set `OTEL_PROVIDER_NAME = "gemini"`
- Implement helper method `_prepare_options()`:
  - Convert `ChatOptions` to Gemini generation config
  - Map temperature, max_tokens, top_p parameters
  - Handle tool configuration
- Add error handling utilities:
  - Map Gemini SDK exceptions to agent-framework exceptions
  - Create `_handle_gemini_error()` method
- Write unit tests for initialization and configuration

### 5. Implement Non-Streaming Response

- Implement `_inner_get_response()` method in `GeminiChatClient`:
  - Convert messages using `to_gemini_message()`
  - Prepare generation config from `chat_options`
  - Call `client.models.generate_content()` (non-streaming)
  - Convert response to `ChatResponse` using `from_gemini_message()`
  - Handle function calls in response
  - Extract usage information (token counts)
  - Wrap errors with proper exception handling
- Write unit tests with mocked Gemini SDK:
  - Test simple text response
  - Test response with function call
  - Test error scenarios
  - Verify message conversion

### 6. Implement Streaming Response

- Implement `_inner_get_streaming_response()` method:
  - Convert messages and prepare config (same as non-streaming)
  - Call `client.models.generate_content()` with streaming
  - Yield `ChatResponseUpdate` objects as chunks arrive
  - Handle streaming function calls
  - Accumulate usage information
  - Proper error handling in async iterator
- Write unit tests with mocked streaming responses:
  - Test text streaming
  - Test function call in stream
  - Test stream interruption/error
  - Verify chunk-by-chunk conversion

### 7. Implement Function Calling Support

- Enhance `to_gemini_tools()` in `types.py`:
  - Support `AIFunction` conversion to Gemini `FunctionDeclaration`
  - Map parameter schemas correctly (types, descriptions, required fields)
  - Handle nested parameter objects
- Update response handling to process function calls:
  - Detect function calls in Gemini response parts
  - Convert to `FunctionCallContent`
  - Handle automatic function execution if enabled
- Write unit tests for function calling:
  - Test tool definition conversion
  - Test function call detection
  - Test function result handling
  - End-to-end function calling flow

### 8. Add Authentication Support

- Implement API key authentication:
  - Pass `api_key` to `genai.Client(api_key=...)`
  - Set from `GEMINI_API_KEY` environment variable
- Implement Vertex AI authentication:
  - Use `genai.Client(vertexai=True, project=..., location=...)`
  - Leverage Google Cloud default credentials
  - Require `GEMINI_PROJECT_ID` and `GEMINI_LOCATION`
- Add configuration validation:
  - Ensure API key OR Vertex AI credentials are provided
  - Validate project/location for Vertex AI mode
- Write unit tests for both auth modes

### 9. Integrate with Agent Framework

- Edit `src/agent/agent.py`:
  - Import `GeminiChatClient` from `agent.providers.gemini`
  - Add `elif self.config.llm_provider == "gemini":` case to `_create_chat_client()`
  - Initialize GeminiChatClient with configuration parameters
  - Handle both API key and Vertex AI initialization paths
- Update `src/agent/config.py`:
  - Add Gemini validation in `validate()` method
  - Update `get_model_display_name()` to return `"Gemini/{model_name}"`
- Write integration tests:
  - Test agent creation with Gemini provider
  - Test with mock Gemini client injection
  - Verify tool registration works

### 10. Create Comprehensive Unit Tests

- Create `tests/unit/providers/test_gemini_chat_client.py`:
  - Test client initialization (both auth modes)
  - Test `_prepare_options()` with various ChatOptions
  - Test `_inner_get_response()` with mocked SDK
  - Test `_inner_get_streaming_response()` with mocked streams
  - Test error handling and exception mapping
  - Test message conversion edge cases
  - Test function calling with multiple tools
- Create fixtures in `tests/fixtures/gemini.py`:
  - Mock Gemini client factory
  - Mock response builders
  - Standard test configurations
- Ensure all unit tests pass: `uv run pytest -m "unit and gemini"`

### 11. Create LLM Integration Tests

- Create `tests/integration/llm/test_gemini_integration.py`:
  - Mark with `@pytest.mark.llm` and `@pytest.mark.requires_gemini`
  - Test basic chat completion with real API
  - Test streaming response
  - Test function calling with hello_world tool
  - Test conversation continuity across multiple turns
  - Skip if `GEMINI_API_KEY` not set
- Add pytest marker to `pyproject.toml`:
  - Add `requires_gemini: Tests requiring Gemini API key`
- Document in test README:
  - How to run Gemini tests
  - Cost implications
  - Required environment variables
- Verify LLM tests pass: `uv run pytest -m "llm and gemini"` (with API key)

### 12. Update Documentation

- Edit `README.md`:
  - Add Gemini to supported providers list (line 37)
  - Add link to Gemini API documentation
  - Update provider count from 4 to 5
- Edit `docs/design/usage.md`:
  - Add Gemini to `--check` command example output (line 60-65)
  - Add Gemini to prerequisites section
- Create `docs/decisions/0015-gemini-provider-integration.md`:
  - Document decision to implement custom client vs OpenAI compatibility
  - Explain BaseChatClient inheritance pattern
  - Note authentication options (API key vs Vertex AI)
  - List trade-offs and future considerations
- Update `CONTRIBUTING.md` if needed:
  - Mention Gemini in provider examples

### 13. End-to-End Validation

- Create test environment file:
  - Copy `.env.example` to `.env.test`
  - Set `LLM_PROVIDER=gemini`
  - Set `GEMINI_API_KEY=your-test-key`
  - Set `GEMINI_MODEL=gemini-2.0-flash-exp`
- Test agent creation:
  - Run `uv run agent --check` and verify Gemini shows in output
- Test interactive mode:
  - Run `uv run agent` and send test prompts
  - Verify responses come from Gemini
  - Test `/clear` and session management
- Test single query mode:
  - Run `uv run agent -p "Say hello to Alice"`
  - Verify Gemini response
- Test verbose mode:
  - Run `uv run agent -p "greet Alice" --verbose`
  - Verify execution tree shows tool calls
- Test with custom tools:
  - Verify hello_world tool works with Gemini
  - Check function calling in verbose output

### 14. Run All Validation Commands

Execute validation commands to ensure zero regressions and full functionality.

## Testing Strategy

### Unit Tests

**File**: `tests/unit/providers/test_gemini_chat_client.py`

- **Client Initialization**:
  - Test with API key authentication
  - Test with Vertex AI authentication
  - Test with missing credentials (should raise error)
  - Test with invalid configuration

- **Message Conversion**:
  - Test `to_gemini_message()` for user messages
  - Test `to_gemini_message()` for assistant messages
  - Test `to_gemini_message()` with function calls
  - Test `from_gemini_message()` for text responses
  - Test `from_gemini_message()` for function call responses
  - Test edge cases (empty messages, special characters)

- **Tool Conversion**:
  - Test `to_gemini_tools()` with AIFunction
  - Test parameter schema mapping
  - Test multiple tools
  - Test tool with complex parameters

- **Response Generation** (with mocked SDK):
  - Test `_inner_get_response()` returns valid ChatResponse
  - Test response with usage information
  - Test response with function call
  - Test error handling (API errors, network errors)

- **Streaming** (with mocked SDK):
  - Test `_inner_get_streaming_response()` yields updates
  - Test streaming accumulation
  - Test streaming with function calls
  - Test stream error handling

- **Configuration**:
  - Test `_prepare_options()` maps ChatOptions correctly
  - Test temperature, max_tokens, top_p mapping
  - Test tool configuration in options

### Integration Tests

**File**: `tests/integration/llm/test_gemini_integration.py`

**Markers**: `@pytest.mark.llm`, `@pytest.mark.requires_gemini`

- **Basic Completion**:
  - Send "Say hello" and verify response contains greeting
  - Verify response structure matches ChatResponse

- **Streaming**:
  - Send prompt with streaming enabled
  - Verify chunks are received
  - Verify final assembled message is correct

- **Function Calling**:
  - Register hello_world tool
  - Send prompt triggering function call
  - Verify function is called with correct arguments
  - Verify final response includes function result

- **Conversation Continuity**:
  - Send multiple messages in sequence
  - Verify context is maintained (memory of previous turns)
  - Test with thread persistence

- **Error Scenarios**:
  - Test with invalid API key (should fail gracefully)
  - Test with malformed request (should raise appropriate error)

### Edge Cases

- **Empty or null messages**: Verify proper error handling
- **Very long prompts**: Test with prompts near token limits
- **Special characters**: Test with emojis, unicode, code blocks
- **Concurrent requests**: Verify thread-safety of client
- **Function call failures**: Test when tool execution fails
- **Network failures**: Test retry and timeout behavior
- **Invalid tool definitions**: Verify validation and error messages
- **Model not found**: Test with non-existent model ID
- **Rate limiting**: Verify exponential backoff (if implemented)
- **Token limit exceeded**: Verify clear error message
- **Mixed content types**: Test if Gemini supports (images, etc.) in future

## Acceptance Criteria

- [ ] GeminiChatClient class successfully extends BaseChatClient
- [ ] Configuration accepts `LLM_PROVIDER=gemini` and validates required fields
- [ ] Both authentication methods work (API key and Vertex AI)
- [ ] Non-streaming chat completion returns valid responses
- [ ] Streaming chat completion yields response updates correctly
- [ ] Function calling works with agent tools (hello_world example)
- [ ] Message conversion handles all content types (text, function calls, results)
- [ ] Error handling maps Gemini exceptions to framework exceptions
- [ ] Unit tests achieve >85% coverage for new code
- [ ] All existing tests continue to pass (zero regressions)
- [ ] LLM integration tests pass with real Gemini API
- [ ] `agent --check` displays Gemini provider status correctly
- [ ] Interactive mode works with Gemini (`uv run agent`)
- [ ] Single query mode works (`uv run agent -p "prompt"`)
- [ ] Verbose mode shows Gemini execution details
- [ ] Session persistence works with Gemini conversations
- [ ] Documentation updated (README, USAGE, ADR)
- [ ] .env.example includes Gemini configuration template
- [ ] Code quality checks pass (black, ruff, mypy)

## Validation Commands

Execute every command to validate the feature works correctly with zero regressions.

```bash
# 1. Install dependencies and verify package is added
uv sync --all-extras
uv pip list | grep google-genai

# 2. Run code quality checks
uv run black src/agent/ tests/ --check
uv run ruff check src/agent/ tests/
uv run mypy src/agent/

# 3. Run unit tests (fast, no API calls)
uv run pytest -m "not llm" -n auto

# 4. Run unit tests with coverage check
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# 5. Run Gemini-specific unit tests
uv run pytest -m "unit and gemini" -v

# 6. Run LLM integration tests (requires GEMINI_API_KEY)
# Note: This will make real API calls and may incur costs
uv run pytest -m "llm and gemini" -v

# 7. Verify configuration with Gemini provider
# Set up .env with: LLM_PROVIDER=gemini, GEMINI_API_KEY=your-key
uv run agent --check

# 8. Test single query mode
uv run agent -p "Say hello to Alice"

# 9. Test verbose mode with function calling
uv run agent -p "Say hello to Bob" --verbose

# 10. Test interactive mode (manual verification)
# Start agent, send messages, verify responses, test /clear, exit
uv run agent

# 11. Run all tests including Gemini (comprehensive validation)
uv run pytest -n auto

# 12. Generate coverage report and review
uv run pytest -m "not llm" --cov=src/agent --cov-report=html
open htmlcov/index.html

# 13. Verify no regressions in existing providers
# Test with OpenAI
LLM_PROVIDER=openai uv run agent -p "test" --quiet

# Test with Anthropic (if configured)
LLM_PROVIDER=anthropic uv run agent -p "test" --quiet
```

## Notes

### Design Decisions

1. **Custom Client vs OpenAI Compatibility Layer**:
   - Chose custom `GeminiChatClient` over using Gemini's OpenAI-compatible API
   - Rationale: Full access to Gemini-specific features, better error handling, native SDK benefits
   - Trade-off: More implementation work upfront, but better long-term maintainability

2. **Dual Authentication Support**:
   - Support both Gemini Developer API (API key) and Vertex AI (GCP credentials)
   - Allows developers to choose based on their infrastructure
   - Vertex AI recommended for production (better rate limits, SLA)

3. **Message Conversion Strategy**:
   - Implement bidirectional conversion utilities in `types.py`
   - Keep conversion logic separate from client logic for testability
   - Handle all current content types, design for extensibility (future: images, etc.)

4. **Provider Package Structure**:
   - Create `src/agent/providers/` as a new top-level package
   - Each provider can be isolated (gemini, potentially others in future)
   - Aligns with potential future refactoring to move OpenAI/Anthropic here

### Future Considerations

1. **Multimodal Support**: Gemini supports image inputs - consider adding in future iterations
2. **Long Context**: Gemini models support up to 2M tokens - may need special handling
3. **Caching**: Gemini supports prompt caching for cost optimization
4. **Grounding**: Vertex AI offers Google Search grounding - potential enhancement
5. **Batch Requests**: Consider batch API support for cost-effective bulk operations
6. **Model Versioning**: Track model version changes (gemini-2.0 → gemini-2.5, etc.)

### Dependencies Added

- `google-genai>=0.8.0` - Google's official Generative AI SDK
  - Provides chat completions, streaming, function calling
  - Supports both Gemini Developer API and Vertex AI
  - Well-maintained by Google

### Alternative Approaches Considered

**Approach 1: Use OpenAI-Compatible API**
- Gemini provides OpenAI-compatible endpoints
- Could reuse existing OpenAIChatClient with different endpoint
- **Rejected**: Limited to OpenAI's feature set, less control over Gemini-specific capabilities

**Approach 2: Wait for Official agent-framework-gemini**
- Microsoft may release official Gemini support in future
- **Rejected**: Unknown timeline, blocks current user needs

**Approach 3: Implement via LangChain Wrapper**
- Use LangChain's ChatGoogleGenerativeAI
- **Rejected**: Adds unnecessary dependency, doesn't align with framework patterns

### Testing Notes

- LLM tests marked with `@pytest.mark.llm` and `@pytest.mark.requires_gemini`
- Real API tests will consume Gemini API quota/credits
- Free tier: 15 requests per minute, 1500 per day (as of 2025)
- Recommend using `gemini-2.0-flash-exp` for testing (fast, cost-effective)
- Document API costs in test README

### Migration Path

For users wanting to switch to Gemini:
1. Add Gemini API key or configure GCP credentials
2. Update `.env`: `LLM_PROVIDER=gemini`
3. Optionally set `GEMINI_MODEL=gemini-2.5-pro` for more capable model
4. Run `agent --check` to verify connectivity
5. Existing sessions remain compatible (provider is session-specific)
