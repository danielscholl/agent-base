# Feature: Workspace Filesystem Tools

## Feature Description

Add a cross-platform, sandboxed filesystem toolset to Agent Base that enables agents to inspect and modify files in a controlled workspace, without exposing arbitrary OS shell execution to the LLM.

This feature introduces a `FileSystemTools` toolset that offers:

- **Structured Directory Listing**: List files and directories with metadata, with safe recursion and entry limits
- **Chunked File Reading**: Read text files by line range with truncation indicators and navigation metadata
- **Path Information**: Check file/directory existence and retrieve metadata safely
- **Text Search**: Search for literal text (with optional regex) within files using glob patterns and match limits
- **Guarded Writes and Edits**: Optional, configuration-gated tools for writing files and applying precise text edits
- **Directory Creation**: Create directories for organizing agent-generated outputs
- **Workspace Sandboxing**: All operations constrained to a required workspace root, consistent on macOS, Linux, and Windows

The goal is to give the agent safe, structured file operations that replace arbitrary shell access while maintaining predictability, observability, and cross-platform behavior.

## User Story

As a **developer using Agent Base to build specialized agents**
I want **structured, sandboxed filesystem tools**
So that **my agents can safely inspect and modify project files across platforms without risking arbitrary command execution, path traversal attacks, or filesystem damage**

## Problem Statement

Currently, Agent Base only provides a “hello world” toolset and has no built-in capabilities for working with the local filesystem. This creates several limitations:

1. **No File Inspection**: The agent cannot list directories or inspect project files, limiting its usefulness for code review, refactoring, and debugging workflows.
2. **No Controlled Editing**: There is no pattern for safe, incremental edits to files (e.g., patching a function body) under LLM control.
3. **Cross-Platform Complexity**: A naive “shell tool” that simply executes OS commands would need to handle differences between macOS, Linux, and Windows (paths, commands, quoting), and it is difficult to constrain safely.
4. **Safety Risks**: Exposing arbitrary shell access to an LLM raises risks of destructive operations (`rm -rf`, registry modifications, system-level commands) and accidental data exfiltration.
5. **Lack of Structure**: Raw command output is unstructured text, making it harder for the agent to reason about results, paginate content, or handle large files in a predictable way.
6. **No Observability Hooks**: Without a structured filesystem toolset, we cannot easily emit metrics, spans, or events for file operations.

A solution is needed that provides shell-like capabilities in a structured, cross-platform, and sandboxed way that fits the existing Agent Base architecture.

## Solution Statement

Implement a `FileSystemTools` toolset that provides structured, sandboxed file operations via strongly-typed Python tools, replacing the need for raw OS shell commands.

The solution will:

1. **Require Explicit Workspace Root**
   - Require `workspace_root` configuration (environment variable or config file)
   - Enforce that all paths resolve under this root (no `..` escapes, symlinks that escape, or absolute paths outside workspace)
   - Use `pathlib.Path.resolve()` for cross-platform path handling and symlink resolution
   - Fail gracefully when workspace_root is not configured (tools disabled with clear error message)

2. **Provide Read-Only Tools First**
   - `get_path_info(path)` - Check existence, type, size, permissions (safe metadata queries)
   - `list_directory(path, recursive, max_entries, include_hidden)` - Structured directory listings
   - `read_file(path, start_line, max_lines)` - Chunked text file reading with UTF-8 encoding
   - `search_text(query, path, glob, max_matches, use_regex)` - Literal string or regex search
   Each tool returns structured responses with metadata (truncation flags, next offsets, total counts)

3. **Add Guarded Write Tools Behind Config**
   - `write_file(path, content, mode)` with modes: `create`, `overwrite`, `append`
   - `apply_text_edit(path, expected_text, replacement_text, replace_all)` for surgical edits with safety checks
   - `create_directory(path, parents)` for organizing agent-generated outputs
   - Writes disabled by default; require explicit `filesystem_writes_enabled=true` configuration
   - Enforce size limits (`filesystem_max_write_bytes`) and return clear error codes

4. **Integrate with Existing Patterns**
   - Implement as `AgentToolset` subclass, taking `AgentConfig` via constructor
   - Return responses in standard `{success, result|error, message}` format
   - Leverage middleware for automatic observability (logging, events, OTEL spans)
   - Integrate with display system via existing event bus patterns
   - Follow same testing patterns as HelloTools and memory components

5. **Ensure Cross-Platform Behavior**
   - Use Python stdlib (`pathlib`, `os`, `glob`, `fnmatch`) exclusively
   - Handle platform-specific path separators transparently
   - Detect and reject binary files in text operations (UTF-8 with `errors="replace"`)
   - Normalize line endings (`\r\n`, `\n`, `\r`) in a platform-appropriate way

6. **Observability and Privacy**
   - Log file paths, operation types, and metadata
   - DO NOT log full file contents (privacy/performance concern)
   - Log only first 100 chars of search queries and results
   - Leverage existing middleware instrumentation automatically

This design provides focused file operations with safety guarantees, predictability, and full testability.

## Explicitly Out of Scope

To prevent scope creep and maintain security boundaries, the following capabilities are **explicitly not included** in this feature:

**File Operations Not Included**:
- ❌ `delete_file` / `delete_directory` - Destructive operations too risky for LLM control
- ❌ `move_file` / `rename_file` - Can be implemented via read + write + delete if needed later
- ❌ `copy_file` - Can be implemented via read + write if needed later
- ❌ Symlink creation (`create_symlink`) - Security complexity, can follow existing symlinks only

**Command Execution**:
- ❌ Arbitrary shell command execution - This is the whole point of structured tools
- ❌ Process spawning or system calls - Use Bash tool if needed (not part of filesystem tools)
- ❌ Environment variable manipulation - Not filesystem concern

**Binary File Operations**:
- ❌ `read_file_bytes` / `write_file_bytes` - Binary files are explicitly rejected in this phase
- ❌ Binary file editing or manipulation - Use specialized tools if needed
- ❌ MIME type detection beyond simple null-byte check

**Advanced Features**:
- ❌ File watching / change notifications - Complex, requires background tasks
- ❌ Archive operations (zip, tar, gzip) - Specialized tools, not core filesystem
- ❌ Diff/patch operations - Can be added later if needed
- ❌ File locking or concurrent access control - OS handles this
- ❌ Extended attributes or metadata modification

**Search Limitations**:
- ❌ Full-text indexing or semantic search - Use dedicated search tools
- ❌ Syntax-aware search (AST-based code search) - Too complex for initial version
- ❌ Fuzzy matching or similarity search - Keep it simple

**Why These Boundaries Matter**:
- **Safety**: Destructive operations (delete, move) are too risky for initial LLM control
- **Simplicity**: Focus on 80% use case (read, write, edit, search) rather than 100% completeness
- **Security**: No arbitrary command execution defeats the purpose of structured tools
- **Maintenance**: Smaller surface area means better testing and fewer bugs

**Future Considerations**: Some out-of-scope items (like delete, move, copy) could be added in later phases with additional safety guardrails (confirmation prompts, undo capability, etc.). For now, keeping the scope focused ensures a robust, well-tested foundation.

## Related Documentation

### Requirements

- `docs/design/requirements.md`  
  - FR-FOUND-2: Natural Language Query Interface (agents should reason about code and files)  
  - FR-FOUND-4: Tool Integration Pattern (class-based toolsets, structured responses)  
  - FR-FOUND-5: Event Bus for Component Coordination (file operations should produce events)  
  - FR-FOUND-6: Middleware Integration Pattern (cross-cutting concerns for tools)
- `docs/specs/foundation.md`  
  - Tool architecture and patterns (HelloTools as foundational example)

### Architecture Decisions

- `docs/decisions/0005-event-bus-pattern-for-loose-coupling.md`  
  - Event bus used for visualization and potential future coordination around filesystem operations.
- `docs/decisions/0006-class-based-toolset-architecture.md`  
  - Guides the design of `FileSystemTools` as a dependency-injected toolset.
- `docs/decisions/0008-testing-strategy-and-coverage-targets.md`  
  - Applies to filesystem tools (high coverage with no real external dependencies).
- `docs/decisions/0012-middleware-integration-strategy.md`  
  - Middleware will emit events and telemetry for filesystem tools.
- `docs/specs/observability-integration.md`  
  - Filesystem tools will be instrumented via existing observability hooks.
- `docs/specs/memory-support.md`  
  - Similar structured response and naming conventions apply.

## Codebase Analysis Findings

### Architecture Patterns to Follow

- **Dependency Injection**:  
  - `FileSystemTools` must accept `AgentConfig` in its constructor, following `AgentToolset` and `MemoryManager` patterns.  
  - Workspace root and write permissions should be driven from configuration/env, not global state.

- **Structured Responses**:  
  - All tool methods return the standardized result shape:  
    - Success: `{"success": True, "result": {...}, "message": "..."}`  
    - Error: `{"success": False, "error": "code", "message": "..."}`  
  - This aligns with HelloTools, memory managers, and observability helpers.

- **Event-Driven & Observable**:  
  - Middleware (`logging_function_middleware`) already emits ToolStart/ToolComplete/ToolError events and OTEL spans.  
  - Filesystem tools automatically benefit from this; no special wiring required beyond being registered as tools.

- **Async-First & Testable**:  
  - Tools should be async, but internal filesystem operations can use sync stdlib calls, wrapped in coroutines (no external I/O like network).  
  - Easy to test with temporary directories and fixtures.

### Naming & Structure

- **Module**: `src/agent/tools/filesystem.py`
- **Class**: `FileSystemTools(AgentToolset)`
- **Functions**: `get_path_info`, `list_directory`, `read_file`, `search_text`, `write_file`, `apply_text_edit`, `create_directory`
- **Config Fields** (in `AgentConfig` / `AgentSettings`):
  - `workspace_root: Path | None` (optional in schema, defaults to `Path.cwd()` when None)
    - Defaults to current working directory for immediate usability
    - Can be overridden via settings.json or AGENT_WORKSPACE_ROOT environment variable
  - `filesystem_writes_enabled: bool` (default: False)
  - `filesystem_max_read_bytes: int` (default: 10MB)
  - `filesystem_max_write_bytes: int` (default: 1MB)

### Error Codes

Common error codes to standardize (following Agent Base conventions):

**Path & Workspace Errors**:
- `path_traversal_attempt` - User input contains `..` or suspicious patterns (detected before resolution)
- `path_outside_workspace` - Resolved path falls outside workspace boundary (detected after resolution)
- `symlink_outside_workspace` - Symlink target resolves outside workspace
- `not_found` - File or directory does not exist at given path
- `not_a_file` - Path exists but is not a regular file (e.g., is a directory or special file)
- `not_a_directory` - Path exists but is not a directory (e.g., is a regular file)
- `permission_denied` - Filesystem permissions prevent operation

**File Content Errors**:
- `file_too_large` - File exceeds configured `filesystem_max_read_bytes` limit
- `is_binary` - File detected as binary (contains null bytes), cannot read as text
- `line_out_of_range` - Requested start_line beyond file length

**Write Operation Errors**:
- `writes_disabled` - Filesystem writes not enabled in configuration
- `write_too_large` - Content exceeds `filesystem_max_write_bytes`
- `invalid_mode` - Unknown write mode specified (not create/overwrite/append)
- `file_exists` - File already exists (only for `mode="create"`)

**Edit Operation Errors**:
- `match_not_found` - expected_text not found in file (0 occurrences)
- `multiple_matches` - expected_text found multiple times when replace_all=False (ambiguous)
- `empty_expected_text` - expected_text cannot be empty string

**Search Errors**:
- `invalid_regex` - Regex pattern is malformed (when use_regex=True)
- `regex_timeout` - Regex took too long (catastrophic backtracking protection)

**Note on encoding errors**: Files with encoding issues are handled gracefully via `errors="replace"` rather than returning an error. The `encoding_errors: bool` field in responses indicates if replacement occurred.

These codes enable predictable error handling in tests and higher-level agent behaviors.

## Design Details

### Workspace Root & Sandboxing

**Configuration Strategy**:
- `workspace_root` defaults to current working directory (`Path.cwd()`) for immediate usability
- Can be explicitly configured via (in priority order):
  1. Config file: `~/.agent/settings.json` → `agent.workspace_root`
  2. Environment variable: `AGENT_WORKSPACE_ROOT`
  3. Default fallback: Current working directory
- Workspace location displayed in `agent --check` output for transparency
- Warning logged if workspace is home directory (`~`) or filesystem root (`/`)

**Implementation Helpers** in `FileSystemTools`:

1. **`_get_workspace_root() -> Path`**
   - Priority order: config.workspace_root > AGENT_WORKSPACE_ROOT env var > Path.cwd()
   - Return `Path(workspace_root).resolve()` to normalize the root
   - Log warning if workspace is home directory or filesystem root (risky locations)
   - Cache the resolved path for performance

2. **`_resolve_path(relative_path: str) -> Path`**
   - Get workspace_root from _get_workspace_root() (always returns a Path)
   - Reject absolute paths that don't start with workspace_root
   - Reject paths containing `..` components (before resolution)
   - Combine `workspace_root / relative_path` and call `.resolve()` to resolve symlinks
   - Verify resolved path is under `workspace_root` using `.is_relative_to()` (Python 3.9+)
   - If symlink target escapes workspace, raise `symlink_outside_workspace`
   - Return validated, resolved `Path` object

3. **Security Checks**:
   - All tools MUST call `_resolve_path()` before any filesystem access
   - Never construct paths directly from user input
   - Log all path resolution attempts for audit trails
   - Document workspace boundary in error messages

**Example**:
```python
# Config: workspace_root = "/home/user/project"
# User input: "src/main.py"
# Result: Path("/home/user/project/src/main.py").resolve()

# User input: "../etc/passwd"
# Result: Error "path_traversal_attempt"

# User input: "/etc/passwd"
# Result: Error "path_outside_workspace"
```

### Tool API Surface

#### `get_path_info`

**Purpose**: Query metadata about a path without reading contents. Safe, read-only operation.

- **Inputs**:
  - `path: str` (relative to workspace root, default `"."`)
- **Behavior**:
  - Resolve `path` under workspace
  - Check if path exists and gather metadata
  - No file reading or directory listing
- **Result**:
  ```python
  {
    "exists": bool,
    "type": "file" | "directory" | "symlink" | "other" | None,
    "size": int | None,  # bytes, only for files
    "modified": float | None,  # Unix timestamp
    "is_readable": bool,
    "is_writable": bool,
    "absolute_path": str  # resolved path (for debugging)
  }
  ```
- **Error Codes**: `path_outside_workspace`, `permission_denied`

#### `list_directory`

- Inputs:  
  - `path: str` (relative to workspace root, default `"."`)  
  - `recursive: bool = False`  
  - `max_entries: int` (e.g., default 200, upper bound 500)  
  - `include_hidden: bool = False`
- Behavior:  
  - Resolve `path` as a directory under workspace.  
  - List entries with basic metadata:  
    - `name`  
    - `relative_path` (from workspace root)  
    - `type` (`"file"` or `"dir"`)  
    - `size` (for files, best-effort)  
  - If `recursive` is true, walk subdirectories until `max_entries` is reached.
- Result:  
  - `{"entries": [...], "truncated": bool}`

#### `read_file`

**Purpose**: Read text file contents by line range, with chunking for large files.

- **Inputs**:
  - `path: str` (relative to workspace root)
  - `start_line: int = 1` (1-based line number)
  - `max_lines: int = 200` (cap at 1000 for safety)
- **Behavior**:
  - Resolve path and ensure it's a regular file
  - Detect if file is binary (heuristic: check for null bytes in first 8KB)
  - Return `is_binary` error if binary file detected
  - Open using UTF-8 with `errors="replace"` to handle encoding issues gracefully
  - Read up to `max_lines` starting at `start_line`
  - Track total line count if file is reasonably sized (<10MB)
  - Provide pagination metadata for LLM navigation
- **Result**:
  ```python
  {
    "path": str,
    "start_line": int,          # actual start (may differ if requested beyond EOF)
    "end_line": int,             # last line number returned
    "total_lines": int | None,   # total lines in file, None if too large
    "truncated": bool,           # more lines available after end_line
    "next_start_line": int | None,  # hint for next read_file call
    "content": str,              # the actual file lines
    "encoding_errors": bool      # true if errors="replace" was used
  }
  ```
- **Error Codes**: `path_outside_workspace`, `not_found`, `not_a_file`, `is_binary`, `file_too_large`, `line_out_of_range`, `permission_denied`

#### `search_text`

**Purpose**: Search for text patterns across files. Supports literal string or regex matching.

- **Inputs**:
  - `query: str` (search pattern)
  - `path: str = "."` (directory or file to search in)
  - `glob: str = "**/*"` (file match pattern, e.g., "*.py", "src/**/*.ts")
  - `max_matches: int = 50` (limit total matches returned)
  - `use_regex: bool = False` (enable regex mode, default is literal string search)
  - `case_sensitive: bool = True`
- **Behavior**:
  - Resolve `path` under workspace
  - If directory, recursively iterate files matching `glob` pattern
  - If file, search only that file
  - Skip binary files automatically (check for null bytes)
  - For each file:
    - Open with UTF-8, `errors="replace"`
    - Search line-by-line for `query`
    - **Literal mode (default)**: Use `in` operator (safe, fast)
    - **Regex mode**: Compile pattern, match with timeout protection (1s per file)
    - Collect matches with file path, line number, line snippet
  - Stop when `max_matches` is reached
- **Result**:
  ```python
  {
    "query": str,
    "use_regex": bool,
    "files_searched": int,
    "matches": [
      {
        "file": str,           # relative path
        "line": int,           # line number (1-based)
        "snippet": str,        # matched line, trimmed to 200 chars
        "match_start": int,    # char offset in line where match starts
        "match_end": int       # char offset where match ends
      }
    ],
    "truncated": bool  # true if more matches exist beyond max_matches
  }
  ```
- **Error Codes**: `path_outside_workspace`, `not_found`, `invalid_regex`, `regex_timeout`, `permission_denied`
- **Safety Notes**:
  - Regex mode is opt-in due to catastrophic backtracking risks
  - Regex compilation is validated before searching
  - Per-file timeout prevents infinite loops
  - Results are truncated to prevent memory exhaustion

### Guarded Write & Edit Operations

#### `write_file`

- Inputs:  
  - `path: str`  
  - `content: str`  
  - `mode: str = "create"` (`"create"`, `"overwrite"`, `"append"`)
- Behavior:  
  - Check `filesystem_writes_enabled` in config; return `writes_disabled` if false.  
  - Enforce `filesystem_max_write_bytes` limit if configured.  
  - Resolve path under workspace root.  
  - Implement mode semantics:  
    - `create`: error if file exists.  
    - `overwrite`: error if file does not exist (or optionally create).  
    - `append`: append to existing or create new.
- Result:  
  - `{"path": str, "bytes_written": int, "mode": str, "existed_before": bool}`

#### `apply_text_edit`

**Purpose**: Surgical text replacement with safety guardrails. Similar to Claude Code's Edit tool.

- **Inputs**:
  - `path: str` (relative to workspace root)
  - `expected_text: str` (exact text to find and replace, must be non-empty)
  - `replacement_text: str` (replacement content, can be empty for deletion)
  - `replace_all: bool = False` (replace all occurrences instead of requiring exactly one)
- **Behavior**:
  - Check `filesystem_writes_enabled` in config; return `writes_disabled` if false
  - Enforce `filesystem_max_write_bytes` limit if configured
  - Resolve path under workspace and ensure it's a regular text file
  - Read entire file contents as UTF-8 text (with `errors="replace"`)
  - Check if file size after replacement would exceed limits
  - Count occurrences of `expected_text`:
    - If 0: return `match_not_found` error
    - If >1 and `replace_all=False`: return `multiple_matches` error (ambiguous)
    - If >1 and `replace_all=True`: replace all occurrences
    - If exactly 1: replace it
  - Write updated content atomically (write to temp file, then rename)
  - Return statistics about the operation
- **Result**:
  ```python
  {
    "path": str,
    "bytes_written": int,
    "replacements": int,          # number of occurrences replaced
    "original_size": int,         # bytes before edit
    "new_size": int,              # bytes after edit
    "lines_changed": int          # number of lines affected
  }
  ```
- **Error Codes**: `path_outside_workspace`, `writes_disabled`, `not_found`, `not_a_file`, `is_binary`, `write_too_large`, `match_not_found`, `multiple_matches`, `empty_expected_text`, `permission_denied`
- **Safety Notes**:
  - Requires exact match of `expected_text` - no fuzzy matching or whitespace normalization
  - Atomic write ensures file is never left in corrupt state
  - Size limits prevent accidental file bloat
  - `replace_all=False` by default prevents unintended changes

#### `create_directory`

**Purpose**: Create directories for organizing agent-generated outputs.

- **Inputs**:
  - `path: str` (relative to workspace root)
  - `parents: bool = True` (create parent directories if needed, like `mkdir -p`)
- **Behavior**:
  - Check `filesystem_writes_enabled` in config; return `writes_disabled` if false
  - Resolve path under workspace
  - If directory already exists, return success (idempotent)
  - Create directory (and parents if `parents=True`)
- **Result**:
  ```python
  {
    "path": str,
    "created": bool,              # false if already existed
    "parents_created": int        # number of parent dirs created
  }
  ```
- **Error Codes**: `path_outside_workspace`, `writes_disabled`, `permission_denied`, `not_a_directory` (if path exists but is a file)

### Observability & Events

**Automatic Instrumentation via Middleware**:
- `logging_function_middleware` automatically instruments all filesystem tools:
  - Emits `ToolStartEvent` when tool begins execution
  - Emits `ToolCompleteEvent` or `ToolErrorEvent` when finished
  - Records OpenTelemetry spans when `ENABLE_OTEL=true`
  - Logs to configured logger with structured context
- No custom observability code needed in FileSystemTools

**What Gets Logged/Traced**:
- ✅ **DO log**: Tool name, path arguments, operation type, metadata (size, line counts)
- ✅ **DO log**: Error codes and messages
- ✅ **DO log**: Performance metrics (bytes read/written, files searched, matches found)
- ❌ **DO NOT log**: Full file contents (privacy + performance concern)
- ❌ **DO NOT log**: Full search query results (only count + first 100 chars sample)
- ❌ **DO NOT log**: File contents from edit operations (only statistics)

**Span Attributes** (OpenTelemetry):
```python
{
  "tool.name": "read_file",
  "tool.path": "src/agent/agent.py",
  "tool.start_line": 1,
  "tool.lines_read": 200,
  "tool.truncated": true,
  "tool.bytes_read": 8192,
  "tool.duration_ms": 15
}
```

**Privacy Considerations**:
- Workspace root is logged but can be redacted via OTEL configuration
- File paths within workspace are logged (necessary for debugging)
- Sensitive file contents (secrets, API keys) never logged
- Search queries truncated to 100 chars in logs

## Testing Strategy

### Unit Test Coverage (Following ADR-0008)

**Test Organization**: `tests/unit/tools/test_filesystem_tools.py`

**Testing Approach**:
- Use `pytest.fixture` with `tmp_path` for isolated temporary directories
- Each test gets its own workspace_root
- No real file dependencies, all self-contained
- Target: 90%+ coverage for FileSystemTools

**Note on Test Detail Level**: The specific test names below serve as an implementation checklist to ensure comprehensive coverage. During implementation, these can be:
- Used as-is for test function names
- Moved to a comment block or checklist in the test file
- Adjusted based on actual implementation patterns discovered

The categories and coverage areas are the critical specification; exact test names are guidance.

**Test Categories**:

1. **Workspace Sandboxing** (Critical Security Tests):
   - ✅ `test_workspace_defaults_to_cwd` - Workspace defaults to current directory when not configured
   - ✅ `test_workspace_priority` - Verify priority: config > env > cwd
   - ✅ `test_workspace_home_warning` - Warning logged when workspace is home directory or root
   - ✅ `test_path_traversal_blocked` - Reject `../` in paths
   - ✅ `test_absolute_path_outside_workspace` - Reject `/etc/passwd`
   - ✅ `test_symlink_escape_blocked` - Symlink pointing outside workspace blocked
   - ✅ `test_symlink_within_workspace_ok` - Symlink within workspace allowed

2. **Cross-Platform Compatibility**:
   - ✅ `test_windows_path_separators` - Handle backslash on Windows
   - ✅ `test_unicode_filenames` - Create and read files with emoji, Chinese chars
   - ✅ `test_spaces_in_paths` - Handle "My Documents/test file.txt"
   - ✅ `test_case_sensitivity` - Platform-appropriate behavior (case-insensitive on macOS/Windows)

3. **get_path_info**:
   - ✅ `test_path_info_file` - Correct metadata for regular file
   - ✅ `test_path_info_directory` - Correct metadata for directory
   - ✅ `test_path_info_nonexistent` - exists=False for missing path
   - ✅ `test_path_info_symlink` - Detect and resolve symlinks

4. **list_directory**:
   - ✅ `test_list_directory_simple` - Basic listing with files and dirs
   - ✅ `test_list_directory_recursive` - Walk subdirectories
   - ✅ `test_list_directory_hidden_files` - Include/exclude dotfiles
   - ✅ `test_list_directory_max_entries` - Truncation at limit
   - ✅ `test_list_directory_empty` - Empty directory returns empty list
   - ✅ `test_list_directory_not_a_directory` - Error when path is file

5. **read_file**:
   - ✅ `test_read_file_complete` - Small file read entirely
   - ✅ `test_read_file_chunked` - Pagination with start_line and max_lines
   - ✅ `test_read_file_utf8_with_emoji` - UTF-8 encoding handling
   - ✅ `test_read_file_binary_rejected` - Binary file returns is_binary error
   - ✅ `test_read_file_encoding_errors` - Malformed UTF-8 uses errors="replace"
   - ✅ `test_read_file_empty` - Empty file returns 0 lines
   - ✅ `test_read_file_no_newline_at_end` - Handle files without trailing newline
   - ✅ `test_read_file_line_out_of_range` - start_line beyond EOF

6. **search_text**:
   - ✅ `test_search_text_literal` - Simple substring search
   - ✅ `test_search_text_case_insensitive` - Case-insensitive search
   - ✅ `test_search_text_regex_simple` - Basic regex pattern
   - ✅ `test_search_text_regex_invalid` - Malformed regex returns error
   - ✅ `test_search_text_glob_filter` - Search only *.py files
   - ✅ `test_search_text_max_matches` - Truncation at limit
   - ✅ `test_search_text_binary_files_skipped` - Auto-skip binary files
   - ✅ `test_search_text_no_matches` - Empty results when no matches

7. **write_file**:
   - ✅ `test_write_file_disabled` - Returns writes_disabled when config disabled
   - ✅ `test_write_file_mode_create` - Creates new file (writes enabled)
   - ✅ `test_write_file_mode_overwrite` - Overwrites existing (writes enabled)
   - ✅ `test_write_file_mode_append` - Appends to existing (writes enabled)
   - ✅ `test_write_file_file_exists` - Error on create when file exists
   - ✅ `test_write_file_size_limit` - Enforce max_write_bytes

8. **apply_text_edit**:
   - ✅ `test_apply_text_edit_disabled` - Returns writes_disabled when config disabled
   - ✅ `test_apply_text_edit_single_match` - Replace exactly one occurrence (writes enabled)
   - ✅ `test_apply_text_edit_multiple_matches_error` - Error when ambiguous
   - ✅ `test_apply_text_edit_replace_all` - Replace all occurrences (writes enabled)
   - ✅ `test_apply_text_edit_match_not_found` - Error when text not found
   - ✅ `test_apply_text_edit_empty_expected` - Error when expected_text empty
   - ✅ `test_apply_text_edit_multiline` - Handle multi-line replacements
   - ✅ `test_apply_text_edit_whitespace_exact` - No fuzzy whitespace matching

9. **create_directory**:
   - ✅ `test_create_directory_disabled` - Returns writes_disabled when config disabled
   - ✅ `test_create_directory_simple` - Create single directory (writes enabled)
   - ✅ `test_create_directory_parents` - Create nested structure (writes enabled)
   - ✅ `test_create_directory_idempotent` - Already exists is success
   - ✅ `test_create_directory_file_exists` - Error when path is file

10. **Error Handling**:
    - ✅ `test_permission_denied` - Handle OS permission errors
    - ✅ `test_file_too_large` - Reject files over configured limit
    - ✅ All error codes return structured error responses

11. **Edge Cases**:
    - ✅ `test_very_long_path` - Handle paths near OS limits (255 chars)
    - ✅ `test_special_characters` - Handle `$`, `#`, `@` in filenames
    - ✅ `test_concurrent_access` - Multiple tools accessing same file

### Integration Testing

**Test File**: `tests/integration/test_filesystem_integration.py`

- Test FileSystemTools with real Agent instance (mock chat client)
- Verify event emission (ToolStart/ToolComplete events)
- Verify middleware instrumentation (logging, OTEL spans)
- Test with different configurations (writes enabled/disabled)

### Validation Testing (Optional)

**Test File**: `tests/validation/test_filesystem_validation.py`

- CLI subprocess tests: `agent -p "list my project files"`
- Verify agent can use tools in conversation
- Ensure display system renders tool results correctly

## Relevant Files

### New Files

- `src/agent/tools/filesystem.py`  
  - Defines `FileSystemTools` implementing `list_directory`, `read_file`, `search_text`, `write_file`, `apply_text_edit`.
- `tests/unit/tools/test_filesystem_tools.py`  
  - Unit tests for filesystem tools using temporary directories.
- `docs/specs/filesystem-tools.md`  
  - This specification document.

### Existing Files to Modify

- `src/agent/agent.py`  
  - Update default toolset construction to include `FileSystemTools` alongside `HelloTools`.
- `src/agent/config/schema.py` & `src/agent/config/legacy.py`  
  - Add configuration fields for workspace root and filesystem write settings.
- `src/agent/config/manager.py`  
  - Ensure new config fields are persisted/validated.
- `README.md` / `docs/design/usage.md`  
  - Document new capabilities (high-level).
- `docs/specs/validation-strategy.md`  
  - Optionally extend validation strategy to include filesystem behaviors.

## Implementation Plan

### Phase 1: Core Infrastructure & Read-Only Tools

**Goal**: Establish workspace sandboxing and safe read-only filesystem access.

**Estimated Effort**: 8-12 hours

1. **Configuration Schema** (1-2 hours)
   - Add fields to `src/agent/config/schema.py`:
     - `workspace_root: Path | None = None`
     - `filesystem_writes_enabled: bool = False`
     - `filesystem_max_read_bytes: int = 10_485_760` (10MB default)
     - `filesystem_max_write_bytes: int = 1_048_576` (1MB default)
   - Update `AgentConfig.from_combined()` to load from env vars
   - Add validation in config schema

2. **FileSystemTools Foundation** (3-4 hours)
   - Create `src/agent/tools/filesystem.py`
   - Implement `_get_workspace_root()` with env var and config support
   - Implement `_resolve_path()` with all security checks:
     - Path traversal detection
     - Symlink resolution and boundary checking
     - Absolute path validation
   - Add comprehensive docstrings and type hints

3. **Read-Only Tools Implementation** (4-6 hours)
   - Implement `get_path_info()` - metadata queries
   - Implement `list_directory()` - directory listing with recursion
   - Implement `read_file()` - chunked text file reading with UTF-8 handling
   - Implement `search_text()` - literal and regex search
   - All tools return structured responses with metadata

4. **Unit Tests - Security & Read-Only** (4-5 hours)
   - Create `tests/unit/tools/test_filesystem_tools.py`
   - Implement all security/sandboxing tests (11 tests)
   - Implement cross-platform tests (4 tests)
   - Implement read-only tool tests (~30 tests)
   - Target: 90%+ coverage on implemented code

5. **Agent Integration** (30 minutes)
   - Update `src/agent/agent.py` to register `FileSystemTools`
   - Make it opt-in initially (don't add by default until Phase 3)
   - Document how to enable in docstring

**Deliverable**: Working read-only filesystem tools with comprehensive security testing

---

### Phase 2: Write Operations & Advanced Features

**Goal**: Add guarded write operations behind configuration gates.

**Estimated Effort**: 6-8 hours

1. **Write Tools Implementation** (4-5 hours)
   - Implement `write_file()` with modes (create, overwrite, append)
   - Implement `apply_text_edit()` with expected_text matching
   - Implement `create_directory()` with parents support
   - Add size limit enforcement
   - Implement atomic write operations (temp file + rename)
   - Add comprehensive error handling

2. **Unit Tests - Write Operations** (3-4 hours)
   - Extend `test_filesystem_tools.py` with write tests (~25 tests)
   - Test writes_disabled enforcement
   - Test all write modes and error conditions
   - Test apply_text_edit with all edge cases
   - Test size limit enforcement
   - Verify atomic writes (no corruption on failure)

3. **Configuration Validation** (1 hour)
   - Add health check warnings when workspace_root not configured
   - Document configuration in `agent --check` output
   - Add helpful error messages for common misconfigurations

**Deliverable**: Full-featured filesystem toolset with write safety guarantees

---

### Phase 3: Integration, Documentation & Polish

**Goal**: Production-ready feature with complete documentation and integration testing.

**Estimated Effort**: 4-6 hours

1. **Integration Testing** (2-3 hours)
   - Create `tests/integration/test_filesystem_integration.py`
   - Test with real Agent instance (mock chat client)
   - Verify event emission and middleware instrumentation
   - Test observability (logging, OTEL spans)
   - Test different configuration scenarios

2. **Documentation Updates** (2-3 hours)
   - Update `README.md`: Add filesystem tools to capabilities list
   - Update `docs/design/usage.md`: Add examples of using filesystem tools
   - Create usage examples: "list project files", "search for TODO comments", "edit a file"
   - Document configuration requirements and best practices
   - Add security guidance (workspace boundaries, write permissions)

3. **Enable by Default** (30 minutes)
   - Update `Agent.__init__` to include `FileSystemTools` in default toolsets
   - Ensure it gracefully handles unconfigured workspace_root
   - Update documentation to reflect default availability

4. **Optional: Validation Tests** (1-2 hours)
   - Create `tests/validation/test_filesystem_validation.py`
   - CLI subprocess tests: agent using filesystem tools in conversation
   - Verify display rendering of tool results
   - Test error handling in interactive mode

**Deliverable**: Production-ready filesystem tools, fully integrated and documented

---

### Future Enhancements (Post-Launch)

Not included in initial implementation:

- **File Operations**: `move_file`, `copy_file`, `delete_file`, `delete_directory`
- **Advanced Search**: Full-text indexing, fuzzy search, syntax-aware search
- **Binary File Support**: `read_file_bytes`, `write_file_bytes` with MIME type detection
- **Diff Support**: `get_file_diff` comparing two files or versions
- **Watch Operations**: File change notifications for reactive agents
- **Compression**: Read/write from archives (zip, tar, etc.)

These can be added in future phases based on user needs.

---

## Summary

This specification defines a comprehensive, production-ready filesystem toolset for Agent Base that:

**✅ Maintains Safety**:
- Required workspace_root configuration prevents accidental system access
- Path traversal protection blocks `../` and symlink escapes
- Write operations disabled by default, behind explicit configuration
- Size limits prevent resource exhaustion
- Binary file detection protects against invalid text operations

**✅ Follows Agent Base Patterns**:
- Inherits from `AgentToolset` with dependency injection
- Returns structured `{success, result|error, message}` responses
- Leverages middleware for automatic observability (logging, events, OTEL)
- Integrates with event bus for display visualization
- Comprehensive error codes for predictable behavior

**✅ Enables Real Agent Capabilities**:
- **Inspection**: List directories, read files, query metadata, search patterns
- **Modification**: Write files, apply surgical edits, create directories
- **Intelligent**: Chunked reading for large files, regex search, UTF-8 handling
- **Cross-platform**: Works on macOS, Linux, Windows via pathlib

**✅ Production-Ready Quality**:
- 90%+ test coverage target with 70+ unit tests
- Security tests for all sandboxing mechanisms
- Cross-platform compatibility tests
- Integration tests for observability
- Comprehensive documentation and examples

**Total Implementation Effort**: 18-26 hours across 3 phases

This feature transforms Agent Base from a "hello world" template into a practical foundation for building coding agents, documentation agents, file management agents, and other specialized agents that need structured, safe filesystem access.

