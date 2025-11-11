---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Title: Testing Strategy and Coverage Targets

## Context and Problem Statement

We need a comprehensive testing strategy that provides confidence in the codebase while being maintainable and efficient. This includes decisions about unit vs integration tests, mocking strategies, coverage targets, and test organization.

## Decision Drivers

- **Confidence**: Tests should catch regressions
- **Speed**: Fast feedback loop for developers
- **Maintainability**: Tests should be easy to update
- **Coverage**: Sufficient but not excessive
- **Isolation**: Unit tests should be independent

## Considered Options

1. **Unit + Integration tests with 85% coverage target**
2. **Only integration tests with 70% coverage target**
3. **Unit + Integration + E2E tests with 95% coverage target**

## Decision Outcome

Chosen option: **"Unit + Integration tests with 85% coverage target"**

This provides the best balance of confidence, speed, and maintainability. Unit tests for business logic isolation, integration tests for full-stack verification, and realistic coverage expectations.

### Testing Strategy

**Unit Tests:**
- Test components in isolation
- Mock all dependencies
- Target: 100% coverage for business logic
- Location: `tests/unit/`

**Integration Tests:**
- Test full stack with mocked LLM
- Verify component interactions
- Target: Cover happy paths and major errors
- Location: `tests/integration/`

**Overall Target:** 85% coverage (enforced by CI)

### Consequences

**Good:**
- Fast unit tests (no I/O)
- Integration tests catch integration issues
- 85% is achievable and meaningful
- Mocking enables testing without LLM calls
- Clear test organization

**Neutral:**
- Need to maintain mocks
- Some code excluded (display, CLI)

**Bad:**
- No E2E tests (acceptable for MVP)
- Some edge cases may not be covered

## Testing Patterns

### Unit Test Example

```python
@pytest.mark.asyncio
async def test_hello_world_default_name(hello_tools):
    """Test hello_world with default name."""
    result = await hello_tools.hello_world()

    assert result["success"] is True
    assert result["result"] == "Hello, World!"
```

**Characteristics:**
- Fast (no I/O)
- Isolated (mocked dependencies)
- Focused (one behavior)

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_agent_with_hello_tools():
    """Test full agent integration."""
    config = AgentConfig(llm_provider="openai", openai_api_key="test")
    mock_client = MockChatClient(response="Test")
    agent = Agent(config=config, chat_client=mock_client)

    response = await agent.run("Test")
    assert response == "Test"
```

**Characteristics:**
- Tests real interactions
- Mocks only external services (LLM)
- Verifies full stack

## Coverage Exclusions

**Excluded from coverage:**
- `src/agent/__main__.py` - Wrapper only
- `src/agent/utils/__init__.py` - Imports only
- `src/agent/utils/errors.py` - Exception definitions
- `src/agent/cli.py` - CLI display logic (hard to test)

**Rationale:**
- Low value to test
- Mostly formatting/display
- Would require complex mocking

## Mock Strategy

### MockChatClient

Replaces real LLM clients in tests:

```python
mock_client = MockChatClient(response="Test response")
agent = Agent(config=config, chat_client=mock_client)
```

**Benefits:**
- No API calls
- Fast tests
- Predictable responses
- Can test error cases

### Configuration Mocking

```python
@pytest.fixture
def mock_config():
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test-key"
    )
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_config.py       # 20 tests
│   ├── test_events.py       # 13 tests
│   ├── test_hello_tools.py  # 16 tests
│   └── test_agent.py        # 13 tests
├── integration/
│   └── test_hello_integration.py  # 6 tests
└── mocks/
    └── mock_client.py       # Test mocks
```

**Total:** 68 tests

## CI Integration

### GitHub Actions Workflow

```yaml
- name: Run tests with coverage
  run: |
    uv run pytest \
      --cov=src/agent \
      --cov-report=xml \
      --cov-report=term-missing \
      --cov-fail-under=85 \
      -v
```

**Enforcement:**
- CI fails if coverage < 85%
- All tests must pass
- No flaky tests allowed

## Testing Enhancements (Updated 2025-11-09)

**Implemented**:
- ✅ Hierarchical test organization by component (unit/core/, unit/tools/, etc.)
- ✅ Real LLM integration tests in tests/integration/llm/ (opt-in, with cost controls)
- ✅ Comprehensive pytest markers for flexible test selection
- ✅ Test templates for consistent patterns (tests/templates/)
- ✅ Test helpers and utilities (tests/helpers/)
- ✅ Modular fixture organization (tests/fixtures/)
- ✅ CLI validation tests with YAML configuration
- ✅ Total: 246 tests (199 unit, 25 integration, 22 LLM)

**Pytest Markers Added**:
- Test types: `unit`, `integration`, `validation`, `llm`
- Feature areas: `agent`, `tools`, `display`, `cli`, `middleware`, `persistence`, `config`, `events`
- Speed: `fast`, `slow`
- Providers: `requires_openai`, `requires_anthropic`, `requires_azure`

**New Test Structure**:
```
tests/
├── unit/{core,tools,display,cli,middleware,persistence}/  # Organized by component
├── integration/                                            # Mocked LLM integration
├── integration/llm/                                        # Real LLM tests (⚠️ costs money)
├── validation/                                             # CLI validation
├── fixtures/                                               # Modular fixtures
├── helpers/                                                # Test utilities
└── templates/                                              # Test templates
```

See [tests/README.md](../../tests/README.md) for comprehensive guide.

**Future Enhancements**:
- Property-based tests (hypothesis)
- Performance benchmarking framework
- Load testing (concurrent agents)
- Mutation testing
- Snapshot tests for output

## References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Test Infrastructure Guide](../../tests/README.md)

## Related Decisions

- ADR-0006: Class-based Toolset Architecture (enables easy mocking)
- ADR-0002: Repository Infrastructure (CI setup)
- All ADRs benefit from this testing strategy
