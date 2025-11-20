# Bug Fix: Skills Progressive Discovery

## Bug Description

**Current Behavior:**
All skill documentation (full SKILL.md markdown content after YAML frontmatter) is injected into the system prompt at agent initialization and sent with **every LLM request**, regardless of whether the skill will be used in that request.

**Impact:**
- Token overhead of 60-80% on baseline requests that don't use skills
- hello-extended skill alone adds ~1200 tokens of XML documentation
- Multiple skills compound this overhead linearly
- Wastes context window space and increases latency/cost

**Example:**
A skill like `hello-extended` has 47 lines of detailed XML documentation describing tools, triggers, examples, and language mappings. This entire documentation is loaded into the system prompt even for simple requests like "What is 2+2?" that will never use greeting functionality.

## Problem Statement

The current architecture loads full skill instructions at agent initialization (Agent.__init__) and statically injects them into the system prompt (_create_agent), making them part of every LLM request regardless of relevance. This violates the progressive disclosure principle that the skills architecture is designed around.

**Files Affected:**
- src/agent/agent.py:73-148 - Skill instructions collected and stored
- src/agent/agent.py:389-397 - Static injection into system prompt
- src/agent/skills/loader.py:318-320 - Full instructions extracted from manifest

## Solution Statement

Implement dynamic skill instruction injection using Agent Framework's `ContextProvider` pattern. Only inject skill documentation when the user's request is relevant to that skill's capabilities. This follows the proven pattern established by `MemoryContextProvider` (ADR-0013).

**Approach:**
1. Create `SkillContextProvider` that analyzes incoming requests
2. Match requests to relevant skills using trigger keywords
3. Inject only matched skill instructions via `Context(instructions=...)`
4. Keep skill registry for quick metadata access

## Steps to Reproduce

1. Enable a skill (e.g., hello-extended bundled skill)
2. Run agent with trace logging to see token counts:
   ```bash
   export LOG_LEVEL=trace
   export ENABLE_SENSITIVE_DATA=true
   agent -p "What is 2+2?"
   cat ~/.agent/logs/session-*-trace.log | jq '.tokens'
   ```
3. Observe baseline token count includes full skill documentation
4. Compare to expected tokens for just the user message + system prompt (without skills)
5. **Expected:** Skill instructions only present when relevant
6. **Actual:** Skill instructions present in every request

## Root Cause Analysis

### Architectural Root Cause

The skills architecture was designed with progressive disclosure in mind (per docs/design/skills.md):
> "Scripts provide the executable behavior and are loaded only when invoked. This separation keeps context usage low while enabling rich extensibility."

However, **only scripts** follow this pattern. The SKILL.md documentation itself is eagerly loaded:

**In src/agent/skills/loader.py:318-320:**
```python
# Collect skill instructions for system prompt
if manifest.instructions:
    skill_instructions.append(f"# {manifest.name}\n\n{manifest.instructions}")
```

**In src/agent/agent.py:124-125:**
```python
# Store skill instructions for system prompt injection
self.skill_instructions = skill_instructions
```

**In src/agent/agent.py:391-397:**
```python
# Inject skill instructions into system prompt
if hasattr(self, "skill_instructions") and self.skill_instructions:
    skills_section = "\n\n## Available Skills\n\n" + "\n\n".join(self.skill_instructions)
    instructions += skills_section  # Static injection - happens ONCE at agent creation
```

The problem: `instructions` is set **once** at agent creation and reused for all requests. No mechanism exists to conditionally include/exclude content per request.

### Why This Wasn't Caught

1. **Token tracking exists** (lines 127-148) but only logs totals at startup
2. **No token limit validation** - skills can add unlimited tokens
3. **Scripts use progressive disclosure** - created false impression all skill content was lazy-loaded
4. **Testing gap** - No tests validate instructions are conditional/minimal

## Related Documentation

### Requirements
- [docs/design/skills.md](../design/skills.md) - Skills architecture emphasizes "progressive disclosure" and "keeping context usage low"

### Architecture Decisions
- [ADR-0013: Memory Architecture](../decisions/0013-memory-architecture.md) - Establishes ContextProvider as the proper pattern for dynamic context injection
- [ADR-0012: Middleware Integration Strategy](../decisions/0012-middleware-integration-strategy.md) - Documents why middleware is NOT suitable for this use case

### Related Specs
- [docs/specs/skill-architecture.md](skill-architecture.md) - Comprehensive skills architecture spec

## Codebase Analysis Findings

### ContextProvider Pattern (Proven Solution)

**From ADR-0013:**
> "ContextProvider is the Agent Framework's intended pattern for memory. It has both `invoking()` and `invoked()` hooks, receives complete request/response pair, and is the proper abstraction for memory/context injection."

**Key Advantages:**
1. **Dynamic Injection:** Content added via `Context(instructions=...)` in `invoking()` hook
2. **Request-Time Decision:** Evaluates what to inject for each request
3. **Framework Integration:** Uses Agent Framework's official pattern
4. **Proven Pattern:** Successfully used by MemoryContextProvider

**Reference Implementation (src/agent/memory/context_provider.py:45-97):**
```python
async def invoking(self, messages, **kwargs) -> Context:
    """Inject relevant memories before agent invocation."""
    # Analyze current request
    result = await self.memory_manager.retrieve_for_context(messages_dicts, limit=self.history_limit)

    if result.get("success") and result["result"]:
        memories = result["result"]
        context_text = "\n".join(context_parts)
        return Context(instructions=context_text)  # DYNAMIC INJECTION
    else:
        return Context()  # No context if not relevant
```

### Why Middleware Doesn't Work

**From ADR-0013:**
```
Middleware limitations discovered:
- Agent middleware only sees input messages, not LLM responses
- context.messages doesn't accumulate - only contains current request
- No clean way to capture assistant responses
- Middleware is for cross-cutting concerns (logging, metrics), not context
```

However, ContextProvider is designed exactly for **dynamic context injection** before LLM calls.

### Error Patterns in This Codebase

**Pattern:** Static system prompt assembly at agent creation
**Found in:** src/agent/agent.py:_create_agent() (line 383-419)
**Issue:** Assembled once, reused for all requests - no conditional content possible

**Pattern:** Agent Framework's ContextProvider for dynamic injection
**Found in:** src/agent/memory/context_provider.py
**Success:** Proven pattern for injecting content conditionally per request

### Similar Fixes in History

No similar fixes found. This is the first implementation of progressive content injection beyond scripts.

### Dependencies and Side Effects

**Components that depend on skill_instructions:**
1. Agent.__init__ (lines 124-148) - Stores instructions
2. Agent._create_agent (lines 391-397) - Injects into system prompt
3. SkillLoader.load_enabled_skills (lines 318-320) - Extracts from manifests

**Side effects of change:**
1. **Positive:** Reduced token usage (60-80% for non-skill requests)
2. **Neutral:** Skill matching adds minimal latency (~1-5ms)
3. **Negative (risk):** False negatives if matching fails - skill not available when needed

## Relevant Files

### Files to Modify

#### 1. **src/agent/skills/loader.py**
**What needs to be fixed:**
- Line 318-320: Currently extracts full `manifest.instructions`
- Need to also extract `manifest.triggers` for matching

**Changes:**
```python
# BEFORE (line 318-320):
if manifest.instructions:
    skill_instructions.append(f"# {manifest.name}\n\n{manifest.instructions}")

# AFTER:
# Collect skill registry data (metadata + instructions)
skill_registry.register(
    name=canonical_name,
    description=manifest.description,
    triggers=manifest.triggers or [],
    instructions=manifest.instructions or ""
)
```

**Impact:** Change return signature to include SkillRegistry instead of just instructions list

#### 2. **src/agent/skills/registry.py** (existing)
**What needs to be fixed:**
- Currently just stores metadata for script discovery
- Need to add: triggers, instructions for context provider

**Changes:**
- Add `triggers: list[str]` field
- Add `instructions: str` field
- Add method: `get_all_metadata() -> list[dict]`

#### 3. **src/agent/skills/context_provider.py** (NEW FILE)
**Purpose:** Dynamic skill instruction injection

**Implementation:**
```python
"""Skill context provider for dynamic instruction injection."""

from agent_framework import ChatMessage, Context, ContextProvider
from agent.skills.registry import SkillRegistry

class SkillContextProvider(ContextProvider):
    """Inject skill instructions dynamically based on request relevance."""

    def __init__(self, skill_registry: SkillRegistry, max_skills: int = 3):
        self.skill_registry = skill_registry
        self.max_skills = max_skills

    async def invoking(self, messages, **kwargs) -> Context:
        """Inject relevant skill instructions before agent invocation."""
        # 1. Extract latest user message
        user_message = self._get_latest_user_message(messages)
        if not user_message:
            return Context()

        # 2. Match skills based on triggers
        relevant_skills = self._match_skills(user_message)

        # 3. Inject matched skill instructions
        if relevant_skills:
            instructions_parts = [
                f"# {skill['name']}\n{skill['instructions']}"
                for skill in relevant_skills[:self.max_skills]
            ]
            instructions = "\n\n## Available Skills\n\n" + "\n\n".join(instructions_parts)
            return Context(instructions=instructions)

        return Context()

    def _match_skills(self, message: str) -> list[dict]:
        """Match skills to message using keyword triggers."""
        # Simple keyword matching for Phase 1
        # Phase 2: Can add semantic similarity
        message_lower = message.lower()
        matched = []

        for skill in self.skill_registry.get_all_metadata():
            for trigger in skill.get("triggers", []):
                if trigger.lower() in message_lower:
                    matched.append(skill)
                    break

        return matched
```

#### 4. **src/agent/agent.py**
**What needs to be fixed:**

**Lines 73-148 (Agent.__init__):**
```python
# BEFORE:
self.skill_instructions: list[str] = []
self.skill_instructions_tokens: int = 0
skill_toolsets, script_tools, skill_instructions = skill_loader.load_enabled_skills()
self.skill_instructions = skill_instructions

# AFTER:
skill_toolsets, script_tools, skill_registry = skill_loader.load_enabled_skills()
# Store registry instead of static instructions
self.skill_registry = skill_registry
```

**Lines 389-419 (Agent._create_agent):**
```python
# BEFORE (lines 391-397):
if hasattr(self, "skill_instructions") and self.skill_instructions:
    skills_section = "\n\n## Available Skills\n\n" + "\n\n".join(self.skill_instructions)
    instructions += skills_section

# AFTER:
# No static injection - let SkillContextProvider handle it dynamically

# Lines 399-408 (context_providers):
context_providers = []
if self.memory_manager:
    from agent.memory import MemoryContextProvider
    memory_provider = MemoryContextProvider(self.memory_manager, ...)
    context_providers.append(memory_provider)

# ADD:
if hasattr(self, "skill_registry") and self.skill_registry.has_skills():
    from agent.skills.context_provider import SkillContextProvider
    skill_provider = SkillContextProvider(self.skill_registry, max_skills=3)
    context_providers.append(skill_provider)
    logger.info("Skill context provider enabled")
```

#### 5. **src/agent/skills/manifest.py**
**What needs to be fixed:**
- Add `triggers: list[str]` field to SkillManifest model

**Changes:**
```python
class SkillManifest(BaseModel):
    name: str
    description: str
    triggers: list[str] | None = None  # NEW: For matching
    instructions: str = ""
    # ... rest of fields
```

### Files to Test

#### **tests/unit/skills/test_context_provider.py** (NEW)
**Purpose:** Unit tests for SkillContextProvider

**Key Tests:**
```python
def test_injects_relevant_skill_only()
def test_no_skills_matched_returns_empty_context()
def test_multiple_skills_matched_respects_max_limit()
def test_keyword_matching_case_insensitive()
def test_partial_keyword_matches()
```

#### **tests/unit/skills/test_loader.py** (MODIFY)
**Add tests:**
```python
def test_load_enabled_skills_returns_registry()
def test_skill_registry_contains_triggers_and_instructions()
```

#### **tests/unit/core/test_agent.py** (MODIFY)
**Add tests:**
```python
def test_agent_creates_skill_context_provider_when_skills_present()
def test_agent_no_skill_provider_when_no_skills()
```

#### **tests/integration/skills/test_progressive_disclosure.py** (NEW)
**Purpose:** Integration tests validating progressive disclosure

**Key Tests:**
```python
@pytest.mark.asyncio
async def test_skill_instructions_not_present_for_irrelevant_request()
async def test_skill_instructions_present_for_relevant_request()
async def test_token_usage_lower_without_skills()
```

### New Files

#### **src/agent/skills/context_provider.py**
**Purpose:** SkillContextProvider implementation
**Size:** ~150 lines

#### **tests/unit/skills/test_context_provider.py**
**Purpose:** Unit tests for context provider
**Size:** ~200 lines

#### **tests/integration/skills/test_progressive_disclosure.py**
**Purpose:** Integration tests for progressive disclosure
**Size:** ~150 lines

## Implementation Plan

### Phase 1: Core Progressive Disclosure (MVP)

Implement basic dynamic injection with keyword matching. This delivers the primary benefit (60-80% token reduction) with minimal complexity.

**Changes:**
1. Add `triggers` field to SkillManifest
2. Update SkillRegistry to store triggers + instructions
3. Implement SkillContextProvider with keyword matching
4. Update Agent to use SkillContextProvider instead of static injection
5. Update SkillLoader return signature

**Deliverable:** Skills only injected when keywords match

### Phase 2: Validation & Testing

Ensure robust testing and validation of the progressive disclosure behavior.

**Changes:**
1. Add unit tests for SkillContextProvider
2. Add integration tests for token usage validation
3. Add logging/metrics for skill matching
4. Update existing tests for new loader signature

**Deliverable:** 95%+ test coverage, token usage metrics

### Phase 3: Enhanced Matching (Future)

Improve matching beyond simple keywords for better relevance detection.

**Changes:**
1. Add semantic similarity matching (optional)
2. Add confidence scoring for skill matches
3. Add fallback to show all skills if no match (configurable)
4. Add skill match caching

**Deliverable:** Better matching accuracy, reduced false negatives

## Step by Step Tasks

### Task 1: Update SkillManifest for Triggers
- Description: Add `triggers` field to manifest model for keyword matching
- Files to modify:
  - src/agent/skills/manifest.py (SkillManifest class)
- Changes:
  - Add `triggers: list[str] | None = None` field to model
  - Update manifest parsing to extract triggers from YAML
  - Add validation: triggers must be non-empty strings if provided

### Task 2: Enhance SkillRegistry for Context Provider
- Description: Store skill metadata (triggers, instructions) for matching
- Files to modify:
  - src/agent/skills/registry.py
- Changes:
  - Add `triggers: list[str]` field to registry entries
  - Add `instructions: str` field to registry entries
  - Add method `get_all_metadata() -> list[dict]` for context provider
  - Add method `has_skills() -> bool` to check if any skills registered

### Task 3: Implement SkillContextProvider
- Description: Create context provider for dynamic skill instruction injection
- Files to modify:
  - src/agent/skills/context_provider.py (NEW)
- Changes:
  - Implement ContextProvider with invoking() hook
  - Add keyword-based skill matching logic
  - Add max_skills limit (default: 3) to prevent token overflow
  - Add logging for matched skills
  - Follow MemoryContextProvider pattern closely

### Task 4: Update SkillLoader to Return Registry
- Description: Change loader to return registry instead of instruction list
- Files to modify:
  - src/agent/skills/loader.py
- Changes:
  - Line 318-320: Register skills instead of collecting instructions
  - Change return signature: `tuple[list[AgentToolset], Any, SkillRegistry]`
  - Remove skill_instructions list building
  - Add skill metadata to registry during load

### Task 5: Update Agent to Use SkillContextProvider
- Description: Replace static injection with dynamic context provider
- Files to modify:
  - src/agent/agent.py
- Changes:
  - Lines 73-148: Store skill_registry instead of skill_instructions
  - Remove skill_instructions_tokens tracking (moved to provider)
  - Lines 391-397: Remove static skill instruction injection
  - Lines 399-408: Add SkillContextProvider to context_providers list
  - Add logging for skill context provider initialization

### Task 6: Write Unit Tests for SkillContextProvider
- Description: Test skill matching and context injection logic
- Files to modify:
  - tests/unit/skills/test_context_provider.py (NEW)
- Changes:
  - Test: injects relevant skill only
  - Test: returns empty context when no match
  - Test: respects max_skills limit
  - Test: case-insensitive keyword matching
  - Test: multiple skills matched and prioritized

### Task 7: Write Integration Tests for Progressive Disclosure
- Description: Validate end-to-end token usage reduction
- Files to modify:
  - tests/integration/skills/test_progressive_disclosure.py (NEW)
- Changes:
  - Test: skill instructions NOT in context for irrelevant request
  - Test: skill instructions present for relevant request
  - Test: token count lower for non-skill requests
  - Test: multiple skills matched correctly

### Task 8: Update Existing Tests
- Description: Fix tests affected by loader signature change
- Files to modify:
  - tests/unit/skills/test_loader.py
  - tests/unit/core/test_agent.py
- Changes:
  - Update assertions for new loader return type
  - Add test for skill_registry storage in Agent
  - Add test for SkillContextProvider creation

### Task 9: Update Documentation
- Description: Document the progressive disclosure behavior
- Files to modify:
  - docs/design/skills.md
- Changes:
  - Add section on "Dynamic Instruction Injection"
  - Document triggers field in SKILL.md format
  - Add example of keyword matching behavior
  - Note: Phase 1 uses keyword matching, Phase 2 can add semantic

## Testing Strategy

### Regression Tests

**Purpose:** Ensure skills still work correctly after progressive disclosure

**Test Cases:**
1. **Skill still invoked when relevant** - Request matches trigger → skill available
2. **Script discovery unchanged** - Scripts still loaded and callable
3. **Toolset loading unchanged** - Toolsets still instantiated correctly
4. **Existing skill functionality** - All existing skill features work

**Validation:**
```bash
# Run full skill test suite
cd src && uv run pytest ../tests/unit/skills/ -v

# Verify hello-extended skill still works
agent -p "Say bonjour to Alice"
```

### Edge Case Tests

**Test Cases:**
1. **No skills installed** - Agent should work without skills
2. **No triggers defined** - Skill should never match (never injected)
3. **Empty trigger list** - Same as no triggers
4. **Trigger with special chars** - Matching should handle punctuation
5. **Very long skill instructions** - Should respect max_skills limit
6. **Multiple skills match** - Should prioritize by order, respect limit

### Impact Tests

**Purpose:** Ensure no new bugs introduced

**Test Cases:**
1. **Memory still works** - MemoryContextProvider unaffected
2. **Middleware still works** - Logging/metrics middleware unaffected
3. **Token counting** - Trace logging shows reduced tokens
4. **Session persistence** - Save/load sessions still works

**Validation:**
```bash
# Test memory integration
agent -p "My name is Alice"
agent --continue <session-id> -p "What's my name?"

# Test token reduction
export LOG_LEVEL=trace
agent -p "What is 2+2?" 2>&1 | grep "tokens"
agent -p "Say bonjour to Alice" 2>&1 | grep "tokens"
# Second should have more tokens (skill injected)
```

## Acceptance Criteria

- [ ] Skill instructions NOT present in system prompt for irrelevant requests
- [ ] Skill instructions present ONLY when request matches trigger keywords
- [ ] Token usage reduced by 60-80% for non-skill requests (measured via trace logs)
- [ ] All existing skill functionality still works (scripts, toolsets, discovery)
- [ ] SkillContextProvider unit tests pass with 95%+ coverage
- [ ] Integration tests validate token reduction
- [ ] No performance degradation (matching adds <5ms per request)
- [ ] Documentation updated with triggers field and matching behavior

## Validation Commands

```bash
# 1. Run unit tests
cd src && uv run pytest ../tests/unit/skills/ -v

# 2. Run integration tests
cd src && uv run pytest ../tests/integration/skills/test_progressive_disclosure.py -v

# 3. Validate token reduction (requires trace logging)
export LOG_LEVEL=trace
export ENABLE_SENSITIVE_DATA=true

# Request WITHOUT skill relevance (baseline)
agent -p "What is 2+2?"
cat ~/.agent/logs/session-*-trace.log | jq -s 'map(select(.tokens)) | map(.tokens.total) | add'

# Request WITH skill relevance (should be higher)
agent -p "Say bonjour to Alice"
cat ~/.agent/logs/session-*-trace.log | jq -s 'map(select(.tokens)) | map(.tokens.total) | add'

# 4. Verify skill still works
agent -p "Greet Alice in French"
# Should invoke hello-extended skill successfully

# 5. Test fallback when no skills match
agent -p "Calculate pi to 10 digits"
# Should work fine without skill instructions

# 6. Run full test suite
cd src && uv run pytest
```

## Notes

### Design Decisions

**Why ContextProvider over Middleware?**
- Middleware only sees input messages, not suitable for context injection
- ContextProvider is the framework's intended pattern (per ADR-0013)
- Proven successful with MemoryContextProvider

**Why Keyword Matching for Phase 1?**
- Simple, fast, predictable behavior
- No external dependencies (embeddings, models)
- Covers 80%+ of use cases
- Can enhance in Phase 2 if needed

**Why max_skills=3 Limit?**
- Prevents token overflow if many skills match
- Most requests need 1-2 skills maximum
- Configurable for future tuning

### Potential Side Effects

**False Negatives (Skill Not Available When Needed):**
- **Mitigation:** Comprehensive trigger keywords in SKILL.md
- **Fallback:** Can add "show all skills" config option
- **Monitoring:** Log when skills matched for debugging

**Matching Latency:**
- **Impact:** Minimal (~1-5ms for keyword matching)
- **Mitigation:** Simple string operations, no I/O
- **Future:** Can add caching if needed

### Future Improvements

**Phase 2 Enhancements:**
1. **Semantic Matching:** Use embeddings for better relevance
2. **Skill Ranking:** Score skills by confidence
3. **Intelligent Fallback:** Show all skills if no high-confidence match
4. **Caching:** Cache matched skills for repeated requests
5. **Analytics:** Track skill match accuracy over time

**Configuration Options (Future):**
```bash
# In config
SKILL_MATCHING_MODE=keyword  # keyword|semantic|hybrid
SKILL_MAX_PER_REQUEST=3
SKILL_FALLBACK_MODE=none     # none|show_all|ask_user
```

## Execution

This spec can be implemented using: `/sdlc:implement docs/specs/bug-skill-progressive-discovery.md`
