# Bug Fix: Skills Progressive Discovery

## Bug Description

**Current Behavior:**
All skill documentation (full SKILL.md markdown content after YAML frontmatter) is injected into the system prompt at agent initialization and sent with **every LLM request**, regardless of whether the skill will be used in that request.

**Impact:**
- Token overhead of 60-80% on baseline requests that don't use skills
- hello-extended skill alone adds ~1200 tokens of XML documentation
- Multiple skills compound this overhead linearly
- Wastes context window space and increases latency/cost
- LLM lacks awareness of available capabilities when skills don't match triggers

**Example:**
A skill like `hello-extended` has 47 lines of detailed XML documentation describing tools, triggers, examples, and language mappings. This entire documentation is loaded into the system prompt even for simple requests like "What is 2+2?" that will never use greeting functionality.

## Problem Statement

The current architecture loads full skill instructions at agent initialization (Agent.__init__) and statically injects them into the system prompt (_create_agent), making them part of every LLM request regardless of relevance. This violates the progressive disclosure principle that the skills architecture is designed around.

**Files Affected:**
- src/agent/agent.py:73-148 - Skill instructions collected and stored
- src/agent/agent.py:389-397 - Static injection into system prompt
- src/agent/skills/loader.py:318-320 - Full instructions extracted from manifest

## Solution Statement

Implement progressive skill documentation using Agent Framework's `ContextProvider` pattern. Inject skill information on-demand based on user queries and trigger matching, avoiding constant token overhead while preserving discoverability. Maintain separation between install metadata (SkillRegistry) and runtime documentation (SkillDocumentationIndex).

**Approach (Three-Tier System):**
1. Create separate `SkillDocumentationIndex` for runtime docs (not persistent registry)
2. Implement three-tier progressive disclosure:
   - Breadcrumb (~10 tokens) when skills exist but don't match
   - Registry (10-15 tokens/skill) when user asks about capabilities
   - Full docs (hundreds of tokens) when triggers match
3. Match requests using single-message analysis (no memory dependency)
4. Use word-boundary matching with error handling for robustness
5. Support multiple trigger types with fallbacks: keywords, verbs, patterns, skill names
6. Cap "show all skills" to prevent context overflow

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

However, the implementation conflates two distinct concerns:
1. **Skill Discovery** - The LLM knowing skills exist (should be minimal, always present)
2. **Skill Documentation** - Detailed usage instructions (should be progressive)

Currently, **only scripts** follow progressive loading. The SKILL.md documentation is eagerly loaded:

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
- Line 318-320: Currently builds static instructions list
- Need to populate SkillDocumentationIndex instead

**Changes:**
```python
# BEFORE (line 318-320 and return):
skill_instructions = []  # Collected in loop
for skill in enabled_skills:
    if manifest.instructions:
        skill_instructions.append(f"# {manifest.name}\n\n{manifest.instructions}")
# ...
return (toolsets, script_tool_wrapper, skill_instructions)

# AFTER:
# Create documentation index once (before loop)
skill_docs = SkillDocumentationIndex()

# Populate with enabled skills (in loop)
for skill in enabled_skills:
    skill_docs.add_skill(
        name=canonical_name,
        manifest=manifest
    )

# Script tool wrapper created as before
script_tool_wrapper = ScriptToolWrapper(...)

# Return new signature
return (toolsets, script_tool_wrapper, skill_docs)
```

**New Return Signature:**
```python
def load_enabled_skills() -> tuple[
    list[AgentToolset],           # Toolsets
    Any,                           # Script tool wrapper
    SkillDocumentationIndex        # Runtime documentation index
]:
```

#### 2. **src/agent/skills/documentation_index.py** (NEW FILE)
**Purpose:** In-memory cache for skill documentation and triggers (separate from install registry)

**Why not SkillRegistry:**
- SkillRegistry persists install metadata to `~/.agent/skills/registry.json`
- Mixing runtime docs would bloat the JSON and break CLI expectations
- Need separation between install state and runtime context

**Implementation:**
```python
from dataclasses import dataclass
from typing import Dict, List, Any, Optional

from agent.skills.manifest import SkillManifest

@dataclass
class SkillDocumentation:
    """Runtime documentation for a single skill."""
    name: str
    brief_description: str
    triggers: Optional[Dict[str, List[str]]]  # {keywords: [], verbs: [], patterns: []}
    instructions: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for context provider."""
        return {
            'name': self.name,
            'brief_description': self.brief_description,
            'triggers': self.triggers or {},
            'instructions': self.instructions
        }

class SkillDocumentationIndex:
    """In-memory index of skill documentation for context injection.

    Separate from SkillRegistry to avoid mixing persistent install
    metadata with runtime documentation.
    """

    def __init__(self):
        self._skills: Dict[str, SkillDocumentation] = {}

    def add_skill(self, name: str, manifest: SkillManifest) -> None:
        """Add skill documentation from manifest."""
        self._skills[name] = SkillDocumentation(
            name=name,
            brief_description=manifest.brief_description,
            triggers=manifest.triggers,
            instructions=manifest.instructions
        )

    def get_all_metadata(self) -> List[Dict[str, Any]]:
        """Get all skill metadata for matching."""
        return [skill.to_dict() for skill in self._skills.values()]

    def has_skills(self) -> bool:
        """Check if any skills are loaded."""
        return bool(self._skills)

    def count(self) -> int:
        """Get number of loaded skills."""
        return len(self._skills)
```

#### 3. **src/agent/skills/context_provider.py** (NEW FILE)
**Purpose:** Three-tier skill documentation system with progressive disclosure

**Implementation:**
```python
"""Skill context provider for dynamic instruction injection."""

import logging
import re
from typing import Any, List, Dict, Optional
from agent_framework import ChatMessage, Context, ContextProvider
from agent.skills.documentation_index import SkillDocumentationIndex

logger = logging.getLogger(__name__)

class SkillContextProvider(ContextProvider):
    """Progressive skill documentation with on-demand registry."""

    def __init__(
        self,
        skill_docs: SkillDocumentationIndex,
        memory_manager: Optional[Any] = None,
        max_skills: int = 3,
        max_all_skills: int = 10
    ):
        self.skill_docs = skill_docs
        self.memory_manager = memory_manager  # For conversation context
        self.max_skills = max_skills
        self.max_all_skills = max_all_skills  # Cap for "show all"

    async def invoking(self, messages, **kwargs) -> Context:
        """Inject skill documentation based on request relevance."""
        # 1. Extract current user message
        current_message = self._get_latest_user_message(messages)
        if not current_message:
            return Context()

        # 2. Check if user is asking about capabilities
        if self._wants_skill_info(current_message):
            return self._inject_skill_registry()

        # 3. Check for "show all skills" escape hatch
        if self._wants_all_skills(current_message):
            return self._inject_all_skills_capped()

        # 4. Match skills based on current message
        relevant_skills = self._match_skills_safely(current_message.lower())

        # 5. Build response based on matches
        if relevant_skills:
            # Inject full documentation for matched skills
            docs = self._build_skill_documentation(relevant_skills[:self.max_skills])
            return Context(instructions=docs)
        elif self.skill_docs.has_skills():
            # Inject minimal breadcrumb for discoverability (~10 tokens)
            breadcrumb = f"[{self.skill_docs.count()} skills available]"
            return Context(instructions=breadcrumb)
        else:
            # No skills installed - inject nothing
            return Context()

    def _inject_skill_registry(self) -> Context:
        """Inject skill registry with brief descriptions on demand."""
        lines = ["## Available Capabilities\n"]
        for skill in self.skill_docs.get_all_metadata():
            # Include brief description for discoverability (10-15 tokens per skill)
            brief = skill['brief_description'][:50]  # Cap at 50 chars
            lines.append(f"- **{skill['name']}**: {brief}")
        lines.append("\nAsk about specific skills for full documentation.")
        return Context(instructions="\n".join(lines))

    def _wants_skill_info(self, message: str) -> bool:
        """Check if user is asking about capabilities."""
        info_patterns = [
            r"\bwhat.*(?:can|could).*(?:you|u).*do\b",
            r"\b(?:show|list).*capabilities\b",
            r"\bwhat.*skills?\b"
        ]
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in info_patterns)

    def _wants_all_skills(self, message: str) -> bool:
        """Check if user wants to see all skill documentation."""
        all_patterns = [
            r"\bshow.*all.*skills?\b",
            r"\blist.*all.*skills?\b",
            r"\ball.*skill.*(?:documentation|docs)\b"
        ]
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in all_patterns)

    def _match_skills_safely(self, context: str) -> list[dict]:
        """Match skills with word boundaries and error handling."""
        matched = []
        seen = set()

        for skill in self.skill_docs.get_all_metadata():
            skill_id = skill['name']
            if skill_id in seen:
                continue

            # Strategy 1: Skill name mentioned (word boundary)
            skill_name_lower = skill['name'].lower()
            if re.search(rf"\b{re.escape(skill_name_lower)}\b", context):
                matched.append(skill)
                seen.add(skill_id)
                continue

            # If no triggers, fallback to restrictive description matching
            triggers = skill.get('triggers', {})
            if not triggers:
                # Fallback: only match if skill name appears in context
                # Don't match generic description words to avoid false positives
                if re.search(rf"\b{re.escape(skill_name_lower)}\b", context):
                    matched.append(skill)
                    seen.add(skill_id)
                continue

            # Strategy 2: Keyword triggers (word boundary)
            for keyword in triggers.get('keywords', []):
                if re.search(rf"\b{re.escape(keyword.lower())}\b", context):
                    matched.append(skill)
                    seen.add(skill_id)
                    break

            # Strategy 3: Verb triggers (word boundary)
            for verb in triggers.get('verbs', []):
                if re.search(rf"\b{re.escape(verb.lower())}\b", context):
                    matched.append(skill)
                    seen.add(skill_id)
                    break

            # Strategy 4: Pattern matching (with error handling)
            for pattern in triggers.get('patterns', []):
                try:
                    if re.search(pattern, context, re.IGNORECASE):
                        matched.append(skill)
                        seen.add(skill_id)
                        break
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {skill_id}: {pattern} - {e}")

        return matched

    def _build_skill_documentation(self, skills: list[dict]) -> str:
        """Build full documentation for matched skills."""
        docs = ["## Relevant Skill Documentation\n"]
        for skill in skills:
            docs.append(f"### {skill['name']}\n")
            docs.append(skill.get('instructions', ''))
            docs.append("")
        return "\n".join(docs)

    def _inject_all_skills_capped(self) -> Context:
        """Inject skill documentation with cap to avoid context overflow."""
        all_skills = self.skill_docs.get_all_metadata()

        if len(all_skills) <= self.max_all_skills:
            # Show all if under cap
            docs = self._build_skill_documentation(all_skills)
        else:
            # Show capped list with note
            docs = self._build_skill_documentation(all_skills[:self.max_all_skills])
            docs += f"\n\n*Showing {self.max_all_skills} of {len(all_skills)} skills. "
            docs += "Ask about specific skills for more details.*"

        return Context(instructions=docs)

    def _get_latest_user_message(self, messages: list) -> str:
        """Extract the latest user message."""
        # Messages in ContextProvider are typically just the current turn
        for msg in reversed(messages):
            if hasattr(msg, 'role') and msg.role == 'user':
                return msg.content
        return ""
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
skill_toolsets, script_tools, skill_docs = skill_loader.load_enabled_skills()
# Store documentation index instead of static instructions
self.skill_docs = skill_docs  # SkillDocumentationIndex instance
```

**Lines 389-419 (Agent._create_agent):**
```python
# BEFORE (lines 391-397):
if hasattr(self, "skill_instructions") and self.skill_instructions:
    skills_section = "\n\n## Available Skills\n\n" + "\n\n".join(self.skill_instructions)
    instructions += skills_section

# AFTER:
# Remove ALL static skill injection - handled by SkillContextProvider

# Lines 399-408 (context_providers):
context_providers = []
if self.memory_manager:
    from agent.memory import MemoryContextProvider
    memory_provider = MemoryContextProvider(self.memory_manager, ...)
    context_providers.append(memory_provider)

# ADD:
if hasattr(self, "skill_docs") and self.skill_docs.has_skills():
    from agent.skills.context_provider import SkillContextProvider
    # Note: memory_manager is optional, only used for future conversation context
    skill_provider = SkillContextProvider(
        skill_docs=self.skill_docs,
        memory_manager=None,  # Not used in current implementation
        max_skills=3
    )
    context_providers.append(skill_provider)
    logger.info(f"Skill context provider enabled with {self.skill_docs.count()} skills")
```

#### 5. **src/agent/skills/manifest.py**
**What needs to be fixed:**
- Add structured `triggers` field to SkillManifest model
- Add `brief_description` field for registry display

**Changes:**
```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class SkillTriggers(BaseModel):
    """Structured triggers for skill matching."""
    keywords: List[str] = Field(default_factory=list)  # Direct keyword matches
    verbs: List[str] = Field(default_factory=list)     # Action verbs
    patterns: List[str] = Field(default_factory=list)  # Regex patterns

class SkillManifest(BaseModel):
    name: str
    description: str
    brief_description: str | None = None  # NEW: One-line description for registry
    triggers: SkillTriggers | None = None  # NEW: Structured triggers
    instructions: str = ""
    # ... rest of fields

    def model_post_init(self, __context) -> None:
        """Auto-generate brief description and add skill name as trigger."""
        # Auto-generate brief description if not provided
        if not self.brief_description:
            # Take first sentence or first 80 chars of description
            first_sentence = self.description.split('.')[0]
            self.brief_description = first_sentence[:80]

        # Ensure triggers exists (creates new instance, not mutating default)
        if self.triggers is None:
            self.triggers = SkillTriggers()

        # Add skill name as implicit trigger (case-insensitive check)
        # Creates new list to avoid mutating shared defaults
        skill_name_lower = self.name.lower()
        existing_keywords_lower = [kw.lower() for kw in self.triggers.keywords]
        if skill_name_lower not in existing_keywords_lower:
            # Create new list with skill name added
            self.triggers.keywords = self.triggers.keywords + [skill_name_lower]
```

### Files to Test

#### **tests/unit/skills/test_context_provider.py** (NEW)
**Purpose:** Unit tests for SkillContextProvider

**Key Tests:**
```python
def test_minimal_breadcrumb_when_no_match()
def test_injects_documentation_for_matched_skills()
def test_registry_only_on_user_request()
def test_escape_hatch_shows_all_skills_with_cap()
def test_word_boundary_matching_prevents_false_positives()
def test_invalid_regex_handled_gracefully()
def test_fallback_to_skill_name_when_no_triggers()
def test_skill_name_as_implicit_trigger()
def test_respects_max_skills_limit()
def test_pattern_based_matching_with_error_handling()
def test_verb_based_matching_with_boundaries()
```

#### **tests/unit/skills/test_loader.py** (MODIFY)
**Add tests:**
```python
def test_load_enabled_skills_returns_documentation_index()
def test_documentation_index_contains_triggers_and_instructions()
def test_documentation_index_separate_from_install_registry()
```

#### **tests/unit/core/test_agent.py** (MODIFY)
**Add tests:**
```python
def test_agent_stores_skill_documentation_index()
def test_agent_creates_skill_context_provider_when_skills_present()
def test_agent_no_skill_provider_when_no_skills()
def test_agent_uses_skill_docs_not_skill_registry_for_runtime()
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

### Phase 1: Progressive Documentation with Minimal Breadcrumb (MVP)

Implement progressive skill documentation with minimal breadcrumb for discoverability. This delivers the primary benefit (70-90% token reduction) while preserving skill discoverability through a tiny hint.

**Changes:**
1. Add structured `triggers` and `brief_description` fields to SkillManifest
2. Create separate SkillDocumentationIndex for runtime (not persistent registry)
3. Implement SkillContextProvider with three-tier injection:
   - Minimal breadcrumb when skills exist but don't match (~10 tokens)
   - Full registry when user asks about capabilities (10-15 tokens/skill)
   - Full documentation when triggers match (hundreds of tokens)
4. Use single-message matching (conversation context requires memory)
5. Add escape hatches for "show all skills" with cap
6. Update Agent to use SkillContextProvider with skill_docs
7. Update SkillLoader to return SkillDocumentationIndex

**Deliverable:** Near-zero token overhead with preserved discoverability

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

### Task 1: Update SkillManifest for Enhanced Triggers
- Description: Add structured triggers and brief description to manifest model
- Files to modify:
  - src/agent/skills/manifest.py (SkillManifest class)
- Changes:
  - Add `SkillTriggers` model with keywords, verbs, patterns
  - Add `triggers: SkillTriggers | None = None` field
  - Add `brief_description: str | None = None` field
  - Add model_post_init to auto-generate brief description if missing
  - Add skill name as implicit trigger keyword
  - Update manifest parsing to extract structured triggers from YAML

### Task 2: Create SkillDocumentationIndex
- Description: Create separate in-memory index for runtime documentation
- Files to modify:
  - src/agent/skills/documentation_index.py (NEW)
- Changes:
  - Create SkillDocumentationIndex class (not persistent)
  - Store brief_description, triggers, instructions from manifests
  - Add method `add_skill(name, manifest)` to populate from loader
  - Add method `get_all_metadata() -> list[dict]` for context provider
  - Add method `has_skills() -> bool` to check if any skills loaded
  - Keep SkillRegistry unchanged (only for install metadata)

### Task 3: Implement Progressive SkillContextProvider
- Description: Create context provider with three-tier injection
- Files to modify:
  - src/agent/skills/context_provider.py (NEW)
- Changes:
  - Implement ContextProvider with invoking() hook
  - Inject minimal breadcrumb when no matches (~10 tokens)
  - Inject full registry when user asks about capabilities
  - Match skills using current message only (single-message)
  - Implement multi-strategy matching with word boundaries:
    - Direct skill name mentions
    - Keyword triggers (word boundary)
    - Verb-based triggers (word boundary)
    - Pattern matching (regex with error handling)
  - Add escape hatch for "show all skills" with cap (10 max)
  - Add max_skills limit (default: 3) for documentation
  - Add logging for matched skills

### Task 4: Update SkillLoader to Return DocumentationIndex
- Description: Change loader to return documentation index instead of instruction list
- Files to modify:
  - src/agent/skills/loader.py
- Changes:
  - Line 318-320: Add skills to SkillDocumentationIndex instead of list
  - Change return signature: `tuple[list[AgentToolset], Any, SkillDocumentationIndex]`
  - Create and populate SkillDocumentationIndex during load
  - Keep SkillRegistry usage unchanged (for install tracking only)

### Task 5: Update Agent to Use SkillContextProvider
- Description: Replace static injection with dynamic context provider
- Files to modify:
  - src/agent/agent.py
- Changes:
  - Lines 73-148: Store skill_docs (SkillDocumentationIndex) instead of skill_instructions
  - Remove skill_instructions and skill_instructions_tokens fields
  - Lines 391-397: Remove ALL static skill injection code
  - Lines 399-408: Add SkillContextProvider(skill_docs, memory_manager)
  - Pass memory_manager to SkillContextProvider for optional conversation context
  - Log when skill context provider is enabled

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

- [ ] Minimal breadcrumb (~10 tokens) when skills exist but don't match
- [ ] Full registry (10-15 tokens/skill) ONLY when user asks about capabilities
- [ ] Full documentation injected ONLY when triggers match
- [ ] Token usage reduced by 70-90% for non-skill requests
- [ ] Word-boundary matching prevents false positives ("run" doesn't match "runner")
- [ ] Invalid regex patterns handled gracefully (logged, not crashed)
- [ ] Fallback to skill name only when no triggers defined
- [ ] "Show all skills" capped at 10 skills to prevent overflow
- [ ] Skill name always works as implicit trigger
- [ ] SkillDocumentationIndex separate from persistent SkillRegistry
- [ ] SkillDocumentationIndex exposes count() method for encapsulation
- [ ] All existing skill functionality preserved (opt-in model maintained)
- [ ] Tests cover truncation path for "show all skills" cap
- [ ] SkillContextProvider unit tests pass with 95%+ coverage
- [ ] No performance degradation (matching adds <5ms per request)

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

**Why Three-Tier Documentation?**
- Tier 1: Breadcrumb (~10 tokens total) - minimal hint that skills exist
- Tier 2: Registry (10-15 tokens/skill) - on-demand capability list
- Tier 3: Full docs (hundreds of tokens) - only when triggers match
- Balances discoverability with token efficiency

**Why ContextProvider over Middleware?**
- Middleware only sees input messages, not suitable for context injection
- ContextProvider is the framework's intended pattern (per ADR-0013)
- Proven successful with MemoryContextProvider

**Why Single-Message Matching?**
- ContextProvider only receives current turn without memory enabled
- Conversation context requires memory manager integration
- Single-message is simpler and works consistently
- Future: Can enhance with memory for multi-turn context

**Why Multiple Trigger Strategies?**
- Keywords alone are too brittle for natural language
- Verbs capture action intent ("translate", "greet", "fetch")
- Patterns handle complex expressions ("say .* in", "translate to")
- Skill name as trigger ensures direct references work

**Why max_skills=3 Limit?**
- Prevents token overflow if many skills match
- Most requests need 1-2 skills maximum
- Configurable for future tuning

### Example SKILL.md Format

```yaml
---
name: hello-extended
description: Multi-language greeting tool for personalized messages
brief_description: Multi-language greetings and translations
triggers:
  keywords:
    - hello
    - greet
    - bonjour
    - hola
    - greeting
    - welcome
  verbs:
    - greet
    - welcome
    - say
    - translate
  patterns:
    - "say .* in .*"
    - "greet .* in .*"
    - "translate .* to .*"
---

# hello-extended

[Full documentation goes here...]
```

### Potential Side Effects

**False Negatives (Reduced but Not Eliminated):**
- **Mitigation 1:** Registry always visible ensures LLM knows skill exists
- **Mitigation 2:** Multiple trigger strategies increase match likelihood
- **Mitigation 3:** Conversation context captures related discussions
- **Mitigation 4:** Escape hatch allows user to request all skills
- **Monitoring:** Log matched skills and confidence for tuning

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

## Key Improvements Based on Feedback

This revised spec addresses critical architectural concerns:

1. **Registry Separation**: SkillDocumentationIndex for runtime, SkillRegistry for installs
   - Prevents bloating persistent registry.json
   - Maintains clean separation of concerns

2. **Three-Tier System**: Breadcrumb → Registry → Full docs
   - Breadcrumb (~10 tokens) when skills exist but don't match
   - Registry (10-15 tokens/skill) only when user asks
   - Full docs (hundreds of tokens) only when triggers match
   - Achieves 70-90% token reduction

3. **Single-Message Matching**: No memory dependency
   - Works consistently regardless of memory configuration
   - Matches on current turn only for simplicity and reliability

4. **Robust Matching**: Word boundaries and error handling
   - Prevents false positives ("run" vs "runner")
   - Handles invalid regex patterns gracefully
   - Fallback to skill name only when no triggers

5. **Maintained Opt-In Model**: Skills still require explicit enabling
   - Preserves original activation contract
   - Prevents unexpected skill activation

6. **Capped Output**: "Show all" limited to prevent context overflow
   - Max N skills shown at once
   - User prompted for specific skills beyond cap

## Follow-Up Issues Resolved

All inconsistencies from both follow-up reviews have been addressed:

### Round 1 (Architectural):
1. **Loader return consistency**: Fixed - Returns `SkillDocumentationIndex` everywhere
2. **Context-provider tests**: Aligned - Removed conversation-aware tests, single-message only
3. **Data model gaps**: Added `SkillDocumentation` dataclass with all fields
4. **Discovery vs invisibility**: Added minimal breadcrumb (~10 tokens) for discoverability
5. **Registry snippet**: Now includes brief descriptions (10-15 tokens/skill) when shown
6. **Matching fallback**: Restricted to skill name only, not generic description words
7. **"Show all" cap**: Documented and tested at 10 skills max
8. **Signature clarity**: Agent uses `skill_docs` consistently, memory_manager optional
9. **Schema defaults**: Uses `Field(default_factory=list)`, creates new lists in post_init

### Round 2 (Implementation Consistency):
1. **Loader snippets**: Updated to use `skill_docs.add_skill()` not `skill_registry.register()`
2. **Task 3 wording**: Fixed - "minimal breadcrumb" not "always inject registry", single-message not multi-turn
3. **Matching fallback**: Removed "description" language, only skill name fallback documented
4. **Test names**: Renamed all "registry" tests to "documentation_index"
5. **Breadcrumb encapsulation**: Added `count()` method, no direct `_skills` access
6. **Import clarity**: Added `SkillManifest` import to SkillDocumentationIndex
7. **Token accuracy**: Updated breadcrumb to ~10 tokens (was 3-5), matches actual implementation

## Open Questions Resolved

Based on the feedback, these design decisions were made:

1. **"Do we want the registry text on every turn?"**
   - **Decision**: Minimal breadcrumb only (~10 tokens) when skills exist
   - **Rationale**: Preserves discoverability without token bloat

2. **"Should trigger matching be opt-in per skill?"**
   - **Decision**: Skills remain opt-in (must be explicitly enabled in config)
   - **Rationale**: Preserves backward compatibility and original activation model
   - **Note**: Trigger matching only applies to already-enabled skills

## Execution

This spec can be implemented using: `/sdlc:implement docs/specs/bug-skill-progressive-discovery.md`
