# Bug Fix: Excessive Tool Docstring Token Consumption

## Bug Description

Tool docstrings are consuming excessive LLM context tokens due to comprehensive developer-focused documentation being sent to the LLM on every request. Current telemetry shows **3,470 input tokens** for just **14 tools** (~248 tokens per tool), with the majority being verbose docstring content that the LLM doesn't need.

### Symptoms
- High input token usage even for simple requests
- Tool definitions dominate context budget
- Detailed implementation examples, response format specifications, and developer notes are sent to LLM
- Scales poorly as more tools are added

### Expected vs Actual Behavior

**Expected**: Tool descriptions should provide concise "what" and "when" information for LLM routing (~30-50 tokens per tool)

**Actual**: Tool descriptions include full developer documentation with multi-line Args/Returns/Example sections, code snippets, and complete response format specifications (~150-300 tokens per tool)

## Problem Statement

The Microsoft Agent Framework extracts the entire `__doc__` string from tool functions and sends it as the `description` field in tool schemas to the LLM. Our current docstrings are optimized for developer documentation (great for code readability) but create excessive token consumption when passed to LLMs.

**Specific issues:**
1. **Code examples** showing instantiation (`>>> tools = HelloTools(config)`)
2. **Complete response format specifications** (50+ lines of dictionary structure)
3. **Multi-paragraph explanations** of implementation details
4. **Internal implementation notes** about validation, security, edge cases

## Solution Statement

Implement a **two-tier documentation approach**:
1. **LLM-facing docstrings**: Concise, action-oriented descriptions (first line + brief Args/Returns)
2. **Developer documentation**: Comprehensive details in module-level docstrings, comments, or separate docs

This approach:
- Reduces token consumption by ~70-80% per tool
- Maintains code readability for developers
- Follows existing "progressive disclosure" pattern used by skills system
- Requires no framework changes (surgical fix)

## Steps to Reproduce

1. Start agent with telemetry enabled:
   ```bash
   agent --telemetry start
   export ENABLE_OTEL=true
   ```

2. Make a simple request:
   ```bash
   agent -p "Say hello"
   ```

3. Check Aspire Dashboard at http://localhost:18888

4. Observe: **input_tokens: 3470** for minimal request

5. Inspect tool definitions in span attributes or logs

6. Note: Tool `description` fields contain full docstrings with examples, complete response formats, implementation details

## Root Cause Analysis

### Framework Integration

The Microsoft Agent Framework (`agent_framework/_tools.py`) extracts tool metadata as follows:

```python
def ai_function(func):
    tool_desc: str = description or (f.__doc__ or "")  # <-- Uses full __doc__
    return AIFunction(
        name=tool_name,
        description=tool_desc,  # <-- This goes to LLM
        func=f,
    )
```

**Key finding**: No intermediate processing of docstrings. The entire `__doc__` attribute is passed directly to the LLM.

### Current Docstring Pattern

All tools follow this comprehensive pattern (example from `hello.py:54-78`):

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

**Token analysis**:
- Current: ~180 tokens
- Needed for LLM: ~15 tokens ("Say hello to someone. Returns greeting message.")
- Waste: ~165 tokens per tool (91% reduction possible)

### Why This Wasn't Caught Earlier

1. **No token tracking** for tool definitions (only skill instructions are tracked)
2. **Developer-first culture**: Docstrings written for code documentation
3. **No guidance** in ADRs or CONTRIBUTING.md about LLM consumption
4. **Tests validate presence**, not efficiency (check docstring exists, not length)
5. **Skills use progressive disclosure**, but pattern not applied to core tools

## Related Documentation

### Requirements
- None directly address tool description optimization

### Architecture Decisions
- **ADR-0006**: Class-based Toolset Architecture - Shows brief docstring examples but doesn't mandate brevity
- **ADR-0007**: Tool Response Format - Defines structured responses but not documentation format
- **ADR-0008**: Testing Strategy - Defines coverage targets but not docstring efficiency tests

### Related Patterns
- **Skills Architecture** (`docs/design/skills.md`): Uses progressive disclosure pattern
  - Manifest: ~250 tokens (loaded at startup)
  - Scripts: Loaded only on invocation
  - Pattern applicable to tools: Brief docstring + detailed external docs

## Codebase Analysis Findings

### Current State
- **14 tools** across 2 toolsets (HelloTools, FileSystemTools) + skills
- **Pattern consistency**: All tools follow comprehensive docstring format
- **No optimization efforts**: First issue raised about token consumption
- **Testing gap**: Tests verify docstrings exist, not efficiency

### Error Patterns
- No error handling for token limits
- No warnings when tool definitions exceed thresholds
- No metrics/logging for tool schema token usage

### Similar Fixes
- None in history
- Skills system provides a pattern (progressive disclosure)
- Token counting utility exists (`src/agent/utils/tokens.py`)

### Dependencies
- **Microsoft Agent Framework**: Uses `func.__doc__` directly (no modification needed)
- **Type hints**: Already optimal via `Annotated[type, Field(description="...")]`
- **Structured responses**: Separate from docstrings (no changes needed)

### Side Effects
- **Tests**: Need updates to validate concise format
- **Contributing docs**: Need updated examples
- **Existing skills**: May need review/updates
- **Developer onboarding**: Need clear guidance on two-tier approach

## Archon Project

Project ID: (Will be created if Archon is configured)

## Relevant Files

### Files to Fix

1. **src/agent/tools/hello.py** (~144 lines)
   - Optimize: `hello_world()` docstring (lines 54-78)
   - Optimize: `greet_user()` docstring (lines 82-128)
   - Move detailed docs to module-level or class-level docstring

2. **src/agent/tools/filesystem.py** (~800+ lines)
   - Optimize: 7 tool function docstrings
   - `get_path_info()`, `list_directory()`, `read_file()`, `search_text()`, `write_file()`, `apply_text_edit()`, `create_directory()`
   - Each currently 40-80 lines, target 5-10 lines

3. **src/agent/_bundled_skills/hello-extended/toolsets/hello.py**
   - Optimize: Skill toolset examples
   - `greet_in_language()`, `greet_multiple()`

### Files to Test

1. **tests/unit/tools/test_hello_tools.py**
   - Update: Docstring validation tests
   - Add: Token consumption tests
   - Add: Concise format validation

2. **tests/unit/tools/test_filesystem_tools.py**
   - Update: Docstring validation tests
   - Add: Token consumption validation

3. **New: tests/unit/tools/test_tool_token_efficiency.py**
   - Add: Token counting for all tools
   - Add: Threshold validation (<100 tokens per tool)
   - Add: Format validation (no code examples in docstrings)

### New Files

1. **docs/decisions/0017-tool-docstring-optimization.md**
   - Document: Decision to optimize tool docstrings
   - Rationale: Token consumption reduction
   - Pattern: Two-tier documentation approach
   - Examples: Before/after comparisons

2. **docs/design/tool-documentation-guidelines.md** (Optional)
   - Guidelines: Writing LLM-friendly docstrings
   - Examples: Good vs bad patterns
   - Template: Recommended structure

## Implementation Plan

### Phase 1: Immediate Fix (HelloTools)
Start with HelloTools as proof-of-concept:
1. Create ADR documenting optimization pattern
2. Optimize hello.py docstrings (2 tools)
3. Add module-level comprehensive documentation
4. Update tests to validate concise format
5. Measure token reduction

### Phase 2: Core Tools (FileSystemTools)
Apply pattern to larger toolset:
1. Optimize filesystem.py docstrings (7 tools)
2. Add comprehensive documentation as class docstring or comments
3. Update tests
4. Measure cumulative token reduction

### Phase 3: Validation & Documentation
Ensure sustainability:
1. Update CONTRIBUTING.md with new pattern
2. Create test template for token-efficient tools
3. Add token consumption tracking to middleware (optional)
4. Update skill toolset examples

## Step by Step Tasks

### Task 1: Create ADR for Tool Docstring Optimization
- **Description**: Document the decision to optimize tool docstrings for LLM consumption
- **Files to modify**:
  - `docs/decisions/0017-tool-docstring-optimization.md` (new)
- **Changes**:
  - Context: Current token consumption issue
  - Decision: Two-tier documentation approach
  - Consequences: Reduced tokens, maintained developer docs
  - Examples: Before/after comparisons
- **Archon task**: Will be created during implementation

### Task 2: Optimize HelloTools Docstrings
- **Description**: Convert hello.py docstrings to concise LLM-friendly format
- **Files to modify**:
  - `src/agent/tools/hello.py`
- **Changes**:
  - `hello_world()`: "Say hello to someone. Returns greeting message."
  - `greet_user()`: "Greet user in different languages (en, es, fr). Returns localized greeting."
  - Move comprehensive docs to module docstring
- **Archon task**: Will be created during implementation

### Task 3: Add Module-Level Documentation
- **Description**: Create comprehensive developer documentation at module level
- **Files to modify**:
  - `src/agent/tools/hello.py` (module docstring)
- **Changes**:
  - Add detailed implementation notes
  - Add response format specifications
  - Add usage examples for developers
  - Reference from individual tool docstrings if needed
- **Archon task**: Will be created during implementation

### Task 4: Update HelloTools Tests
- **Description**: Update tests to validate concise docstring format
- **Files to modify**:
  - `tests/unit/tools/test_hello_tools.py`
- **Changes**:
  - Update docstring validation tests
  - Add max length assertions (<100 chars per tool)
  - Add format validation (no >>> examples, no complete dicts)
- **Archon task**: Will be created during implementation

### Task 5: Measure Token Reduction
- **Description**: Use existing token utilities to measure improvement
- **Files to modify**:
  - New test file or script
- **Changes**:
  - Count tokens for old vs new docstrings
  - Log reduction percentage
  - Validate <100 tokens per tool target
- **Archon task**: Will be created during implementation

### Task 6: Optimize FileSystemTools Docstrings
- **Description**: Apply pattern to all 7 filesystem tools
- **Files to modify**:
  - `src/agent/tools/filesystem.py`
- **Changes**:
  - `get_path_info()`: "Get file/directory metadata. Returns exists, type, size, permissions."
  - `list_directory()`: "List directory contents. Returns entries with name, type, size."
  - `read_file()`: "Read text file by line range. Returns content with pagination support."
  - `search_text()`: "Search for text patterns across files. Supports literal and regex."
  - `write_file()`: "Write file with safety checks. Requires filesystem_writes_enabled."
  - `apply_text_edit()`: "Apply exact text replacement. Requires filesystem_writes_enabled."
  - `create_directory()`: "Create directory with optional parent creation."
  - Move detailed docs to class docstring
- **Archon task**: Will be created during implementation

### Task 7: Update FileSystemTools Tests
- **Description**: Update filesystem tool tests for concise format
- **Files to modify**:
  - `tests/unit/tools/test_filesystem_tools.py`
- **Changes**:
  - Update docstring validation
  - Add token efficiency tests
  - Validate no code examples in docstrings
- **Archon task**: Will be created during implementation

### Task 8: Create Token Efficiency Test Suite
- **Description**: Add comprehensive token tracking for all tools
- **Files to modify**:
  - `tests/unit/tools/test_tool_token_efficiency.py` (new)
- **Changes**:
  - Import all toolsets
  - Count tokens for each tool docstring
  - Assert <100 tokens per tool
  - Generate report of token usage
  - Fail if any tool exceeds threshold
- **Archon task**: Will be created during implementation

### Task 9: Update CONTRIBUTING.md
- **Description**: Update developer guidelines with new docstring pattern
- **Files to modify**:
  - `CONTRIBUTING.md`
- **Changes**:
  - Add section on LLM-friendly docstrings
  - Provide before/after examples
  - Explain two-tier documentation approach
  - Update tool implementation template
- **Archon task**: Will be created during implementation

### Task 10: Optimize Bundled Skill Toolsets
- **Description**: Apply pattern to skill toolset examples
- **Files to modify**:
  - `src/agent/_bundled_skills/hello-extended/toolsets/hello.py`
- **Changes**:
  - Optimize `greet_in_language()` docstring
  - Optimize `greet_multiple()` docstring
  - Update as example for skill developers
- **Archon task**: Will be created during implementation

## Testing Strategy

### Regression Tests
Validator agent will create tests during implementation phase to ensure:

1. **Tool functionality unchanged**
   - All existing tool tests pass
   - Tool invocation works identically
   - Structured responses unchanged

2. **Docstring format validation**
   - All tools have docstrings (non-empty)
   - Docstrings are concise (<100 tokens)
   - No code examples (`>>>` not in docstrings)
   - No complete dict structures (response formats)
   - Key phrases present (tool purpose clear)

3. **Framework integration**
   - Tools register correctly with framework
   - Tool schemas generated properly
   - Parameter descriptions preserved (from Field annotations)
   - LLM can invoke tools successfully

### Edge Case Tests

1. **Empty or missing docstrings**
   - Verify tools fail validation if docstring missing
   - Verify meaningful error messages

2. **Parameter descriptions**
   - Verify Field(description="...") preserved
   - Verify parameter schemas correct
   - Verify LLM receives parameter info

3. **Skill toolsets**
   - Verify skill tools follow same pattern
   - Verify skill loading unchanged
   - Verify script tools work correctly

### Impact Tests

1. **Token consumption**
   - Measure tool definition tokens before/after
   - Target: 70-80% reduction per tool
   - Target: <100 tokens per tool
   - Overall target: <1500 tokens for 14 tools (vs current 3470)

2. **LLM routing accuracy**
   - Verify LLM still selects correct tools
   - Test with variety of prompts
   - Compare before/after tool selection

3. **Developer experience**
   - Verify code remains readable
   - Verify comprehensive docs accessible
   - Verify new developers can understand tools

## Acceptance Criteria

- [ ] All tool docstrings optimized to <100 tokens each
- [ ] Comprehensive developer documentation preserved (module/class level)
- [ ] All existing tests pass without modification (except docstring validation)
- [ ] New token efficiency tests added and passing
- [ ] ADR created documenting the optimization pattern
- [ ] CONTRIBUTING.md updated with new guidelines
- [ ] Measured token reduction: ≥70% per tool, ≥50% overall
- [ ] LLM routing accuracy unchanged (integration test)
- [ ] No performance degradation
- [ ] Coverage remains ≥85%

## Validation Commands

```bash
# Measure current token usage
uv run python -c "
from agent.utils.tokens import count_tokens
from agent.tools.hello import HelloTools
from agent.config import AgentConfig
config = AgentConfig.from_env()
tools = HelloTools(config)
for tool in tools.get_tools():
    tokens = count_tokens(tool.__doc__ or '')
    print(f'{tool.__name__}: {tokens} tokens')
"

# Run all tests
uv run pytest -m "not llm" -n auto --cov=src/agent --cov-fail-under=85

# Run token efficiency tests (after implementation)
uv run pytest tests/unit/tools/test_tool_token_efficiency.py -v

# Run tool tests specifically
uv run pytest tests/unit/tools/test_hello_tools.py -v
uv run pytest tests/unit/tools/test_filesystem_tools.py -v

# Verify LLM integration (requires API key, costs money)
uv run pytest -m llm tests/integration/llm/test_tool_invocation.py -v

# Check with telemetry
agent --telemetry start
export ENABLE_OTEL=true
agent -p "Say hello" --verbose
# Check http://localhost:18888 for input_tokens (should be <2000)

# Code quality
uv run black src/agent/tools/ tests/unit/tools/
uv run ruff check --fix src/agent/tools/ tests/unit/tools/
uv run mypy src/agent/tools/
```

## Notes

### Token Reduction Estimates

**Current state (14 tools):**
- Input tokens: 3,470
- Average per tool: ~248 tokens

**After optimization (conservative):**
- Average per tool: ~50 tokens (80% reduction)
- Total for 14 tools: ~700 tokens
- **Savings: 2,770 tokens per request** (80% reduction)

**Scaling benefits:**
- With 30 tools: Saves ~5,940 tokens
- With 50 tools: Saves ~9,900 tokens
- With 100 tools: Saves ~19,800 tokens

### Pattern Examples

**Before (hello_world):**
```python
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
**Tokens: ~180**

**After (hello_world):**
```python
"""Say hello to someone. Returns greeting message."""
```
**Tokens: ~8 (96% reduction)**

**Comprehensive docs moved to:**
```python
class HelloTools(AgentToolset):
    """Hello World tools for demonstrating tool architecture.

    Detailed Implementation Guide:

    hello_world(name: str = "World") -> dict:
        Simple demonstration tool showing basic patterns. Always succeeds.
        Response format: {"success": True, "result": "Hello, <name>!", "message": "Greeted <name>"}
        Example usage in tests: tests/unit/tools/test_hello_tools.py

    greet_user(name: str, language: str = "en") -> dict:
        Demonstrates error handling with language validation.
        Supported: en (English), es (Spanish), fr (French)
        Response format: {"success": True, "result": "<greeting>", "message": "..."}
        Error format: {"success": False, "error": "unsupported_language", "message": "..."}
    """
```

### Future Enhancements

1. **Automatic token tracking**: Add middleware logging for tool definition tokens
2. **Token budget alerts**: Warn when tool definitions exceed threshold
3. **Documentation generation**: Auto-generate comprehensive docs from concise docstrings
4. **Skill template updates**: Update skill templates with optimized pattern
5. **CI validation**: Add token efficiency to CI pipeline

## Execution

This spec can be implemented using: `/sdlc:implement docs/specs/bug-excessive-tool-docstring-tokens.md`
