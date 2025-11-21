"""Unit tests for SkillContextProvider.

Tests progressive skill documentation injection and trigger matching.
"""

import pytest
from agent_framework import Context

from agent.skills.context_provider import SkillContextProvider
from agent.skills.documentation_index import SkillDocumentationIndex
from agent.skills.manifest import SkillManifest, SkillTriggers


class MockMessage:
    """Mock ChatMessage for testing."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


@pytest.fixture
def skill_docs():
    """Create a SkillDocumentationIndex with test skills."""
    docs = SkillDocumentationIndex()

    # Skill 1: hello-extended with triggers
    manifest1 = SkillManifest(
        name="hello-extended",
        description="Multi-language greeting tool for personalized messages",
        brief_description="Multi-language greetings and translations",
        triggers=SkillTriggers(
            keywords=["hello", "greet", "bonjour", "hola", "greeting"],
            verbs=["greet", "welcome", "say"],
            patterns=[r"say .* in .*", r"greet .* in .*"],
        ),
        instructions="# hello-extended\n\nProvides greeting functionality in multiple languages.",
    )
    docs.add_skill("hello-extended", manifest1)

    # Skill 2: calculator with triggers
    manifest2 = SkillManifest(
        name="calculator",
        description="Perform mathematical calculations",
        triggers=SkillTriggers(
            keywords=["calculate", "math", "compute"],
            verbs=["calculate", "compute", "add", "subtract"],
            patterns=[r"\d+\s*[\+\-\*/]\s*\d+"],
        ),
        instructions="# calculator\n\nPerforms basic math operations.",
    )
    docs.add_skill("calculator", manifest2)

    # Skill 3: weather (no custom triggers, only skill name as implicit trigger)
    manifest3 = SkillManifest(
        name="weather",
        description="Get weather information",
        instructions="# weather\n\nFetches current weather data.",
    )
    docs.add_skill("weather", manifest3)

    return docs


@pytest.fixture
def provider(skill_docs):
    """Create a SkillContextProvider with test skills."""
    return SkillContextProvider(skill_docs, max_skills=3, max_all_skills=10)


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_minimal_breadcrumb_when_no_match(provider):
    """Test that minimal breadcrumb is injected when skills exist but don't match."""
    messages = [MockMessage("user", "What is the capital of France?")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "[3 skills available]" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_injects_documentation_for_matched_skills(provider):
    """Test that full documentation is injected when skills match."""
    messages = [MockMessage("user", "Say hello in French")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "## Relevant Skill Documentation" in result.instructions
    assert "hello-extended" in result.instructions
    assert (
        "Multi-language greetings" in result.instructions
        or "greeting functionality" in result.instructions
    )


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_registry_only_on_user_request(provider):
    """Test that skill registry is shown when user asks about capabilities."""
    messages = [MockMessage("user", "What can you do?")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "## Available Skills" in result.instructions
    assert "hello-extended" in result.instructions
    assert "calculator" in result.instructions
    assert "weather" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_escape_hatch_shows_all_skills_with_cap(provider):
    """Test that 'show all skills' escape hatch works with cap."""
    messages = [MockMessage("user", "Show all skills")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "## Relevant Skill Documentation" in result.instructions
    # Should show all 3 skills since we're under the cap of 10
    assert "hello-extended" in result.instructions
    assert "calculator" in result.instructions
    assert "weather" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_escape_hatch_truncates_when_over_cap():
    """Test that 'show all skills' is capped to prevent overflow."""
    # Create many skills to exceed cap
    docs = SkillDocumentationIndex()
    for i in range(15):
        manifest = SkillManifest(
            name=f"skill-{i}",
            description=f"Test skill {i}",
            instructions=f"# skill-{i}\n\nTest skill {i} documentation.",
        )
        docs.add_skill(f"skill-{i}", manifest)

    provider = SkillContextProvider(docs, max_skills=3, max_all_skills=10)
    messages = [MockMessage("user", "List all skills")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    # Should show message about truncation
    assert "Showing 10 of 15 skills" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_word_boundary_matching_prevents_false_positives(provider):
    """Test that word boundaries prevent false positives (e.g., 'run' vs 'runner')."""
    messages = [MockMessage("user", "I'm a runner and I like running")]

    result = await provider.invoking(messages)

    # Should only show breadcrumb, not match any skill
    assert isinstance(result, Context)
    assert result.instructions == "[3 skills available]"


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_invalid_regex_handled_gracefully():
    """Test that invalid regex patterns are handled gracefully."""
    docs = SkillDocumentationIndex()
    manifest = SkillManifest(
        name="bad-regex",
        description="Skill with invalid regex",
        triggers=SkillTriggers(
            patterns=["[invalid(regex"],  # Invalid regex
        ),
        instructions="# bad-regex\n\nTest skill with invalid regex.",
    )
    docs.add_skill("bad-regex", manifest)

    provider = SkillContextProvider(docs, max_skills=3)
    messages = [MockMessage("user", "test message")]

    # Should not crash, just return breadcrumb
    result = await provider.invoking(messages)
    assert isinstance(result, Context)
    assert result.instructions == "[1 skills available]"


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_fallback_to_skill_name_when_no_triggers(provider):
    """Test that skill name works as fallback when no custom triggers defined."""
    messages = [MockMessage("user", "What's the weather like?")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "## Relevant Skill Documentation" in result.instructions
    assert "weather" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_skill_name_as_implicit_trigger(provider):
    """Test that skill name always works as implicit trigger."""
    messages = [MockMessage("user", "Use the calculator skill")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "## Relevant Skill Documentation" in result.instructions
    assert "calculator" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_respects_max_skills_limit():
    """Test that max_skills limit is respected when multiple skills match."""
    # Create 5 skills with same trigger
    docs = SkillDocumentationIndex()
    for i in range(5):
        manifest = SkillManifest(
            name=f"skill-{i}",
            description=f"Test skill {i}",
            triggers=SkillTriggers(keywords=["test"]),
            instructions=f"# skill-{i}\n\nTest skill {i} documentation.",
        )
        docs.add_skill(f"skill-{i}", manifest)

    provider = SkillContextProvider(docs, max_skills=2)  # Limit to 2
    messages = [MockMessage("user", "I want to test something")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    # Count how many skills are in the result by counting "### skill-" headers
    skill_count = result.instructions.count("### skill-")
    assert skill_count <= 2


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_pattern_based_matching_with_error_handling(provider):
    """Test that pattern-based matching works correctly."""
    messages = [MockMessage("user", "Say hello in Spanish")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "hello-extended" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_verb_based_matching_with_boundaries(provider):
    """Test that verb-based triggers work with word boundaries."""
    messages = [MockMessage("user", "Please calculate 5 + 3")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "calculator" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_keyword_matching_case_insensitive(provider):
    """Test that keyword matching is case-insensitive."""
    messages = [MockMessage("user", "GREET the user")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    assert "hello-extended" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_no_injection_when_no_skills():
    """Test that nothing is injected when no skills are loaded."""
    empty_docs = SkillDocumentationIndex()
    provider = SkillContextProvider(empty_docs, max_skills=3)
    messages = [MockMessage("user", "Hello world")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    # Should have empty or no instructions
    assert not result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_multiple_skills_matched_correctly(provider):
    """Test that multiple skills can be matched in one message."""
    messages = [MockMessage("user", "Greet me and calculate 2+2")]

    result = await provider.invoking(messages)

    assert isinstance(result, Context)
    assert result.instructions
    # Both skills should be in the result
    assert "hello-extended" in result.instructions
    assert "calculator" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_skill_without_instructions_still_discoverable():
    """Test that skills without instructions are still in registry and can match triggers."""
    docs = SkillDocumentationIndex()

    # Skill with triggers but no instructions
    manifest = SkillManifest(
        name="api-client",
        description="API client for external services",
        triggers=SkillTriggers(keywords=["api", "request", "fetch"]),
        instructions="",  # Empty instructions
    )
    docs.add_skill("api-client", manifest)

    provider = SkillContextProvider(docs, max_skills=3)

    # Should appear in capabilities list even without instructions
    messages = [MockMessage("user", "What can you do?")]
    result = await provider.invoking(messages)
    assert "api-client" in result.instructions
    assert "API client for external services" in result.instructions

    # Should match on triggers even without instructions
    messages = [MockMessage("user", "Make an api request")]
    result = await provider.invoking(messages)
    assert "api-client" in result.instructions


@pytest.mark.unit
@pytest.mark.skills
@pytest.mark.asyncio
async def test_hybrid_fallback_no_triggers_uses_registry():
    """Test that hybrid tier-1 uses registry when no skills have triggers."""
    # Create skills WITHOUT any triggers (empty SkillTriggers with no keywords)
    skill_docs = SkillDocumentationIndex()

    # Add skill with completely empty triggers
    manifest1 = SkillManifest(
        name="skill1",
        description="Test skill 1",
        instructions="Skill 1 documentation",
        triggers=SkillTriggers(),  # Empty - no keywords, verbs, or patterns
    )
    # Clear the implicit skill name that model_post_init adds
    manifest1.triggers.keywords = []
    skill_docs.add_skill("skill1", manifest1)

    manifest2 = SkillManifest(
        name="skill2",
        description="Test skill 2",
        instructions="Skill 2 documentation",
        triggers=SkillTriggers(),  # Empty
    )
    manifest2.triggers.keywords = []
    skill_docs.add_skill("skill2", manifest2)

    provider = SkillContextProvider(skill_docs, max_skills=3)

    # Non-matching message
    messages = [MockMessage("user", "some random query")]
    result = await provider.invoking(messages)

    # Should inject registry (not breadcrumb) because no skills have triggers
    assert isinstance(result, Context)
    assert result.instructions
    assert "## Available Skills" in result.instructions
    assert "skill1" in result.instructions
    assert "skill2" in result.instructions
    # Should NOT be just a breadcrumb
    assert result.instructions != "[2 skills available]"
