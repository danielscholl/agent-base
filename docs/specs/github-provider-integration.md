# Feature

GitHub Models Provider Integration

# Feature Description

Add support for GitHub Models as a new LLM provider in agent-base, enabling users to leverage GitHub's AI models through the Azure AI Inference SDK. This integration will provide access to models like Meta Llama, Phi, and other models available through GitHub's model catalog at `https://models.github.ai`. The provider will support both `GITHUB_TOKEN` environment variable authentication and `gh auth token` CLI authentication, following established multi-provider patterns in the codebase.

GitHub Models offers free tier access for developers and integrates seamlessly with GitHub's development workflow, making it an attractive option for users already working within the GitHub ecosystem. This provider expands the agent-base's multi-provider architecture to seven total providers (Local, OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, Google Gemini, and GitHub Models).

# User Story

As a developer using GitHub for my projects
I want to use GitHub Models as my LLM provider
So that I can leverage free tier AI models, stay within the GitHub ecosystem, and avoid managing separate API keys from other providers

# Problem Statement

Agent-base currently supports six LLM providers (Local, OpenAI, Anthropic, Azure OpenAI, Azure AI Foundry, Google Gemini), but lacks support for GitHub Models. Users who:

1. Are already authenticated with GitHub via `gh` CLI
2. Want to use GitHub's free tier model access
3. Prefer to consolidate tooling within the GitHub ecosystem
4. Want to experiment with models like Meta Llama or Phi without separate API keys

...currently cannot use agent-base with GitHub Models. This creates a gap for developers who want to leverage GitHub's growing AI infrastructure while using our agent framework.

Additionally, GitHub Models uses the Azure AI Inference SDK with endpoint `https://models.github.ai/inference`, which is compatible with the Azure AI Inference pattern but requires specific GitHub token authentication.

# Solution Statement

Implement a GitHub Models provider using Azure AI Inference SDK's `ChatCompletionsClient`, following the established multi-provider architecture patterns. The implementation will:

1. **Authentication**: Support both `GITHUB_TOKEN` environment variable and `gh auth token` command
2. **Client Implementation**: Use `azure.ai.inference.ChatCompletionsClient` (already available via Azure dependencies)
3. **Configuration**: Add GitHub-specific configuration to the Pydantic schema
4. **Integration Pattern**: Follow the "Client Reuse with Custom Authentication" pattern similar to Local provider
5. **Testing**: Add comprehensive unit, integration, and LLM tests following existing patterns

This approach:
- Reuses existing `azure-ai-inference` dependency (no new packages needed)
- Follows established provider implementation patterns (ADR-0003)
- Maintains consistency with other provider configurations
- Enables future GitHub-specific features (model catalog integration, etc.)

# Relevant Files

## Existing Files

- **src/agent/config/schema.py** - Add `GitHubProviderConfig` class and update `ProviderConfig`, add "github" to `VALID_PROVIDERS`
- **src/agent/config/defaults.py** - Add default GitHub model constant
- **src/agent/agent.py** - Add GitHub client creation logic in `_create_chat_client()` method
- **src/agent/cli/config_commands.py** - Add interactive GitHub provider setup commands
- **tests/fixtures/config.py** - Add GitHub configuration fixtures
- **tests/unit/config/test_schema.py** - Add GitHub config validation tests
- **tests/unit/core/test_agent.py** - Add GitHub client creation tests
- **tests/integration/llm/conftest.py** - Add GitHub agent fixture
- **pyproject.toml** - Update test markers (add `requires_github`)
- **README.md** - Add GitHub Models to provider list
- **USAGE.md** - Add GitHub Models usage examples
- **docs/design/architecture.md** - Update provider count and matrix

### New Files

- **src/agent/providers/github/__init__.py** - Public API exports for GitHub provider
- **src/agent/providers/github/auth.py** - GitHub token authentication helper (detect `gh` CLI or env var)
- **tests/fixtures/github.py** - Test fixtures for GitHub provider
- **tests/unit/providers/test_github_auth.py** - Unit tests for GitHub authentication
- **tests/integration/llm/test_github_integration.py** - Real API integration tests
- **docs/decisions/0017-github-provider-integration.md** - Architecture Decision Record

# Implementation Plan

## Phase 1: Foundation

### 1.1 Research and Validation
- Validate Azure AI Inference SDK compatibility with GitHub Models endpoint
- Test authentication flow with both `GITHUB_TOKEN` and `gh auth token`
- Verify model listing and available models at `https://models.github.ai`
- Document any GitHub-specific API quirks or limitations

### 1.2 Configuration Schema
- Add `GitHubProviderConfig` Pydantic model to `src/agent/config/schema.py`
- Add "github" to `VALID_PROVIDERS` constant
- Add GitHub-specific fields: `enabled`, `token`, `model`, `endpoint`
- Add validation logic for GitHub provider in `validate_enabled_providers()`
- Add default GitHub model constant to `src/agent/config/defaults.py`

### 1.3 Authentication Helper
- Create `src/agent/providers/github/auth.py` with token detection logic
- Implement `get_github_token()` function:
  - Check `GITHUB_TOKEN` environment variable first
  - Fall back to `gh auth token` command if `gh` CLI is available
  - Raise clear error if neither authentication method available
- Add logging for authentication method used

## Phase 2: Core Implementation

### 2.1 GitHub Provider Module
- Create `src/agent/providers/github/__init__.py`
- Implement exports for public API

### 2.2 Client Creation Logic
- Add GitHub provider case to `Agent._create_chat_client()` in `src/agent/agent.py`
- Use `azure.ai.inference.ChatCompletionsClient` with:
  - `endpoint="https://models.github.ai/inference"`
  - `credential=AzureKeyCredential(token)` from authentication helper
  - `model_id` from configuration
- Add error handling for missing dependencies or authentication failures

### 2.3 Configuration Commands
- Add `config_github_provider()` function to `src/agent/cli/config_commands.py`
- Implement interactive prompts:
  - Model selection (with recommended models: phi-4, llama-3.3-70b-instruct)
  - Authentication method selection (GITHUB_TOKEN vs gh CLI)
  - Token validation with test API call
- Follow existing provider setup patterns (see `_setup_local_provider()`)

## Phase 3: Integration

### 3.1 Display and Health Checks
- Update `get_model_display_name()` in AgentConfig to handle GitHub provider
- Add GitHub provider to health check output in CLI
- Update token masking for GitHub tokens (show last 4 chars)
- Add connectivity test to GitHub Models endpoint in `--check` command

### 3.2 Documentation Updates
- Update `README.md`:
  - Add GitHub Models to supported providers list
  - Add authentication prerequisites
  - Update provider count (6 → 7)
- Update `USAGE.md`:
  - Add GitHub Models usage examples
  - Document authentication methods
  - Add model selection guidance
- Update `docs/design/architecture.md`:
  - Add GitHub to provider matrix
  - Update provider count references

### 3.3 Architecture Decision Record
- Create `docs/decisions/0017-github-provider-integration.md`
- Document:
  - Decision to use Azure AI Inference SDK (reuse existing dependency)
  - Authentication strategy (dual method support)
  - Why this provider adds value (free tier, GitHub ecosystem integration)
  - Future considerations (model catalog API, usage tracking)

# Step by Step Tasks

## 1. Add Configuration Schema

- Add `GitHubProviderConfig` class to `src/agent/config/schema.py`:
  ```python
  class GitHubProviderConfig(BaseModel):
      enabled: bool = False
      token: str | None = None
      model: str = "phi-4"
      endpoint: str = "https://models.github.ai/inference"
  ```
- Add "github" to `VALID_PROVIDERS` set
- Add `github: GitHubProviderConfig` field to `ProviderConfig`
- Update `sync_enabled_flags()` validator to include GitHub
- Update `validate_enabled_providers()` to check GitHub token
- Add `DEFAULT_GITHUB_MODEL = "phi-4"` to `src/agent/config/defaults.py`
- Write unit tests in `tests/unit/config/test_schema.py`:
  - Test GitHub config creation
  - Test validation with missing token
  - Test validation with valid token
  - Test enabled flag syncing

## 2. Create Authentication Helper

- Create `src/agent/providers/github/` directory
- Create `src/agent/providers/github/__init__.py` with exports
- Create `src/agent/providers/github/auth.py`:
  - Implement `get_github_token() -> str` function
  - Check `GITHUB_TOKEN` environment variable first
  - Try `gh auth token` command as fallback
  - Raise `ValueError` with helpful message if neither works
  - Add logging for authentication method
- Write unit tests in `tests/unit/providers/test_github_auth.py`:
  - Test with `GITHUB_TOKEN` env var
  - Test with `gh` CLI available
  - Test error when neither available
  - Mock subprocess calls appropriately

## 3. Add Client Creation Logic

- Update `src/agent/agent.py` in `_create_chat_client()`:
  - Add `elif self.config.llm_provider == "github":` case
  - Import `ChatCompletionsClient` from `azure.ai.inference`
  - Import `AzureKeyCredential` from `azure.core.credentials`
  - Import `get_github_token` from `agent.providers.github.auth`
  - Create client with GitHub endpoint and token
  - Add error handling and logging
- Write unit tests in `tests/unit/core/test_agent.py`:
  - Test GitHub client creation with valid config
  - Test error handling with missing token
  - Mock ChatCompletionsClient to avoid real API calls

## 4. Add CLI Configuration Commands

- Update `src/agent/cli/config_commands.py`:
  - Add `config_github_provider()` function
  - Implement interactive prompts for:
    - Model selection (default: phi-4, options: phi-4, llama-3.3-70b-instruct, etc.)
    - Authentication method (GITHUB_TOKEN or gh CLI)
    - Token detection and validation
  - Add test connectivity with small API call
  - Save configuration to settings file
- Follow pattern from `_setup_local_provider()` for user experience

## 5. Create Test Fixtures

- Create `tests/fixtures/github.py`:
  - Add `github_token()` fixture returning test token
  - Add `github_model()` fixture returning default model
  - Add `github_config()` fixture returning test AgentConfig
  - Add `github_agent()` fixture for LLM tests (requires real token)
- Update `tests/integration/llm/conftest.py`:
  - Add GitHub agent fixture
  - Add skip logic if `GITHUB_TOKEN` not available

## 6. Write Integration Tests

- Create `tests/integration/llm/test_github_integration.py`:
  - Add docstring warning about real API costs
  - Add `@pytest.mark.llm` and `@pytest.mark.requires_github` markers
  - Test basic prompt response
  - Test simple math reasoning
  - Test streaming response
  - Test tool invocation (hello_world)
  - Test error handling
- Follow pattern from `tests/integration/llm/test_gemini_integration.py`

## 7. Update Documentation

- Update `README.md`:
  - Add GitHub Models to provider list in prerequisites table
  - Add authentication requirement (`gh` CLI or GITHUB_TOKEN)
  - Update provider count (6 → 7 providers)
- Update `USAGE.md`:
  - Add GitHub Models setup example
  - Add usage example with `agent --provider github`
  - Document authentication methods
- Update `docs/design/architecture.md`:
  - Add GitHub to provider matrix table
  - Update provider count references
  - Add to "Current Supported Providers" section

## 8. Create Architecture Decision Record

- Create `docs/decisions/0017-github-provider-integration.md`:
  - Document decision to use Azure AI Inference SDK
  - Explain authentication strategy (dual method)
  - List benefits (free tier, GitHub ecosystem)
  - Document alternatives considered
  - Add future considerations
  - Follow ADR template structure

## 9. Update pyproject.toml

- Add `requires_github` marker to test markers list:
  ```toml
  "requires_github: Tests requiring GitHub token"
  ```
- Verify `azure-ai-inference` is already in dependencies (it should be)

## 10. Run Validation Commands

- Run all validation commands (see Validation Commands section)
- Fix any failing tests
- Ensure zero regressions
- Verify feature works end-to-end with both authentication methods

# Testing Strategy

## Unit Tests

### Configuration Tests (`tests/unit/config/test_schema.py`)
- **Test GitHub config creation**: Verify `GitHubProviderConfig` can be instantiated
- **Test validation with missing token**: Verify validation error when GitHub enabled but no token
- **Test validation with valid token**: Verify validation passes with token present
- **Test enabled flag syncing**: Verify `github.enabled` syncs with `enabled` list
- **Test default values**: Verify default model, endpoint, and enabled state

### Authentication Tests (`tests/unit/providers/test_github_auth.py`)
- **Test GITHUB_TOKEN env var**: Verify token detection from environment variable
- **Test gh CLI fallback**: Verify token detection from `gh auth token` command
- **Test no authentication**: Verify clear error when neither method available
- **Test gh CLI not installed**: Verify graceful handling when `gh` command missing
- **Test subprocess errors**: Verify handling of `gh auth token` failures
- **Mock all subprocess calls**: Use `pytest-mock` to avoid real CLI calls

### Agent Core Tests (`tests/unit/core/test_agent.py`)
- **Test GitHub client creation**: Verify `_create_chat_client()` creates GitHub client correctly
- **Test configuration validation**: Verify agent validates GitHub config on initialization
- **Test missing token error**: Verify clear error message when token unavailable
- **Mock ChatCompletionsClient**: Avoid real API calls in unit tests

## Integration Tests

### LLM Integration Tests (`tests/integration/llm/test_github_integration.py`)
⚠️ **WARNING**: These tests make real API calls and may cost money (free tier available)

- **Test basic prompt response**: Verify simple prompt returns valid response
- **Test simple reasoning**: Test basic math/logic with GitHub Models
- **Test streaming response**: Verify streaming works correctly with chunk assembly
- **Test tool invocation**: Verify LLM can call our tools (hello_world)
- **Test tool with parameters**: Verify tool calls with language parameter
- **Test error handling**: Verify graceful error communication to user
- **Mark as opt-in**: Use `@pytest.mark.llm` and `@pytest.mark.requires_github`
- **Skip if no token**: Auto-skip if `GITHUB_TOKEN` not set

### Configuration Integration (`tests/integration/config/test_config_integration.py`)
- **Test full config cycle**: Create, save, load GitHub configuration
- **Test provider switching**: Switch between GitHub and other providers
- **Test validation in context**: Verify validation works with full config file

## Edge Cases

### Authentication Edge Cases
- **Empty GITHUB_TOKEN**: Token exists but is empty string
- **Invalid token format**: Token present but malformed
- **Expired token**: Token expired (should fail with clear message)
- **gh CLI partial install**: `gh` command exists but not configured
- **Permission issues**: Token lacks required scopes

### Configuration Edge Cases
- **Missing endpoint**: Verify default endpoint is used
- **Invalid model name**: Verify error handling for non-existent models
- **Provider disabled mid-session**: Handle provider becoming unavailable
- **Multiple providers enabled**: Verify GitHub works alongside other providers

### API Edge Cases
- **Rate limiting**: Handle GitHub API rate limit responses
- **Network timeouts**: Handle slow/failed API connections
- **Invalid model responses**: Handle unexpected API response formats
- **Streaming interruption**: Handle mid-stream connection failures

### Platform Edge Cases
- **Windows path handling**: Ensure `gh` CLI detection works on Windows
- **macOS credential helper**: Verify integration with macOS keychain via `gh`
- **Linux environments**: Test in containerized environments without `gh` CLI
- **CI/CD environments**: Verify GITHUB_TOKEN env var method in GitHub Actions

# Acceptance Criteria

1. **Configuration Management**
   - ✅ GitHub provider can be enabled/configured via `agent config provider github`
   - ✅ Configuration persists to `~/.agent/settings.json`
   - ✅ Validation detects missing/invalid GitHub tokens with clear error messages
   - ✅ Default model is set appropriately (phi-4)

2. **Authentication**
   - ✅ Supports `GITHUB_TOKEN` environment variable authentication
   - ✅ Supports `gh auth token` CLI authentication as fallback
   - ✅ Provides clear error messages when neither authentication method available
   - ✅ Logs which authentication method is being used

3. **Core Functionality**
   - ✅ Agent can initialize with GitHub provider configuration
   - ✅ Basic prompts return valid responses from GitHub Models
   - ✅ Streaming responses work correctly
   - ✅ Tool invocation works (LLM can call our tools)
   - ✅ Error handling is graceful with user-friendly messages

4. **Testing**
   - ✅ Unit tests achieve >85% coverage for new code
   - ✅ Integration tests pass with mocked clients (free)
   - ✅ LLM integration tests pass with real API (opt-in, marked appropriately)
   - ✅ No regressions in existing tests
   - ✅ All edge cases have corresponding tests

5. **Documentation**
   - ✅ README.md updated with GitHub Models as supported provider
   - ✅ USAGE.md includes GitHub Models setup and usage examples
   - ✅ Architecture documentation updated (provider count, matrix)
   - ✅ ADR-0017 created documenting implementation decisions
   - ✅ Code includes clear docstrings and comments

6. **User Experience**
   - ✅ Health check (`agent --check`) shows GitHub provider status
   - ✅ Provider switching works seamlessly (`agent --provider github`)
   - ✅ Token masking in display (shows last 4 chars only)
   - ✅ Interactive setup guides user through authentication
   - ✅ Clear, actionable error messages for common failures

7. **Quality**
   - ✅ Code follows project style (Black, Ruff, MyPy all pass)
   - ✅ Type hints on all public APIs
   - ✅ Structured error responses following existing patterns
   - ✅ Logging at appropriate levels
   - ✅ No security issues (tokens not logged/displayed)

# Validation Commands

Execute every command to validate the feature works correctly with zero regressions.

## 1. Code Quality Checks
```bash
# Format code with Black
uv run black src/agent/ tests/

# Lint with Ruff
uv run ruff check --fix src/agent/ tests/

# Type check with MyPy
uv run mypy src/agent/
```

## 2. Unit Tests (Free, Fast)
```bash
# Run all unit tests
uv run pytest -m unit -n auto

# Run GitHub-specific unit tests
uv run pytest tests/unit/config/test_schema.py -k github -v
uv run pytest tests/unit/providers/test_github_auth.py -v
uv run pytest tests/unit/core/test_agent.py -k github -v
```

## 3. Integration Tests (Free, No API Calls)
```bash
# Run all integration tests with mocks
uv run pytest -m integration -n auto

# Run config integration tests
uv run pytest tests/integration/config/ -v
```

## 4. Full Test Suite (Free, No LLM Calls)
```bash
# Run complete test suite excluding LLM tests
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# Verify coverage meets 85% threshold
uv run pytest -m "not llm" --cov=src/agent --cov-report=html
open htmlcov/index.html  # Review coverage report
```

## 5. LLM Integration Tests (Costs Money, Opt-In)
```bash
# Set GitHub token for testing
export GITHUB_TOKEN="your-github-token"

# Run GitHub-specific LLM tests
uv run pytest -m "llm and requires_github" -v

# Run all LLM tests to ensure no regressions
uv run pytest -m llm -v
```

## 6. CLI Validation
```bash
# Verify GitHub provider shows in check
uv run agent --check

# Test interactive GitHub configuration
uv run agent config provider github

# Test health check after configuration
uv run agent --check

# Test basic prompt with GitHub provider
uv run agent --provider github -p "Say hello"

# Test interactive mode with GitHub provider
uv run agent --provider github
> Say hello
> exit
```

## 7. Configuration Validation
```bash
# Verify configuration saved correctly
cat ~/.agent/settings.json | jq '.providers.github'

# Test provider switching
uv run agent --provider openai -p "test"  # Should work
uv run agent --provider github -p "test"   # Should work
uv run agent --provider local -p "test"    # Should work
```

## 8. Documentation Validation
```bash
# Verify README mentions GitHub Models
grep -i "github" README.md

# Verify USAGE has GitHub examples
grep -i "github" USAGE.md

# Verify ADR exists
ls docs/decisions/0017-github-provider-integration.md

# Verify architecture docs updated
grep -i "github" docs/design/architecture.md
```

## 9. Regression Testing
```bash
# Ensure all existing provider tests still pass
uv run pytest tests/integration/llm/test_openai_integration.py -v
uv run pytest tests/integration/llm/test_anthropic_integration.py -v
uv run pytest tests/integration/llm/test_gemini_integration.py -v
uv run pytest tests/integration/llm/test_local_integration.py -v

# Ensure existing config tests still pass
uv run pytest tests/unit/config/ -v

# Ensure agent core tests still pass
uv run pytest tests/unit/core/test_agent.py -v
```

## 10. End-to-End Validation
```bash
# Complete workflow test with GitHub provider
export GITHUB_TOKEN="your-token"

# 1. Configure GitHub provider
uv run agent config provider github

# 2. Verify configuration
uv run agent --check

# 3. Test single prompt mode
uv run agent --provider github -p "What is 2+2?"

# 4. Test verbose mode
uv run agent --provider github -p "Say hello" --verbose

# 5. Test interactive mode with memory
uv run agent --provider github
> Remember my name is Alice
> What's my name?
> exit

# 6. Test session persistence
uv run agent --provider github --continue
```

# Notes

## Dependencies

- **No new packages required**: GitHub provider uses `azure-ai-inference` SDK which is already a dependency for Azure providers
- **Optional dependency**: `gh` CLI is optional (authentication can use `GITHUB_TOKEN` env var)
- **Python version**: Requires Python 3.12+ (same as project minimum)

## Model Recommendations

Based on GitHub Models catalog:
- **phi-4** (default): Fast, efficient, good for general tasks (smaller context window)
- **llama-3.3-70b-instruct**: Larger model, better reasoning, higher cost
- **gpt-4o-mini**: OpenAI model available through GitHub (if desired)

The default should be `phi-4` for best balance of performance and cost.

## Authentication Priority

1. **GITHUB_TOKEN environment variable** (checked first)
   - Advantage: Works in CI/CD, containers, any environment
   - Usage: `export GITHUB_TOKEN=ghp_...`

2. **gh auth token command** (fallback)
   - Advantage: Integrates with existing GitHub CLI authentication
   - Usage: User runs `gh auth login` once, token auto-retrieved
   - Limitation: Requires `gh` CLI installed

## Future Considerations

1. **Model Catalog API Integration**
   - Add command to list available models from GitHub's catalog
   - Auto-detect latest model versions
   - Show model capabilities and context limits

2. **Usage Tracking**
   - Track GitHub Models API usage via telemetry
   - Display rate limit information
   - Warn when approaching free tier limits

3. **GitHub-Specific Features**
   - Code completion models (Copilot models)
   - Repository context integration
   - GitHub Actions integration for automated workflows

4. **Cost Optimization**
   - Automatic failover to free tier models when available
   - Usage budgeting and alerts
   - Model recommendation based on prompt characteristics

## Security Notes

- **Token Security**: Tokens must never be logged or displayed in full
- **Token Masking**: Display only last 4 characters (e.g., `****ABC123`)
- **Token Scope**: Recommend minimal scopes required for model access
- **Token Rotation**: Support dynamic token refresh from `gh` CLI
- **CI/CD Safety**: Use secrets management for GITHUB_TOKEN in pipelines

## Implementation Complexity

- **Estimated Effort**: 8-12 hours
  - Configuration schema: 1 hour
  - Authentication helper: 2 hours
  - Client integration: 2 hours
  - CLI commands: 2 hours
  - Testing: 3-4 hours
  - Documentation: 1-2 hours

- **Risk Level**: Low
  - Reuses existing Azure AI Inference SDK
  - Follows established provider patterns
  - Similar to Local provider implementation

## Related Work

- **ADR-0003**: Multi-Provider LLM Architecture Strategy (foundation)
- **ADR-0015**: Gemini Provider Integration (custom client pattern)
- **ADR-0016**: Local Provider Integration (client reuse pattern)
- **GitHub Models Docs**: https://docs.github.com/en/rest/models
- **Azure AI Inference SDK**: https://learn.microsoft.com/en-us/python/api/azure-ai-inference
