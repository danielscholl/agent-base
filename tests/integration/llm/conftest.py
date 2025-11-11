"""Fixtures for real LLM integration tests.

⚠️ These fixtures create agents with REAL LLM clients that make API calls!

Fixtures automatically skip if API keys are not set.
"""

import os

import pytest
import requests

from agent.agent import Agent
from agent.config import AgentConfig


@pytest.fixture
def openai_agent():
    """Create agent with real OpenAI client.

    Automatically skips if OPENAI_API_KEY is not set.

    Example:
        @pytest.mark.llm
        @pytest.mark.requires_openai
        async def test_something(openai_agent):
            response = await openai_agent.run("test")
    """
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set - skipping real LLM test")

    config = AgentConfig(
        llm_provider="openai",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        # Use env var if set, otherwise use same default as main config
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    )

    return Agent(config=config)


@pytest.fixture
def anthropic_agent():
    """Create agent with real Anthropic client.

    Automatically skips if ANTHROPIC_API_KEY is not set.

    Example:
        @pytest.mark.llm
        @pytest.mark.requires_anthropic
        async def test_something(anthropic_agent):
            response = await anthropic_agent.run("test")
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set - skipping real LLM test")

    config = AgentConfig(
        llm_provider="anthropic",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        # Use env var if set, otherwise use same default as main config
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
    )

    return Agent(config=config)


@pytest.fixture
def azure_openai_agent():
    """Create agent with real Azure OpenAI client.

    Automatically skips if Azure credentials are not set.

    Example:
        @pytest.mark.llm
        @pytest.mark.requires_azure
        async def test_something(azure_openai_agent):
            response = await azure_openai_agent.run("test")
    """
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        pytest.skip("Azure OpenAI credentials not set - skipping real LLM test")

    config = AgentConfig(
        llm_provider="azure",
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        # Support both naming conventions, default to gpt-5-codex
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
        or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-codex"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION")
        or os.getenv("AZURE_OPENAI_VERSION", "2025-03-01-preview"),
    )

    return Agent(config=config)


@pytest.fixture
def foundry_agent():
    """Create agent with real Azure AI Foundry client.

    Automatically skips if Azure AI Foundry credentials are not set.

    Note: Requires full project endpoint like:
    https://<account-name>.services.ai.azure.com/api/projects/<project-name>

    Example:
    export AZURE_PROJECT_ENDPOINT=https://dasch-m8kjif04-eastus2.services.ai.azure.com/api/projects/spi-agent
    export AZURE_MODEL_DEPLOYMENT=gpt-4o

    Example:
        @pytest.mark.llm
        @pytest.mark.requires_azure
        async def test_something(foundry_agent):
            response = await foundry_agent.run("test")
    """
    if not os.getenv("AZURE_PROJECT_ENDPOINT"):
        pytest.skip("Azure AI Foundry credentials not set - skipping real LLM test")

    config = AgentConfig(
        llm_provider="foundry",
        azure_project_endpoint=os.getenv("AZURE_PROJECT_ENDPOINT"),
        # Use gpt-5-mini as default (supports tools and matches main config)
        azure_model_deployment=os.getenv("AZURE_MODEL_DEPLOYMENT", "gpt-5-mini"),
    )

    return Agent(config=config)


@pytest.fixture
def gemini_agent():
    """Create agent with real Gemini client.

    Automatically skips if GEMINI_API_KEY is not set.

    Example:
        @pytest.mark.llm
        @pytest.mark.requires_gemini
        async def test_something(gemini_agent):
            response = await gemini_agent.run("test")
    """
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set - skipping real LLM test")

    from agent.config import DEFAULT_GEMINI_MODEL

    config = AgentConfig(
        llm_provider="gemini",
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        # Use env var if set, otherwise use same default as main config
        gemini_model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
    )

    return Agent(config=config)


@pytest.fixture
def local_agent():
    """Create agent with local Docker model client.

    Automatically skips if local models are not available.
    Tries default localhost:12434 first, then checks LOCAL_BASE_URL env var.

    Example:
        @pytest.mark.llm
        @pytest.mark.requires_local
        async def test_something(local_agent):
            response = await local_agent.run("test")
    """
    # Use env var if set, otherwise use default from config
    base_url = os.getenv("LOCAL_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1")

    # Check if local models are available by trying to list models
    # Build models endpoint: base_url/models (e.g., http://localhost:12434/engines/llama.cpp/v1/models)
    models_url = f"{base_url.rstrip('/')}/models"

    try:
        response = requests.get(models_url, timeout=2)
        if response.status_code != 200:
            pytest.skip(f"Local models not available at {base_url} - status {response.status_code}")
    except (requests.RequestException, ConnectionError) as e:
        pytest.skip(f"Local models not available at {base_url} - {e}")

    config = AgentConfig(
        llm_provider="local",
        local_base_url=base_url,
        # Use env var if set, otherwise use same default as main config
        local_model=os.getenv("LOCAL_MODEL", "ai/phi4"),
    )

    return Agent(config=config)


@pytest.fixture(autouse=True)
def track_llm_test_cost(request):
    """Track estimated cost of LLM tests (autouse for all tests in this directory).

    This is a simple implementation - actual costs depend on prompt/response length.
    """

    # Cost tracking happens here
    yield

    # After test completes, could log cost
    # For now, just a placeholder for future cost tracking implementation


def pytest_configure(config):
    """Print cost warning when LLM tests are about to run."""
    if config.option.markexpr and "llm" in config.option.markexpr:
        print("\n" + "=" * 70)
        print("⚠️  RUNNING REAL LLM TESTS - THESE MAKE API CALLS AND COST MONEY")
        print("=" * 70)
        print("\n💰 Estimated cost: ~$0.005 per test run")
        print("📊 Target: < $0.01 total for all LLM tests\n")


def pytest_collection_modifyitems(config, items):
    """Mark all tests in this directory with @pytest.mark.llm."""
    llm_path_marker = "integration/llm"

    for item in items:
        if llm_path_marker in str(item.fspath):
            item.add_marker(pytest.mark.llm)
            item.add_marker(pytest.mark.slow)
