---
status: accepted
contact: danielscholl
date: 2025-11-20
deciders: danielscholl
---

# Skill Progressive Discovery with Dynamic Context Injection

## Context and Problem Statement

Skills currently inject full SKILL.md documentation into the system prompt at agent initialization, adding 60-80% token overhead to every request regardless of whether the skill is used. A single skill like hello-extended adds ~1200 tokens of documentation that is sent with every LLM request, even for unrelated queries like "What is 2+2?". How can we implement progressive disclosure for skill documentation to reduce this overhead?

## Decision Drivers

- **Token Efficiency**: Reduce baseline token usage by 60-80% for non-skill requests
- **Progressive Disclosure**: Align with skills architecture principle of loading content only when needed
- **Framework Alignment**: Use Agent Framework's intended patterns
- **Backward Compatibility**: Existing skills should work without modification
- **Performance**: Skill matching must add minimal latency (<5ms)
- **Reliability**: Must not introduce false negatives (skill unavailable when needed)

## Considered Options

1. **ContextProvider with keyword matching** - Dynamic injection based on trigger keywords
2. **Tiered documentation** - Split SKILL.md into brief/full content
3. **Semantic matching with embeddings** - ML-based relevance detection
4. **Middleware-based injection** - Attempt to inject via middleware
5. **Keep current static injection** - No change (status quo)

## Decision Outcome

Chosen option: **"ContextProvider with keyword matching"**, because:

- **Framework Native**: Uses Agent Framework's ContextProvider pattern (same as memory)
- **Proven Pattern**: MemoryContextProvider successfully implements similar dynamic injection
- **Simple & Fast**: Keyword matching is predictable, no external dependencies
- **High Impact**: Delivers 60-80% token reduction immediately
- **Extensible**: Can enhance with semantic matching in Phase 2 if needed
- **Low Risk**: False negatives mitigated by comprehensive trigger keywords

### Implementation Pattern

**Dynamic Injection via ContextProvider:**
```python
class SkillContextProvider(ContextProvider):
    """Inject skill instructions dynamically based on request relevance."""

    async def invoking(self, messages, **kwargs) -> Context:
        # 1. Extract user message
        user_message = self._get_latest_user_message(messages)

        # 2. Match skills using trigger keywords
        relevant_skills = self._match_skills(user_message)

        # 3. Inject only matched skill instructions
        if relevant_skills:
            instructions = "\n\n## Available Skills\n\n" + "\n\n".join([
                f"# {skill['name']}\n{skill['instructions']}"
                for skill in relevant_skills[:self.max_skills]
            ])
            return Context(instructions=instructions)

        return Context()  # No skills matched - no injection
```

**Keyword Matching (Phase 1):**
```python
def _match_skills(self, message: str) -> list[dict]:
    """Match skills to message using keyword triggers."""
    message_lower = message.lower()
    matched = []

    for skill in self.skill_registry.get_all_metadata():
        for trigger in skill.get("triggers", []):
            if trigger.lower() in message_lower:
                matched.append(skill)
                break

    return matched
```

**Skill Manifest Enhancement:**
```yaml
---
name: hello-extended
description: Multi-language greeting tool
triggers: ["greet", "hello", "bonjour", "hola", "greeting"]
---

# hello-extended

This skill provides multi-language greetings.
...
```

**Agent Integration:**
```python
# In Agent._create_agent()
if hasattr(self, "skill_registry") and self.skill_registry.has_skills():
    from agent.skills.context_provider import SkillContextProvider
    skill_provider = SkillContextProvider(self.skill_registry, max_skills=3)
    context_providers.append(skill_provider)
```

### Architecture Changes

**Before (Static Injection):**
```
Agent.__init__()
  → SkillLoader.load_enabled_skills()
      → Returns: skill_instructions list (ALL full docs)
  → Store: self.skill_instructions

Agent._create_agent()
  → instructions = load_system_prompt()
  → instructions += "\n\n## Available Skills\n\n" + join(skill_instructions)
  → Create agent with static instructions
  → EVERY request includes ALL skill docs
```

**After (Dynamic Injection):**
```
Agent.__init__()
  → SkillLoader.load_enabled_skills()
      → Returns: skill_registry (metadata + instructions)
  → Store: self.skill_registry

Agent._create_agent()
  → instructions = load_system_prompt()
  → NO skill instruction injection here
  → Create SkillContextProvider(skill_registry)
  → Create agent with context_providers=[..., skill_provider]

Per Request:
  → SkillContextProvider.invoking(messages)
      → Extract user message
      → Match to relevant skills via triggers
      → Return Context(instructions=relevant_docs)
  → LLM sees ONLY matched skill docs
```

### Token Impact

**Example Measurements:**

| Request Type | Before (tokens) | After (tokens) | Reduction |
|-------------|----------------|---------------|-----------|
| "What is 2+2?" | 3500 | 1200 | 66% |
| "Say bonjour to Alice" | 3500 | 2400 | 31% |
| "Calculate pi" | 3500 | 1200 | 66% |

**Assumptions:**
- Baseline system prompt: 1000 tokens
- User message: 10-50 tokens
- Skill docs (all): 2500 tokens
- Skill docs (matched 1 skill): 1200 tokens

## Consequences

### Positive

- **Token Reduction**: 60-80% fewer tokens for non-skill requests
- **Faster Inference**: Smaller context = faster LLM responses
- **Lower Cost**: Fewer input tokens = reduced API costs
- **True Progressive Disclosure**: Skills documentation lazy-loaded like scripts
- **Framework Aligned**: Uses ContextProvider pattern (same as memory)
- **Extensible**: Can enhance matching in Phase 2 without architectural changes

### Neutral

- **Skill Manifest Changes**: Skills need `triggers` field (backward compatible - optional)
- **Matching Logic**: Simple keyword matching Phase 1, can enhance later
- **Max Skills Limit**: Default 3 skills per request to prevent overflow

### Negative

- **False Negative Risk**: Skill might not match when needed if triggers incomplete
  - *Mitigation*: Comprehensive trigger keywords in manifests
  - *Mitigation*: Can add "show all skills" fallback mode in Phase 2
- **Minimal Latency**: Keyword matching adds ~1-5ms per request
  - *Acceptable*: Keyword search is simple string operations
  - *Future*: Can add caching if needed

## Why Not Other Options?

### Option 2: Tiered Documentation

**Rejected** because:
- Requires skill authors to maintain two doc levels (brief/full)
- Less dynamic than ContextProvider approach
- Still includes brief docs for all skills in every request
- More complexity for skill authors

### Option 3: Semantic Matching

**Deferred to Phase 2** because:
- Adds external dependency (embedding model)
- Increases latency (inference time)
- Higher complexity for 80% solution
- Can add later without architectural changes

### Option 4: Middleware-Based Injection

**Rejected** because:
- Agent Framework middleware only sees input messages
- Not designed for context injection (per ADR-0013)
- ContextProvider is the proper abstraction for this use case

### Option 5: Keep Current Static Injection

**Rejected** because:
- Violates progressive disclosure principle
- Wastes 60-80% of tokens on irrelevant content
- Contradicts skills architecture goals

## Related Decisions

- [ADR-0013: Memory Architecture](./0013-memory-architecture.md) - ContextProvider pattern precedent
- [ADR-0012: Middleware Integration Strategy](./0012-middleware-integration-strategy.md) - Why not middleware
- [ADR-0017: Tool Docstring Optimization](./0017-tool-docstring-optimization.md) - Similar token reduction effort

## References

- [Skills Architecture Design](../design/skills.md) - Progressive disclosure principle
- [Bug Fix Spec](../specs/bug-skill-progressive-discovery.md) - Implementation details
- [MemoryContextProvider](../../src/agent/memory/context_provider.py) - Pattern reference
