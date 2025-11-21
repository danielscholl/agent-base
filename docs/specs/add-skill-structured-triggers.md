# Enhancement: Add Structured Triggers to Skills

## Overview

Add structured YAML triggers to all skills to enable efficient keyword-based matching and reduce reliance on registry injection. This enhancement complements the progressive disclosure system implemented in [bug-skill-progressive-discovery.md](bug-skill-progressive-discovery.md).

## Context

**Current State**: Skills rely on implicit triggers (skill name only) added by `model_post_init()`
**Impact**: All skills have minimal triggers, causing breadcrumb path to always activate
**Opportunity**: Add explicit triggers to enable more targeted documentation injection

## Problem Statement

Skills currently have only their name as an implicit keyword trigger. While this works, it means:
1. Breadcrumb is always used (because all skills have triggers)
2. Skill documentation only injected when skill name mentioned explicitly
3. Related queries miss keyword matches (e.g., "fetch a webpage" doesn't match "web" skill)
4. LLM relies on breadcrumb discovery instead of targeted documentation

**Example**:
```yaml
# Current (implicit only)
triggers:
  keywords: ["web"]  # Auto-added by model_post_init

# Better (explicit rich triggers)
triggers:
  keywords: ["web", "search", "fetch", "url", "internet", "online"]
  verbs: ["search", "fetch", "get", "find"]
  patterns: ["https?://", "search.*for"]
```

## Solution Statement

Add explicit structured triggers to all skills in their SKILL.md YAML frontmatter. This enables:
- Keyword-based matching for relevant queries
- Targeted Tier 3 injection when triggers match
- Reduced registry injection reliance (registry only shown on explicit ask or when skill has no triggers)
- Better user experience (right docs at the right time)

**Progressive Disclosure Behavior** (from implementation):
1. **Registry injection**: ONLY when user asks "what can you do?" OR skill has no triggers
2. **Full docs injection**: ONLY when trigger hits (name/keywords/verbs/patterns match)
3. **Breadcrumb**: When skills exist with triggers but no match (`[N skills available]`)

**Requirements**:
- Every skill must have at least one trigger (can be just the skill name)
- All regex patterns must compile without errors
- Each skill must have `brief_description` for registry display

## Proposed Changes

### 1. web Skill

**File**: `~/.agent/skills/web/SKILL.md`

**Current YAML frontmatter**:
```yaml
---
name: web
description: "Search the web using Brave Search API and fetch page content with HTML-to-markdown conversion. Use when user needs current information, online documentation, or specific URL content beyond knowledge cutoff."
version: 1.0.0
allowed-tools: Bash, WebFetch, WebSearch
---
```

**Updated YAML frontmatter** (add these fields):
```yaml
---
name: web
description: "Search the web using Brave Search API and fetch page content with HTML-to-markdown conversion. Use when user needs current information, online documentation, or specific URL content beyond knowledge cutoff."
version: 1.0.0
brief_description: "Web search and page fetching with Brave API"
triggers:
  keywords:
    - web
    - search
    - internet
    - online
    - fetch
    - url
    - webpage
    - website
    - current
    - recent
    - latest
    - news
    - documentation
    - brave
  verbs:
    - search
    - fetch
    - get
    - find
    - lookup
    - retrieve
  patterns:
    - "https?://"
    - "www\\."
    - "search.*for"
    - "look.*up"
    - "find.*information"
    - "current.*(?:news|info|data)"
    - "recent.*(?:news|info|data)"
allowed-tools: Bash, WebFetch, WebSearch
---
```

**Note**: Keep `allowed-tools` and other skill-specific fields separate from `triggers` block

**Rationale**:
- Matches common search intents ("search for", "find information")
- Captures URL patterns automatically
- Covers "current/recent" knowledge cutoff scenarios

### 2. hello-extended Skill

**File**: `src/agent/_bundled_skills/hello-extended/SKILL.md`

**Current YAML frontmatter**:
```yaml
---
name: hello-extended
description: Multi-language greetings in 6 languages. Use for non-English greetings or multiple people.
toolsets:
  - toolsets.hello:HelloExtended
---
```

**Updated YAML frontmatter** (add these fields):
```yaml
---
name: hello-extended
description: Multi-language greetings in 6 languages. Use for non-English greetings or multiple people.
brief_description: "Multi-language greetings (es, fr, de, ja, zh)"
triggers:
  keywords:
    - hello-extended
    - greet
    - greeting
    - hello
    - bonjour
    - hola
    - hallo
    - konnichiwa
    - nihao
    - french
    - spanish
    - german
    - japanese
    - chinese
    - multilingual
    - language
  verbs:
    - greet
    - welcome
    - say
    - speak
  patterns:
    - "say .* in (?:french|spanish|german|japanese|chinese)"
    - "greet .* in (?:es|fr|de|ja|zh)"
    - "\\b(?:bonjour|hola|hallo)\\b"
    - "translate.*greeting"
toolsets:
  - toolsets.hello:HelloExtended
---
```

**Note**: Keep `toolsets` field separate from `triggers` block

**Rationale**:
- Captures language-specific keywords (bonjour, hola, etc.)
- Matches language names (french, spanish, etc.)
- Pattern-matches "say X in Y" constructions
- Includes Unicode greetings for natural language usage

### 3. osdu Skill

**File**: `~/.agent/skills/osdu/SKILL.md`

**Add to YAML frontmatter**:
```yaml
---
name: osdu
description: "GitLab CI/CD test job reliability analysis for OSDU projects. Tracks test job (unit/integration/acceptance) pass/fail status across pipeline runs. Use for test job status, flaky test job detection, test reliability metrics, cloud provider analytics."
version: 1.0.0
brief_description: "OSDU GitLab CI/CD test reliability analysis"
triggers:
  keywords:
    - osdu
    - gitlab
    - ci
    - cd
    - pipeline
    - test
    - job
    - reliability
    - flaky
    - acceptance
    - integration
    - unit
    - azure
    - aws
    - gcp
    - cloud
    - provider
  verbs:
    - analyze
    - track
    - monitor
    - test
    - check
  patterns:
    - "test.*(?:reliability|status|job)"
    - "pipeline.*(?:analysis|status)"
    - "flaky.*test"
    - "ci.*cd"
    - "gitlab.*(?:pipeline|job)"
allowed-tools: Bash
---
```

**Rationale**:
- Domain-specific: OSDU, GitLab, CI/CD terminology
- Captures test reliability queries
- Includes cloud provider keywords

### 4. kalshi-markets Skill

**File**: `~/.agent/skills/kalshi-markets/SKILL.md`

**Add to YAML frontmatter**:
```yaml
---
name: kalshi-markets
description: "Kalshi prediction market data (prices, odds, orderbooks, trades). Use for prediction markets, Kalshi, betting odds, election and sports betting, market forecasts."
version: 1.0.0
brief_description: "Kalshi prediction markets and betting odds"
triggers:
  keywords:
    - kalshi
    - market
    - markets
    - prediction
    - betting
    - odds
    - election
    - sports
    - forecast
    - probability
    - orderbook
    - trade
    - price
    - bet
    - wager
  verbs:
    - bet
    - predict
    - forecast
    - trade
    - check
    - get
  patterns:
    - "prediction.*market"
    - "betting.*odds"
    - "election.*(?:odds|forecast|probability)"
    - "sports.*(?:betting|odds)"
    - "market.*(?:forecast|prediction)"
    - "what.*(?:odds|probability)"
allowed-tools: Bash
---
```

**Rationale**:
- Prediction market terminology
- Election and sports betting queries
- Probability and forecasting language

## Implementation Steps

### Step 1: Validate Pattern Regex (Before Adding)
Test all patterns compile correctly:
```python
import re

# Test each pattern before adding to SKILL.md
patterns = [
    "https?://",
    "search.*for",
    "say .* in (?:french|spanish|german)"
]

for pattern in patterns:
    try:
        re.compile(pattern)
        print(f"✓ {pattern} - valid")
    except re.error as e:
        print(f"✗ {pattern} - ERROR: {e}")
```

**Requirement**: All patterns must compile without errors

### Step 2: Update Each Skill YAML
For each skill listed above:
1. Open the SKILL.md file
2. Add `brief_description` field (if missing)
3. Add `triggers` field with keywords, verbs, patterns
4. Validate patterns compile (see Step 1)
5. Keep existing content unchanged (only modify YAML frontmatter)
6. **Maintain field separation**: Don't mix triggers with allowed-tools, permissions, etc.

### Step 3: Test Trigger Matching
For each skill, test that triggers work:
```bash
# Test web skill triggers
uv run agent -p "search the web for python"  # Should match "search"
uv run agent -p "fetch https://example.com"  # Should match pattern

# Test hello-extended skill triggers
uv run agent -p "say bonjour to Alice"  # Should match "bonjour"
uv run agent -p "greet me in french"     # Should match pattern

# Test osdu skill triggers
uv run agent -p "analyze pipeline reliability"  # Should match keywords

# Test kalshi-markets skill triggers
uv run agent -p "what are the election odds"  # Should match pattern
```

### Step 3: Validate with Trace Logging
```bash
export LOG_LEVEL=TRACE ENABLE_SENSITIVE_DATA=true

# Before: No trigger match → breadcrumb (~10 tokens)
uv run agent -p "random query"

# After: Trigger match → full docs (~1,200 tokens)
uv run agent -p "search the web"

# Compare token counts
cat ~/.agent/logs/session-*-trace.log | jq '.tokens'
```

### Step 4: Update Tests
Add test cases in `tests/unit/skills/test_context_provider.py`:
```python
@pytest.mark.asyncio
async def test_web_skill_triggers():
    """Test that web skill matches on various triggers."""
    # Test cases for "search", "fetch", URL patterns
    pass

@pytest.mark.asyncio
async def test_hello_extended_triggers():
    """Test that hello-extended matches on greetings."""
    # Test cases for "bonjour", "hola", "say X in Y"
    pass
```

## Expected Benefits

### Token Efficiency
With explicit triggers, queries like:
- "search for python tutorials" → Match web skill → Inject web docs only
- "what are betting odds" → Match kalshi skill → Inject kalshi docs only
- "random unrelated query" → No match → Breadcrumb only

**Current**: All queries use breadcrumb (~10 tokens)
**After**: Relevant queries get targeted docs, others stay at breadcrumb

### User Experience
- **Better**: LLM gets relevant skill docs when needed
- **Faster**: Targeted docs → better context → better responses
- **Cheaper**: Only inject what's needed

### Discoverability
Skills remain discoverable via:
1. Breadcrumb `[4 skills available]` for non-matches
2. Registry on "what can you do?"
3. Full docs when triggers match

## Acceptance Criteria

### Trigger Requirements
- [ ] All 4 skills have `triggers` field in YAML frontmatter
- [ ] All skills have `brief_description` field
- [ ] Each skill has at least one trigger (minimum requirement)
- [ ] Each skill has 5-10 keywords relevant to its domain (recommended)
- [ ] Each skill has 3-5 verbs for action matching (recommended)
- [ ] Each skill has 1-3 patterns for complex queries (optional)
- [ ] All regex patterns compile without errors (validated via unit test)

### Validation
- [ ] Triggers tested with sample queries (manual)
- [ ] Token counts validate targeted injection (trace logs)
- [ ] No regressions (all skills still work)
- [ ] Tests updated to cover new trigger scenarios (unit tests)

### Consistency
- [ ] Every skill has both `brief_description` AND `triggers` in YAML
- [ ] `triggers` block is separate from other fields (allowed-tools, permissions, etc.)
- [ ] No schema drift (triggers only contain keywords/verbs/patterns)

### Documentation
- [ ] Maintenance checklist added to skills.md
- [ ] Trigger syntax documented with examples
- [ ] Best practices guide for future skill authors

## Validation Commands

```bash
# 1. Test each skill's triggers
uv run agent -p "search the web for AI news"
uv run agent -p "say hola to Bob"
uv run agent -p "check pipeline reliability"
uv run agent -p "what are the election odds"

# 2. Verify token counts with trace
export LOG_LEVEL=TRACE ENABLE_SENSITIVE_DATA=true

# Non-matching query (should use breadcrumb)
uv run agent -p "calculate 2+2"
# Check: Should be ~3,100 tokens

# Web skill trigger (should inject web docs)
uv run agent -p "search for tutorials"
# Check: Should be ~4,500 tokens (+1,400 for web docs)

# 3. Run test suite
uv run pytest tests/unit/skills/test_context_provider.py -v

# 4. Verify all skills still work
uv run pytest tests/unit/skills/ -v
```

## Migration Notes

### Backward Compatibility ✅
- Triggers are optional (backward compatible)
- Skills without triggers fall back to skill name only
- Existing skills continue working unchanged

### Rollout Strategy
1. **Phase 1**: Add triggers to web skill (most used)
2. **Phase 2**: Add triggers to hello-extended (bundled skill)
3. **Phase 3**: Add triggers to osdu and kalshi-markets
4. **Phase 4**: Document trigger best practices in skills.md

### Pattern Guidelines

**Keywords**: Nouns and domain terms
- Good: "search", "weather", "market", "pipeline"
- Avoid: Generic words like "get", "use", "help"

**Verbs**: Actions users might express
- Good: "search", "fetch", "analyze", "predict"
- Avoid: Overloaded verbs like "do", "make", "run"

**Patterns**: Complex phrases or format matching
- Good: `"https?://"`, `"say .* in .*"`, `"\\d+\\s*[+\\-*/]\\s*\\d+"`
- Avoid: Overly broad patterns like `".*search.*"`

**Testing**: Each pattern should match 2-3 example queries and exclude 2-3 non-examples

## Notes

### Why Not Done in Initial Implementation?
- Progressive disclosure infrastructure had to be built first
- Skills work well with implicit name triggers
- Can be added incrementally without breaking changes
- Allows validation of core system before enhancement

### Relationship to Progressive Disclosure
This enhancement builds on the progressive disclosure implementation:
- Progressive disclosure: Infrastructure for dynamic injection ✅ (done)
- Structured triggers: Content to make matching more effective ⚠️ (this spec)

Together they provide:
1. **Infrastructure**: ContextProvider for dynamic injection
2. **Intelligence**: Rich triggers for accurate matching
3. **Efficiency**: Only inject what's needed when it's needed

### Future Enhancements
After structured triggers are added, consider:
1. **Semantic matching**: Use embeddings for fuzzy matching
2. **Trigger analytics**: Track which triggers are most effective
3. **Auto-discovery**: Suggest triggers based on skill documentation
4. **Multi-language**: Support triggers in multiple languages

## Maintenance: Checklist for Future Skills

When authoring new skills, ensure YAML frontmatter includes:

### Required Fields
- [ ] `name`: Skill identifier (alphanumeric + hyphens)
- [ ] `description`: Full description of skill purpose and use cases
- [ ] `brief_description`: One-line summary (50-80 chars) for registry display
- [ ] `triggers`: At least one trigger type (keywords/verbs/patterns)

### Triggers Checklist
- [ ] **Keywords**: 5-10 domain-specific nouns (e.g., "search", "weather", "market")
- [ ] **Verbs**: 3-5 action words (e.g., "search", "fetch", "analyze")
- [ ] **Patterns** (optional): 1-3 regex for complex phrases (e.g., `"https?://"`, `"say .* in .*"`)
- [ ] All patterns compile without regex errors
- [ ] Triggers tested with 2-3 example queries

### Field Separation
- [ ] Keep `triggers` block separate from operational fields
- [ ] Don't mix `allowed-tools`, `permissions`, `toolsets` into triggers
- [ ] Maintain clean schema (prevents drift)

### Testing
- [ ] Test that skill matches on expected keywords
- [ ] Test that skill doesn't match on unrelated queries (word boundaries)
- [ ] Verify token injection with trace logging

**Example Template**:
```yaml
---
name: my-skill
description: "Full description of what this skill does..."
version: 1.0.0
brief_description: "Short one-line description"
triggers:
  keywords: [skill-domain, relevant, keywords]
  verbs: [action, words, here]
  patterns: ["optional.*regex"]
toolsets: []  # Separate from triggers
allowed-tools: []  # Separate from triggers
---
```

## Future Work (Out of Scope)

**Note**: The following enhancements are intentionally OUT OF SCOPE for this spec but may be considered in future iterations:

### Potential Phase 2 Enhancements
1. **Semantic Matching**: Use embeddings for fuzzy matching when keyword triggers miss
2. **LLM-Based Fallback**: Ask LLM to select relevant skills when confidence is low
3. **Trigger Auto-Discovery**: Analyze skill documentation to suggest triggers
4. **Multi-Language Triggers**: Support triggers in multiple languages
5. **Analytics**: Track trigger effectiveness and suggest improvements

**Why out of scope**:
- Keyword matching achieves 95.7% reduction (sufficient for Phase 1)
- Adding complexity before validating need would be premature
- Can be added later without breaking changes if gaps emerge

**When to consider**:
- High false-negative rate observed in production
- User feedback indicates missed skill activations
- Usage analytics show trigger coverage gaps

## Related Documentation

- [Progressive Discovery Implementation](bug-skill-progressive-discovery.md) - Infrastructure
- [Progressive Discovery ADR](../decisions/0019-skill-progressive-discovery.md) - Design decisions
- [Skills Architecture](../design/skills.md) - Overall skills design
- [Validation Report](bug-skill-progressive-discovery-VALIDATION.md) - Token analysis

## Execution

This spec can be implemented using:
```bash
/sdlc:implement docs/specs/add-skill-structured-triggers.md
```

Or manually:
1. Update each skill's SKILL.md YAML frontmatter
2. Test trigger matching with sample queries
3. Validate token counts with trace logging
4. Update tests to cover new trigger scenarios
5. Document trigger syntax in skills.md

---

**Estimated Effort**: 1-2 hours (15-20 min per skill)
**Priority**: Medium (nice-to-have, not blocking)
**Dependencies**: Requires progressive disclosure implementation (✅ complete)
**Impact**: Better keyword matching, more targeted documentation injection
