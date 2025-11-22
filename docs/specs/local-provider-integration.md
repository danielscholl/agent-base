# Feature: Local LLM Provider with Docker Models Support

## Feature Description

Add support for locally-hosted LLM models via Docker Desktop's built-in model serving capability. This enables users to run the agent framework entirely offline using local models like ai/phi4, without requiring cloud API keys or internet connectivity. The implementation leverages Docker models' OpenAI-compatible API endpoint, allowing seamless integration with the existing agent-framework OpenAI client.

This feature provides cost-free local development, offline operation, data privacy, and rapid iteration for users who have pulled Docker models (e.g., `docker model ai/phi4`).

## User Story

As a **developer working with the agent-base framework**
I want to **run the agent using a locally-hosted LLM model via Docker**
So that **I can develop and test without cloud API costs, work offline, and maintain complete data privacy**

## Problem Statement

Currently, agent-base requires one of five cloud-based LLM providers (OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, or Gemini), which presents several limitations:

1. **Cost barrier**: API calls incur charges, making development and testing expensive
2. **Internet dependency**: Requires stable internet connection and cloud service availability
3. **Data privacy concerns**: All prompts and responses are sent to third-party services
4. **Latency**: Network round-trips add latency to every interaction
5. **Rate limiting**: Cloud providers enforce rate limits that can slow development

Docker Desktop now provides built-in model serving with OpenAI-compatible endpoints, enabling local execution of models like ai/phi4. However, agent-base lacks a provider configuration to utilize these local endpoints.

## Solution Statement

Implement a "local" LLM provider that leverages Docker models' OpenAI-compatible API. Rather than creating a custom chat client (like the Gemini provider), we'll reuse the existing `OpenAIChatClient` from agent-framework with a custom `base_url` pointing to the local Docker endpoint.

**Architecture approach:**
1. Add "local" as a new provider option in `AgentConfig`
2. Configure `OpenAIChatClient` with Docker's local endpoint (`http://localhost:12434/engines/llama.cpp/v1`)
3. Set ai/phi4 as the default local model
4. Allow configuration via environment variables (`LOCAL_BASE_URL`, `LOCAL_MODEL`)
5. Skip API key validation for local provider since Docker doesn't require authentication

This approach minimizes code changes, reuses proven infrastructure, and aligns with Docker's OpenAI-compatible design.

## Relevant Files

### Existing Files to Modify

- **`src/agent/config.py`** (lines 1-248)
  - Add local provider configuration fields (`local_base_url`, `local_model`)
  - Load local config from environment variables in `from_env()`
  - Add validation logic for local provider in `validate()`
  - Add display name for local provider in `get_model_display_name()`

- **`src/agent/agent.py`** (lines 107-199)
  - Add "local" case in `_create_chat_client()` method
  - Instantiate `OpenAIChatClient` with custom `base_url` for Docker endpoint
  - Update provider list in docstrings and error messages

- **`.env.example`** (lines 1-77)
  - Add new section for Local Provider Configuration
  - Document `LLM_PROVIDER=local` option
  - Document `LOCAL_BASE_URL` (default: `http://localhost:12434/engines/llama.cpp/v1`)
  - Document `LOCAL_MODEL` (default: `ai/phi4`)

- **`README.md`** (lines 37-38)
  - Add "Local (Docker Models)" to supported providers list
  - Update "Prerequisites" section to mention Docker as optional

- **`docs/design/usage.md`**
  - Add section documenting local provider setup and usage
  - Include Docker model pull command example
  - Document benefits and limitations of local provider

### New Files to Create

- **`tests/unit/core/test_config_local.py`**
  - Unit tests for local provider configuration
  - Test `from_env()` with local provider settings
  - Test validation logic for local provider
  - Test display name generation

- **`tests/integration/llm/test_local_integration.py`**
  - Integration tests requiring Docker models running
  - Test chat completion with local model
  - Test streaming responses
  - Test tool invocation with local model
  - Mark with `@pytest.mark.llm` and `@pytest.mark.requires_local`

- **`docs/decisions/0016-local-provider-integration.md`**
  - ADR documenting the decision to support Docker models
  - Rationale for reusing OpenAI client vs custom provider
  - Alternatives considered (Ollama, LM Studio, custom client)
  - Consequences and future considerations

## Implementation Plan

### Phase 1: Foundation

Add the core configuration infrastructure for the local provider. This includes:
- Defining configuration fields in `AgentConfig` dataclass
- Loading configuration from environment variables
- Adding validation logic that skips API key requirements
- Updating display name generation

**Goal**: Establish configuration foundation without breaking existing functionality.

### Phase 2: Core Implementation

Implement the local provider chat client integration. This includes:
- Adding "local" case to `_create_chat_client()` method
- Configuring `OpenAIChatClient` with custom `base_url`
- Updating documentation strings and error messages
- Creating comprehensive unit tests

**Goal**: Enable local provider functionality with full test coverage.

### Phase 3: Integration

Complete end-to-end integration and documentation. This includes:
- Creating integration tests for local provider
- Documenting setup process in README and USAGE
- Creating ADR documenting architectural decisions
- Validating complete feature with Docker models

**Goal**: Production-ready feature with complete documentation and validation.

## Step by Step Tasks

### 1. Update AgentConfig with Local Provider Fields

- Add configuration fields to `AgentConfig` dataclass (after gemini fields):
  - `local_base_url: str | None = None`
  - `local_model: str = "ai/ai/phi4"`
- Add local provider loading in `from_env()` method:
  - Load `LOCAL_BASE_URL` (default: `"http://localhost:12434/engines/llama.cpp/v1"`)
  - Load `LOCAL_MODEL` (default: `"ai/ai/phi4"`)
  - Handle `AGENT_MODEL` override for local provider
- Update `validate()` method:
  - Add `elif self.llm_provider == "local":` case
  - Check if `local_base_url` is set (not None)
  - No API key validation required for local provider
  - Add helpful error message suggesting `docker model pull ai/phi4`
- Update `get_model_display_name()` method:
  - Add `elif self.llm_provider == "local":` case
  - Return `f"Local/{self.local_model}"`
- Update docstrings in `AgentConfig` class to include "local" in provider list

### 2. Create Unit Tests for Local Configuration

- Create `tests/unit/core/test_config_local.py`
- Import necessary fixtures and helpers
- Create test class `TestLocalProviderConfig`
- Write test methods:
  - `test_from_env_with_local_provider()` - Test loading local config from env
  - `test_local_provider_validation_success()` - Test validation passes with base_url
  - `test_local_provider_validation_missing_url()` - Test validation fails without base_url
  - `test_local_provider_display_name()` - Test display name generation
  - `test_local_model_override()` - Test AGENT_MODEL overrides default
- Use mocking for environment variables via `monkeypatch` fixture
- Follow existing test patterns from `test_config.py`
- Mark tests with `@pytest.mark.unit` and `@pytest.mark.config`

### 3. Integrate Local Provider in Agent

- Update `src/agent/agent.py` in `_create_chat_client()` method
- Add new elif branch for local provider (after gemini, before else):
  ```python
  elif self.config.llm_provider == "local":
      from agent_framework.openai import OpenAIChatClient

      return OpenAIChatClient(
          model_id=self.config.local_model,
          base_url=self.config.local_base_url,
          api_key="not-needed",  # Docker doesn't require auth
      )
  ```
- Update the error message in the else clause:
  - Change from `"Supported: openai, anthropic, azure, foundry, gemini"`
  - To `"Supported: openai, anthropic, azure, foundry, gemini, local"`
- Update class docstring to list "Local (Docker Models)" as supported provider
- Update method docstring in `_create_chat_client()` to document local provider

### 4. Update Environment Configuration File

- Open `.env.example`
- Add new section after Gemini configuration (line 56):
  ```
  # ==============================================================================
  # Local Provider Configuration (when LLM_PROVIDER=local)
  # ==============================================================================
  # Docker Desktop model serving with OpenAI-compatible API
  # Requires: docker model pull <model-name>
  # LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1
  # AGENT_MODEL=ai/phi4
  ```
- Update line 10 comment to include "local" in supported providers:
  - Change: `# Supported providers: openai, anthropic, azure, foundry, gemini`
  - To: `# Supported providers: openai, anthropic, azure, foundry, gemini, local`

### 5. Create Integration Tests for Local Provider

- Create `tests/integration/llm/test_local_integration.py`
- Import necessary modules, fixtures, and helpers
- Add pytest markers for new requirement:
  ```python
  pytest.mark.requires_local = pytest.mark.skipif(
      not os.getenv("LOCAL_BASE_URL"),
      reason="LOCAL_BASE_URL not configured"
  )
  ```
- Create test class `TestLocalIntegration`
- Write integration test methods:
  - `test_local_chat_completion()` - Test basic chat with local model
  - `test_local_streaming_response()` - Test streaming with local model
  - `test_local_with_tools()` - Test function calling (if supported by ai/phi4)
  - `test_local_multi_turn_conversation()` - Test conversation continuity
- Mark all tests with `@pytest.mark.llm`, `@pytest.mark.integration`, `@pytest.mark.requires_local`
- Use real configuration from environment (not mocks)
- Follow patterns from `test_gemini_integration.py`

### 6. Update Documentation

#### README.md Updates:
- Line 37: Change `"Supports OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, and Google Gemini."`
- To: `"Supports OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, Google Gemini, and Local (Docker Models)."`
- Line 48: Add new line after Gemini:
  ```markdown
  - [Docker Desktop](https://www.docker.com/products/docker-desktop/) - Local model serving (ai/phi4, etc.)
  ```

#### docs/design/usage.md Updates:
- Add new section "Using Local Models with Docker":
  ```markdown
  ## Using Local Models with Docker

  Run agent-base completely offline using Docker Desktop's model serving:

  ### Setup

  ```bash
  # 1. Install Docker Desktop (includes model serving)
  # Download from https://www.docker.com/products/docker-desktop/

  # 2. Pull a model (ai/phi4 recommended)
  docker model pull ai/phi4

  # 3. Start the model server (automatic via Docker Desktop)
  # Models are served at http://localhost:8080

  # 4. Configure agent-base
  export LLM_PROVIDER=local
  export LOCAL_MODEL=ai/phi4

  # 5. Run agent
  agent
  ```

  ### Benefits
  - **No API costs** - Completely free to run
  - **Offline operation** - Works without internet
  - **Data privacy** - All data stays on your machine
  - **Fast iteration** - No network latency

  ### Limitations
  - Requires Docker Desktop with sufficient RAM
  - Model quality varies (ai/phi4 is capable but not GPT-4 level)
  - Function calling support depends on model
  - First run downloads large model files
  ```

### 7. Create Architecture Decision Record

- Create `docs/decisions/0016-local-provider-integration.md`
- Follow ADR template structure:
  - **Status**: Accepted
  - **Context**: Docker Desktop provides local model serving, users need offline/free option
  - **Decision**: Support local provider using OpenAI client with custom base_url
  - **Alternatives Considered**:
    1. Ollama integration (rejected - different API, requires separate install)
    2. LM Studio integration (rejected - less standardized, more setup)
    3. Custom local provider (rejected - unnecessary complexity)
    4. No local support (rejected - users have clear need)
  - **Consequences**:
    - Positive: Reuses OpenAI client, minimal code, leverages Docker ecosystem
    - Negative: Depends on Docker Desktop, limited to OpenAI-compatible models
    - Neutral: Another provider to maintain, documentation overhead
  - **Implementation Details**: Document configuration, validation approach
  - **Future Considerations**: Multi-model support, model management, health checks
  - **References**: Link to Docker models docs, OpenAI API compatibility
  - **Date**: 2025-11-10

### 8. Run Validation Commands

Execute all validation commands to ensure zero regressions and confirm feature works:

- Run unit tests for configuration:
  ```bash
  uv run pytest tests/unit/core/test_config_local.py -v
  ```
- Run all unit tests to check for regressions:
  ```bash
  uv run pytest -m "unit" -n auto
  ```
- Run code quality checks:
  ```bash
  uv run black src/agent/ tests/
  uv run ruff check --fix src/agent/ tests/
  uv run mypy src/agent/
  ```
- Run all free tests with coverage:
  ```bash
  uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85
  ```
- **If Docker with ai/phi4 is available**, run local integration tests:
  ```bash
  docker model pull ai/phi4
  export LLM_PROVIDER=local
  export LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1
  export LOCAL_MODEL=ai/phi4
  uv run pytest -m "requires_local" -v
  ```
- Test end-to-end with local provider (manual verification):
  ```bash
  uv run agent --check  # Should show "Local/ai/phi4" as provider
  uv run agent -p "Say hello"  # Should get response from local model
  ```

## Testing Strategy

### Unit Tests

**Location**: `tests/unit/core/test_config_local.py`

**Coverage areas**:
- Configuration loading from environment variables
- Default values for `local_base_url` and `local_model`
- Validation logic (requires base_url, no API key needed)
- Display name generation (`"Local/ai/phi4"`)
- Model override via `AGENT_MODEL`
- Invalid configuration handling

**Mocking strategy**:
- Mock environment variables using `monkeypatch` fixture
- No need for chat client mocking (config-only tests)
- Use `assert` statements for validation checks

**Coverage target**: 100% of new configuration code paths

### Integration Tests

**Location**: `tests/integration/llm/test_local_integration.py`

**Coverage areas**:
- Basic chat completion with local model
- Streaming response handling
- Multi-turn conversation state
- Function calling (if ai/phi4 supports it)
- Error handling for unavailable Docker service
- Session persistence with local provider

**Test requirements**:
- Docker Desktop installed and running
- ai/phi4 model pulled (`docker model pull ai/phi4`)
- `LOCAL_BASE_URL` environment variable set
- Real API calls (not mocked)

**Markers**: `@pytest.mark.llm`, `@pytest.mark.integration`, `@pytest.mark.requires_local`

**Note**: These tests are opt-in due to Docker requirement, similar to cloud LLM tests

### Edge Cases

1. **Docker not running**:
   - Test: Validate error message when `LOCAL_BASE_URL` is unreachable
   - Expected: Connection error with helpful message

2. **Missing base_url configuration**:
   - Test: `validate()` should raise ValueError
   - Expected: Clear error message explaining LOCAL_BASE_URL requirement

3. **Model not pulled**:
   - Test: API call with non-existent model name
   - Expected: Docker API error, suggest `docker model pull`

4. **Custom base_url (different port)**:
   - Test: Use `LOCAL_BASE_URL=http://localhost:9000/v1`
   - Expected: Agent connects to custom endpoint successfully

5. **Model override**:
   - Test: Set `AGENT_MODEL=llama3.2` while `LLM_PROVIDER=local`
   - Expected: Uses llama3.2 instead of default ai/phi4

6. **Concurrent requests**:
   - Test: Multiple agent instances using local provider
   - Expected: All instances can connect and get responses

## Acceptance Criteria

**Feature is considered complete when:**

1. ✅ Configuration accepts `LLM_PROVIDER=local` with `LOCAL_BASE_URL` and `LOCAL_MODEL`
2. ✅ Agent successfully creates OpenAI client pointing to Docker endpoint
3. ✅ Validation passes with base_url, no API key required
4. ✅ Display name shows `"Local/ai/phi4"` (or configured model)
5. ✅ Unit tests pass with 100% coverage of new configuration paths
6. ✅ Integration tests pass when Docker with ai/phi4 is available
7. ✅ All existing tests pass (zero regressions)
8. ✅ Code quality checks pass (black, ruff, mypy)
9. ✅ Overall test coverage remains ≥85%
10. ✅ `.env.example` documents local provider configuration
11. ✅ README lists local provider in supported providers
12. ✅ docs/design/usage.md includes local provider setup guide
13. ✅ ADR-0016 documents architectural decisions
14. ✅ Manual testing confirms end-to-end functionality with Docker models
15. ✅ Agent works offline when using local provider

## Validation Commands

Execute every command to validate the feature works correctly with zero regressions:

```bash
# 1. Unit tests for new configuration code
uv run pytest tests/unit/core/test_config_local.py -v

# 2. All unit tests (verify no regressions)
uv run pytest -m "unit" -n auto

# 3. Code quality (formatting, linting, type checking)
uv run black src/agent/ tests/
uv run ruff check --fix src/agent/ tests/
uv run mypy src/agent/

# 4. All free tests with coverage (CI equivalent)
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# 5. Generate coverage report (optional, for review)
uv run pytest -m "not llm" --cov=src/agent --cov-report=html

# 6. Local integration tests (requires Docker + ai/phi4)
# Setup first:
docker model pull ai/phi4
export LLM_PROVIDER=local
export LOCAL_BASE_URL=http://localhost:12434/engines/llama.cpp/v1
export LOCAL_MODEL=ai/phi4

# Run tests:
uv run pytest tests/integration/llm/test_local_integration.py -v -s

# 7. Configuration validation
uv run agent --check
# Expected output: "Local/ai/phi4" as model

# 8. End-to-end chat test
uv run agent -p "Say hello in one sentence"
# Expected: Response from local ai/phi4 model

# 9. Interactive session test (manual)
uv run agent
# Expected: Agent starts with "Local/ai/phi4", accepts prompts

# 10. Session persistence test (manual)
uv run agent
# In agent: "Remember: my favorite color is blue"
# Exit and restart agent
# In agent: "What is my favorite color?"
# Expected: Agent recalls "blue" from saved session

# 11. Verify all markers work
uv run pytest --markers | grep requires_local
# Expected: "requires_local" marker is registered
```

## Notes

### Implementation Approach Rationale

We're reusing the `OpenAIChatClient` with a custom `base_url` rather than creating a custom provider for several reasons:

1. **Docker models are OpenAI-compatible** - They implement the same API contract as OpenAI, making the OpenAI client a perfect fit
2. **Minimize code complexity** - No need for custom message conversion, tool mapping, or streaming logic
3. **Proven reliability** - OpenAI client is battle-tested and well-maintained by Microsoft
4. **Consistent behavior** - Users get identical behavior to OpenAI provider, just with local endpoint
5. **Future compatibility** - Any improvements to OpenAI client automatically benefit local provider

### Docker Models Background

Docker Desktop includes model serving capabilities that:
- Automatically serve pulled models via OpenAI-compatible API
- Run at `http://localhost:8080` by default
- Support multiple models (ai/phi4, llama, etc.)
- Require no authentication (local-only)
- Work offline once models are downloaded

### Model Recommendations

**ai/phi4** is recommended as the default because:
- Excellent performance for size (~7B parameters)
- Good instruction following and reasoning
- Fast inference on consumer hardware
- Supports function calling
- Well-tested with OpenAI-compatible APIs

Alternative models to consider:
- `llama3.2` - Meta's latest, very capable
- `mistral` - Strong multilingual support
- `codellama` - Optimized for code tasks

### Future Enhancements

Consider for follow-up work:

1. **Model health check** - Ping endpoint before agent start, show helpful error if Docker not running
2. **Multi-model support** - Allow switching models mid-session
3. **Model management UI** - CLI commands to list, pull, remove models
4. **Performance metrics** - Track local model latency vs cloud providers
5. **Ollama support** - Similar integration for Ollama-served models (different API)
6. **Model download progress** - Show progress when pulling large models
7. **Memory optimization** - Guidance on Docker resource allocation for models

### Dependencies

**No new dependencies required!** This feature leverages:
- Existing `agent-framework` package (includes OpenAI client)
- Docker Desktop (user-provided, not a Python dependency)

### Breaking Changes

**None.** This is a purely additive feature:
- New configuration fields are optional
- Existing providers unchanged
- No changes to public APIs
- Backward compatible with all existing configurations
