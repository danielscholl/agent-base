---
status: accepted
date: 2025-11-20
deciders: danielscholl
consulted: codebase-analyst agent
informed: development team
---

# Tool Docstring Optimization for Reduced LLM Token Consumption

## Context and Problem Statement

Tool docstrings are consuming excessive LLM context tokens due to comprehensive developer-focused documentation being sent to the LLM on every request. Telemetry shows **3,470 input tokens** for just **14 tools** (~248 tokens per tool), with the majority being verbose docstring content that the LLM doesn't need for tool routing decisions.

The Microsoft Agent Framework extracts the entire `__doc__` string from tool functions and sends it as the `description` field in tool schemas to the LLM. Our current docstrings include multi-line Args/Returns/Example sections, complete code examples (`>>> tools = HelloTools(config)`), 50+ line response format specifications, and implementation details—all optimized for developer documentation but excessive for LLM consumption.

**Question**: How can we reduce tool docstring token consumption while maintaining code readability for developers?

## Decision Drivers

- **Token efficiency**: Tool definitions dominate context budget and scale poorly as more tools are added
- **Cost optimization**: Every token sent to LLM has API cost implications
- **Context availability**: Reduced tool overhead leaves more tokens for conversation history and responses
- **Developer experience**: Code must remain readable and well-documented
- **Framework constraints**: Microsoft Agent Framework passes `func.__doc__` directly to LLM (no intermediate processing)
- **Existing patterns**: Skills system already uses "progressive disclosure" pattern (manifest vs scripts)

## Considered Options

1. **Two-tier documentation**: Concise LLM-facing docstrings + comprehensive module/class-level developer docs
2. **Custom tool decorator**: Intercept docstring extraction and transform at runtime
3. **Separate description files**: External JSON/YAML files with LLM-friendly descriptions
4. **Framework modification**: Fork/patch Microsoft Agent Framework to transform docstrings
5. **Status quo**: Keep current comprehensive docstrings

## Decision Outcome

Chosen option: **"Two-tier documentation"**, because:
- Surgical fix requiring no framework changes
- Maintains all developer documentation (moved to module/class level)
- Follows existing "progressive disclosure" pattern from skills system
- Reduces tokens by 70-80% per tool (~248 → ~50 tokens)
- Simple to implement and maintain
- No runtime overhead or complexity

### Consequences

- Good, because reduces token consumption by ~2,770 tokens per request (80% reduction for 14 tools)
- Good, because scales well (with 50 tools, saves ~9,900 tokens)
- Good, because maintains code readability through module-level documentation
- Good, because follows established patterns (skills progressive disclosure)
- Good, because no framework dependencies or custom tooling required
- Good, because improves cost efficiency for all LLM API calls
- Neutral, because requires documentation pattern change for future tools
- Neutral, because moves comprehensive docs from individual functions to module/class level
- Bad, because requires updating existing tool docstrings (one-time cost)
- Bad, because developers need to learn new pattern (mitigated by clear guidelines)

## Validation

Implementation validated through:
1. **Token counting tests**: New test suite `test_tool_token_efficiency.py` enforces <100 tokens per tool
2. **Format validation**: Tests ensure no code examples (`>>>`), no complete dict structures in docstrings
3. **Functional testing**: All existing tool tests must pass without modification
4. **Integration testing**: LLM routing accuracy unchanged with concise descriptions
5. **Telemetry measurement**: Before/after comparison via OpenTelemetry (target: <2000 input tokens)

## Pros and Cons of the Options

### Two-tier documentation (CHOSEN)

Concise function docstrings for LLM + comprehensive module/class docstrings for developers.

- Good, because surgical fix with no framework changes
- Good, because maintains all documentation (just reorganized)
- Good, because significant token reduction (70-80% per tool)
- Good, because follows existing progressive disclosure pattern
- Good, because simple to understand and implement
- Neutral, because requires updating existing docstrings (one-time effort)
- Neutral, because documentation in different location (module vs function level)

### Custom tool decorator

Create `@llm_tool(description="...")` decorator to override `__doc__` at registration.

- Good, because programmatic control over LLM descriptions
- Good, because keeps comprehensive docstrings intact on functions
- Bad, because adds runtime complexity and custom tooling
- Bad, because decorators may interfere with framework introspection
- Bad, because requires maintaining decorator infrastructure
- Bad, because doesn't follow existing patterns in codebase

### Separate description files

Store LLM-friendly descriptions in external JSON/YAML files.

- Good, because complete separation of concerns
- Good, because centralized tool descriptions
- Bad, because adds file management overhead
- Bad, because splits documentation across multiple locations
- Bad, because prone to synchronization issues (code vs description files)
- Bad, because increases maintenance burden

### Framework modification

Fork or patch Microsoft Agent Framework to transform docstrings.

- Good, because could apply transformations automatically
- Good, because no changes to existing docstrings needed
- Bad, because creates framework dependency and maintenance burden
- Bad, because complicates framework upgrades
- Bad, because doesn't follow established patterns
- Bad, because high complexity for marginal benefit

### Status quo

Keep current comprehensive docstrings.

- Good, because no changes needed
- Good, because documentation stays in familiar location
- Bad, because wastes ~2,770 tokens per request
- Bad, because scales poorly as tools are added
- Bad, because increases API costs unnecessarily

## More Information

### Pattern Examples

**Before (hello_world):**
```python
async def hello_world(self, name: str = "World") -> dict:
    """Say hello to someone.

    This is a simple demonstration tool that shows the basic patterns
    for tool implementation. It always succeeds and returns a greeting.

    Args:
        name: Name of person to greet (default: "World")

    Returns:
        Success response with greeting message in format:
        {
            "success": True,
            "result": "Hello, <name>!",
            "message": "Greeted <name>"
        }

    Example:
        >>> tools = HelloTools(config)
        >>> result = await tools.hello_world("Alice")
        >>> print(result["result"])
        Hello, Alice!
    """
```
**Tokens: ~180** (excessive for LLM routing)

**After (hello_world):**
```python
async def hello_world(self, name: str = "World") -> dict:
    """Say hello to someone. Returns greeting message."""
```
**Tokens: ~8** (96% reduction, sufficient for LLM routing)

**Comprehensive docs moved to class docstring:**
```python
class HelloTools(AgentToolset):
    """Hello World tools for demonstrating tool architecture.

    Detailed Implementation Guide:

    hello_world(name: str = "World") -> dict:
        Simple demonstration tool showing basic patterns. Always succeeds.
        Response: {"success": True, "result": "Hello, <name>!", "message": "Greeted <name>"}
        Tests: tests/unit/tools/test_hello_tools.py

    greet_user(name: str, language: str = "en") -> dict:
        Demonstrates error handling with language validation.
        Supported: en (English), es (Spanish), fr (French)
        Response: {"success": True, "result": "<greeting>", "message": "..."}
        Error: {"success": False, "error": "unsupported_language", "message": "..."}
    """
```

### Implementation Guidelines (Revised)

**Analysis of Claude Code's own tool descriptions** revealed that effective LLM tool descriptions require more context than initially planned. The optimal pattern balances token efficiency with critical usage information.

**Optimal Pattern:**
```
<What it does> <Key constraint>. <Critical usage note>. <Default behavior>. <Important return semantic>.
```

**Token Targets:**
- **Simple tools**: 10-20 tokens (just what + returns)
  - Example: `hello_world` - no critical constraints or defaults
- **Complex tools**: 25-40 tokens (what + constraints + defaults + returns)
  - Example: `read_file`, `write_file` - have security constraints and defaults
- **Maximum**: 50 tokens (never exceed)

**What to INCLUDE:**
1. ✅ **What the tool does** - Clear first sentence
2. ✅ **Critical constraints** - Information that prevents tool selection errors
   - "Paths relative to workspace root"
   - "Requires filesystem_writes_enabled"
3. ✅ **Required prerequisites** - Conditions that must be met
4. ✅ **Key defaults** - Default behaviors that affect usage
   - "Default: first 200 lines"
   - "Default: case-sensitive search"
5. ✅ **Important return semantics** - Non-obvious return information
   - "Returns truncation flag"
   - "Returns error if language unsupported"
6. ✅ **When NOT to use** - Critical negative guidance (if applicable)

**What to EXCLUDE:**
1. ✗ **Code examples** - `>>> tools = HelloTools(config)`
2. ✗ **Complete response format structures** - Full dict specifications
3. ✗ **All parameter details** - Schema provides type and description
4. ✗ **Implementation details** - How it works internally
5. ✗ **Edge case handling** - Detailed error scenarios

**Rationale for Revision:**

Initial optimization targeted 9-20 tokens universally, inspired by simple demonstration tools. However, analysis of Claude Code's own tool descriptions (which average 40-60 tokens) revealed that complex tools require critical usage information:
- **Read tool**: "The file_path parameter must be an absolute path" (~60 tokens)
- **Grep tool**: "ALWAYS use Grep for search tasks. NEVER invoke grep" (~55 tokens)
- **Bash tool**: "DO NOT use it for file operations - use specialized tools" (~60 tokens)

These include critical notes, defaults, and constraints that prevent usage errors. Applying this insight:
- **HelloTools** (simple): 9-22 tokens ✓ - appropriate for demonstration tools
- **FileSystemTools** (complex): 25-40 tokens ✓ - includes security constraints, defaults, prerequisites

### Related Decisions

- **ADR-0006**: Class-based Toolset Architecture - Established toolset patterns
- **ADR-0007**: Tool Response Format - Defines structured responses (separate from documentation)
- **Skills Architecture** (docs/design/skills.md): Progressive disclosure pattern (manifest vs scripts)

### Measurement Results

**Current state (baseline):**
- Total input tokens: 3,470 for 14 tools
- Average per tool: ~248 tokens
- Primary contributor: Verbose docstrings with examples and complete response formats

**After optimization (measured/projected):**
- **HelloTools** (2 simple tools): 31 tokens total (~15 tokens/tool) - 90% reduction ✓
- **FileSystemTools** (7 complex tools): ~210 tokens projected (~30 tokens/tool) - 86% reduction
- **Bundled skills** (5 tools): ~100 tokens projected (~20 tokens/tool)
- **Total for 14 tools**: ~341 tokens (vs 3,470)
- **Overall savings: 3,129 tokens per request (90% reduction)**

**Revised scaling benefits:**
- With 30 tools: Saves ~6,900 tokens (assuming 70% simple, 30% complex)
- With 50 tools: Saves ~11,500 tokens
- With 100 tools: Saves ~23,000 tokens

**Comparison to initial target:**
- Initial target: ~50 tokens/tool average (80% reduction)
- Revised target: ~24 tokens/tool average (90% reduction) - better than expected!

### Implementation Plan

Phased rollout:
1. **Phase 1**: HelloTools (2 tools) - Proof of concept
2. **Phase 2**: FileSystemTools (7 tools) - Core tools
3. **Phase 3**: Bundled skills + documentation updates

### Testing Strategy

- Token efficiency test suite: `tests/unit/tools/test_tool_token_efficiency.py`
- Format validation: No `>>>` examples, no complete dict structures
- Functional validation: All existing tests pass unchanged
- Integration validation: LLM routing accuracy unchanged

### Documentation Updates

- **CONTRIBUTING.md**: Updated with new docstring pattern and examples
- **Specification**: `docs/specs/bug-excessive-tool-docstring-tokens.md`
- **This ADR**: Decision record and rationale

### Revised FileSystemTools Examples (25-40 Token Pattern)

Applying the refined pattern with critical constraints and defaults:

```python
# get_path_info (~25 tokens)
"""Get file/directory metadata within workspace. Returns exists, type, size, permissions, timestamps."""

# list_directory (~30 tokens)
"""List directory contents within workspace with metadata. Supports recursive traversal. Default: 200 entries max, excludes hidden files. Returns entries with type and size."""

# read_file (~32 tokens)
"""Read text file within workspace by line range. Paths relative to workspace root. Default: first 200 lines. Returns content with truncation flag for large files."""

# search_text (~35 tokens)
"""Search text patterns across files in workspace. Supports literal (default) and regex modes. Case-sensitive by default. Max 50 matches. Returns matches with file, line, snippet."""

# write_file (~28 tokens)
"""Write file within workspace with safety checks. Requires filesystem_writes_enabled. Supports create/overwrite/append modes. Returns bytes written and mode used."""

# apply_text_edit (~32 tokens)
"""Apply exact text replacement in file within workspace. Requires filesystem_writes_enabled and exact match. Use replace_all for multiple occurrences. Returns replacement count and size delta."""

# create_directory (~24 tokens)
"""Create directory within workspace with optional parent creation. Requires filesystem_writes_enabled. Idempotent (success if exists). Returns created flag."""
```

**Token analysis:**
- Average: ~29 tokens per tool
- Range: 24-35 tokens
- Total for 7 tools: ~203 tokens (vs current ~1,520)
- **Savings: 1,317 tokens (87% reduction)**

**What makes these better:**
- ✅ Security context: "within workspace", "relative to workspace root"
- ✅ Prerequisites: "Requires filesystem_writes_enabled"
- ✅ Defaults: "Default: 200 entries max", "Default: first 200 lines"
- ✅ Key features: "Supports recursive traversal", "Supports create/overwrite/append"
- ✅ Return semantics: "truncation flag", "replacement count"
- ✅ Important behaviors: "Idempotent (success if exists)"

### Future Enhancements

- Automatic token tracking in middleware (log tool definition token counts)
- Token budget alerts (warn when tool definitions exceed threshold)
- CI validation (fail if any tool docstring exceeds 50 tokens for complex tools, 20 for simple)
- Documentation generation (auto-generate comprehensive docs from concise docstrings)
