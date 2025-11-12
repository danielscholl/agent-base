# Feature

Progressive Disclosure Skill Architecture

# Feature Description

This feature introduces a plugin system that enables agent-base to support domain-specific capabilities through git-based skill packages. Users can selectively install, update, and compose specialized capability packages (skills) from git repositories, transforming agent-base from a foundational framework into a platform for specialized agents.

Skills are self-contained packages combining:
- **Structured Python Toolsets**: Testable, type-safe tool classes inheriting from AgentToolset for frequently-used operations
- **Context-Efficient Scripts**: Standalone PEP 723 scripts for context-heavy or rarely-used operations, accessed via generic wrapper tools (`script_help` and `script_run`)
- **Metadata and Manifests**: SKILL.md manifest with YAML front matter defining skill identity, description, and optional metadata

This hybrid approach balances developer experience (structured, testable code) with LLM efficiency (minimal context window consumption), maintaining <5K token overhead even with multiple skills loaded.

## Script Wrapper Contract

**Critical Design Decision**: Scripts are NOT registered as individual tools with static schemas (since PEP 723 scripts lack type info). Instead, two generic wrapper tools provide progressive disclosure:

```python
async def script_list(skill_name: str | None = None) -> dict:
    """List available scripts for a skill or all skills.

    Returns script metadata programmatically without reading SKILL.md.
    """
    # Returns: {
    #   "success": True,
    #   "result": {
    #     "kalshi-markets": [
    #       {"name": "status", "path": "/path/to/status.py"},
    #       {"name": "markets", "path": "/path/to/markets.py"}, ...
    #     ], ...
    #   },
    #   "message": "Found 15 scripts across 2 skills"
    # }

async def script_help(skill_name: str, script_name: str) -> dict:
    """Get help for a skill script by running --help.

    Use this to discover what arguments and options are available before running the script.
    """
    # Executes: uv run <skill_path>/scripts/<script_name>.py --help
    # (shell=False, args as list, timeout=60s, read stdout/stderr as UTF-8)
    # Returns: {"success": True, "result": {"help_text": "...", "usage": "..."}, "message": "Retrieved help for status"}
    # On error: {"success": False, "error": "not_found|timeout|execution_failed", "message": "..."}

async def script_run(skill_name: str, script_name: str, args: list[str] | None = None, json: bool = True) -> dict:
    """Execute a skill script with arguments.

    Most scripts support --json for structured output. Check --help first to see available options.
    """
    # Validate: max 100 args or 4KB total length
    # Normalize: args=None → [], skill_name/script_name → canonical form
    # Executes: uv run <skill_path>/scripts/<script_name>.py <args> [--json]
    # (shell=False, timeout=60s, max_output=1MB, cwd=script_parent, read as UTF-8)
    # When json=True: Parse stdout as JSON, treat non-JSON as parse_error (include stderr tail in message)
    # Returns: {"success": True, "result": {...parsed JSON...}, "message": "Executed status script"}
    # On error: {"success": False, "error": "not_found|invalid_name|timeout|parse_error|execution_failed|args_too_large", "message": "Script timed out after 60s\nstderr: <last 500 bytes>"}
```

**Benefits**:
- Preserves progressive disclosure (script code never loaded)
- No need to guess script parameters at registration time
- LLM can discover available scripts via `script_list`, then call `script_help`, then `script_run`
- Works with any PEP 723 script that follows conventions
- Consistent response format (success, result, message) with AgentToolset standard

**Script Conventions**:
- Scripts must support `--help` flag (output usage information)
- Scripts should support `--json` flag for structured output
- When `--json` is set: Emit ONLY valid JSON to stdout (no banners, logs, or extra text)
- Use stderr for logs/warnings (captured separately by wrapper)
- Encoding: Emit UTF-8 to stdout/stderr (wrapper reads as UTF-8)
- Exit code 0 for success, non-zero for errors
- When json=True and stdout is non-JSON: Wrapper returns parse_error with stderr tail

## Reference Implementation

The **kalshi-markets** skill from `ai-examples/beyond-mcp/apps/4_skill/.claude/skills/kalshi-markets/` serves as the reference implementation demonstrating the progressive disclosure pattern:

**Structure**:
```
kalshi-markets/
├── SKILL.md              # Manifest with YAML front matter + instructions
└── scripts/              # 10 standalone PEP 723 scripts (~200-300 lines each)
    ├── status.py
    ├── markets.py
    ├── search.py
    └── ...
```

**Key Patterns**:
- YAML front matter in SKILL.md defines name and description (no activation keywords - simple config-based loading)
- Each script is self-contained with embedded dependencies (httpx, click) via PEP 723
- Progressive disclosure: "Don't read scripts unless needed - use --help first"
- Scripts support both `--json` (for automation) and human-readable output
- Zero external dependencies between scripts

**SKILL.md Manifest Example**:
```yaml
---
name: kalshi-markets
description: Access Kalshi prediction market data including market prices, orderbooks, trades, events, and series information.
version: 1.0.0
author: Example Author
repository: https://github.com/example/kalshi-markets-skill
---

# Kalshi Markets

Instructions for using this skill...

## Available Scripts

### `scripts/status.py`
**When to use:** Check if Kalshi exchange is operational
```

This reference implementation will guide our skill system design, ensuring we support both the standalone script pattern (for context efficiency) and structured Python toolsets (for testability).

# User Story

As a **DevOps engineer or platform engineer**
I want to **install and compose specialized capability packages (skills) for my agent**
So that **I can build domain-specific automation agents without modifying the core agent-base codebase, maintaining a lightweight context window while accessing only the capabilities I need**

# Problem Statement

agent-base currently ships with minimal built-in tools (HelloTools demonstration). Adding domain-specific capabilities like Kubernetes cluster management, Flux deployments, or GitHub DevOps workflows requires forking and modifying the core codebase, creating several challenges:

1. **Context Window Bloat**: Loading all possible tools into every conversation consumes 15K+ tokens before any work begins, severely limiting available context for actual tasks
2. **User Choice Paralysis**: Not every user needs every capability - a developer focused on local Kubernetes doesn't need GitHub workflow tools
3. **Update Distribution Friction**: Adding new capabilities or fixing bugs requires updating the entire agent-base repository, forcing full installation upgrades
4. **Maintenance Burden**: Consolidating all integrations into core creates testing complexity, dependency conflicts, and harder maintenance
5. **Community Contribution Barriers**: Contributors must navigate the entire codebase, meet all core standards, and wait for mainline releases

# Solution Statement

Introduce a skill plugin system with three key components:

1. **Skill Package Structure**: Git repositories with standardized layout (SKILL.md manifest with YAML front matter, toolsets/ for Python classes, scripts/ for standalone operations)
2. **Skill Management CLI**: Commands to install (`agent skill add <git-url>`), update, list, info, and remove skills with explicit trust confirmations
3. **Dynamic Skill Loading**: Load only skills explicitly enabled in AGENT_SKILLS config, keeping base agent lightweight

This architecture supports three deployment patterns:
- **Core Skills**: Bundled in `skills/core/` for universal needs (kalshi-markets as first example)
- **Community Skills**: Installed to `~/.agent/skills/<name>` from git repositories
- **Private Skills**: Developed internally by organizations for proprietary workflows

All using the same plugin interface, enabling progressive disclosure where users start minimal and add capabilities as needs evolve.

## Key Design Decisions

1. **SKILL.md Format**: YAML front matter + markdown instructions in one file (better LLM context)
2. **Activation Model**: Simple - only load skills listed in AGENT_SKILLS env var (no smart keyword matching - avoids complexity)
3. **Script Wrapper Tools**: Generic `script_help` and `script_run` functions instead of per-script tool registration (preserves progressive disclosure)
4. **Trust Model**: Explicit confirmation for untrusted skills, pin to commit SHA by default, validate manifest before installation completes

# Manifest Schema

## Required Fields

```yaml
---
name: kalshi-markets              # alphanumeric + hyphens, max 64 chars
description: Access Kalshi prediction market data including prices, orderbooks, and trades.  # max 500 chars
---
```

## Optional Fields

```yaml
version: 1.0.0                    # semver format
author: Example Author
repository: https://github.com/example/kalshi-markets-skill
license: MIT
min_agent_base_version: 0.1.0     # Minimum agent-base version required
max_agent_base_version: 1.0.0     # Maximum agent-base version (forward-incompatibility signaling)
toolsets:                         # Python toolset classes to load (module:Class format)
  - toolsets.hello:HelloExtended
  - toolsets.utils:HelperTools
scripts:                          # Auto-discovered from scripts/ if omitted; accepts both "status" and "status.py"
  - status
  - markets
  - search
scripts_ignore:                   # Glob patterns to exclude from auto-discovery
  - "*_test.py"
  - "_*.py"
  - "*.bak"
  - "*.tmp"
permissions:                      # Environment variables allowed in script execution (Phase 2)
  env:
    - KALSHI_API_KEY
    - KALSHI_*                    # Wildcard patterns supported
```

**File Encoding**: SKILL.md must be UTF-8 encoded, no BOM. YAML front matter delimited by `---` lines.

**Scripts Discovery**:
- Scan for `*.py` files in scripts/ directory
- Exclude patterns from scripts_ignore
- Exclude non-files (directories, `.` files)
- Symbolic links: **Rejected** for security (prevent escaping skill directory)

## Path Sanitization and Name Normalization

**Skill Names**:
- Allowed: alphanumeric + hyphens/underscores (`^[a-zA-Z0-9_-]{1,64}$`)
- Canonical form: lowercase, hyphens normalized (underscores → hyphens)
- Matching: case-insensitive ("Kalshi-Markets" == "kalshi-markets" == "kalshi_markets")
- Rejected: `../`, absolute paths, spaces, special chars
- Rejected reserved: `.`, `..`, `~`, `__pycache__`
- Max 64 characters

**Script Names**:
- Accepted: "status", "status.py" → both map to "status.py"
- Canonical form: lowercase, .py extension
- Discovery: Scan for `*.py` files in scripts/, exclude patterns from scripts_ignore
- Matching: case-insensitive ("Status.py" == "status.py" == "status")

# Registry Schema

```python
@dataclass
class SkillRegistryEntry:
    name: str                    # Display name (original case)
    name_canonical: str          # Normalized for matching (lowercase, hyphens)
    git_url: str | None          # None for bundled/local skills
    commit_sha: str | None       # Pinned commit for reproducibility
    branch: str | None           # e.g., "main"
    tag: str | None              # e.g., "v1.0.0"
    installed_path: Path         # ~/.agent/skills/kalshi-markets or skills/core/kalshi-markets
    trusted: bool                # User explicitly approved (bundled=True, git requires confirmation)
    installed_at: datetime       # Installation timestamp
```

**Persistence**: `~/.agent/skills/registry.json`
- Atomic writes via temp file + os.replace() prevent torn files (file corruption)
- **Concurrency**: Last-writer-wins on concurrent modifications (acceptable for Phase 1)
- **Phase 2**: Add simple file lock (lockfile) for multi-process safety if needed
- Cross-platform safe via os.replace()

**Activation Semantics**:
- `AGENT_SKILLS` env var controls what's loaded at runtime
- `AGENT_SKILLS=kalshi-markets,hello-extended` → load these two (case-insensitive, if trusted or bundled)
- `AGENT_SKILLS=all` → load all **trusted** skills only (bundled skills + user-approved git installs)
- `AGENT_SKILLS=all-untrusted` → load all skills including untrusted (advanced users, Phase 2)
- `AGENT_SKILLS=none` or empty → load no skills
- Matching is case-insensitive: "Kalshi-Markets" == "kalshi_markets" (via name_canonical)

# Relevant Files

## Existing Files to Modify

- **src/agent/config.py** - Add skill configuration support (AGENT_SKILLS env variable, skill directory paths)
- **src/agent/agent.py** - Modify toolset initialization to load skills dynamically from configured paths (~line 90)
- **src/agent/cli/app.py** - Add skill management subcommands (skill add, list, info, update, remove)
- **pyproject.toml** - Add skill-related dependencies (GitPython, PyYAML for git operations and YAML parsing)
- **README.md** - Add documentation about skill system and usage examples

## New Files

### Phase 1: Foundation

- **src/agent/skills/__init__.py** - Skill subsystem package initializer
- **src/agent/skills/loader.py** - Core skill loading logic (scan directories, parse SKILL.md, instantiate toolsets)
- **src/agent/skills/manager.py** - Skill lifecycle management (install, update, remove from git repositories)
- **src/agent/skills/registry.py** - Skill registry and metadata management with SHA tracking
- **src/agent/skills/manifest.py** - SKILL.md schema validation and parsing (Pydantic models for YAML front matter)
- **src/agent/skills/errors.py** - Skill-specific exception classes
- **src/agent/skills/script_tools.py** - Generic wrapper tools: script_help() and script_run() for executing PEP 723 scripts
- **src/agent/skills/security.py** - Trust validation, SHA pinning, confirmation prompts, path sanitization

### Phase 2: CLI & Testing

- **src/agent/cli/skill_commands.py** - Skill CLI command implementations
- **tests/unit/skills/test_loader.py** - Unit tests for skill loader
- **tests/unit/skills/test_manager.py** - Unit tests for skill manager
- **tests/unit/skills/test_manifest.py** - Unit tests for manifest parsing
- **tests/unit/skills/test_script_tools.py** - Unit tests for script wrapper tools
- **tests/unit/skills/test_security.py** - Unit tests for security validation
- **tests/integration/skills/test_skill_lifecycle.py** - Integration tests for full skill workflow

### Phase 3: Example Skills

- **skills/core/kalshi-markets/SKILL.md** - Adapted kalshi-markets skill manifest (from reference implementation)
- **skills/core/kalshi-markets/scripts/*.py** - Adapted scripts from reference implementation
- **skills/core/hello-extended/SKILL.md** - Simple extended hello skill manifest
- **skills/core/hello-extended/toolsets/hello.py** - Extended hello toolset (demonstrates Python toolset pattern)
- **skills/core/hello-extended/scripts/advanced_greeting.py** - Standalone script example (demonstrates script pattern)
- **.env.example** - Environment configuration template with AGENT_SKILLS examples

# Implementation Plan

## Phase 1: Foundation (MVP)

**Goal**: Establish core skill infrastructure - manifest schema, loading mechanism, script wrapper tools, and security validation.

**Key Deliverables**:
- Skill manifest schema (SKILL.md with YAML front matter) with Pydantic models
- Skill loader that scans directories, parses SKILL.md, discovers scripts, and instantiates toolsets
- Script wrapper tools (`script_help`, `script_run`) as generic AgentToolset
- Registry with JSON persistence and full tracking (SHA, trust, timestamps)
- Security validation (path sanitization, trust model)
- Configuration integration in AgentConfig
- Updated Agent class to load skills dynamically
- Manual skill installation (copy to skills/core/ for testing)
- agent --check shows loaded skills

**Success Criteria**:
- Can define a skill with SKILL.md manifest (YAML front matter + markdown instructions)
- Can load skill toolsets from a directory
- Can execute standalone scripts via wrapper tools
- Skills integrate with existing AgentToolset pattern
- Configuration supports AGENT_SKILLS environment variable ("kalshi-markets,hello-extended", "all", "none")
- Path sanitization prevents directory traversal
- Registry tracks all installed skills with metadata

**Included in Phase 1** (Basic Versions):
- Script execution timeouts: Hard 60s timeout, return error on timeout
- Max output size: Hard 1MB limit on stdout, truncate with warning
- Max args: 100 arguments or 4KB total length (prevent abuse)
- Working directory: Set to script's parent directory
- Subprocess safety: shell=False, args as list (no shell injection)
- Stderr capture: Always captured, included in error messages only (truncated to 500 bytes)
- Encoding: Read stdout/stderr as UTF-8 (scripts must emit UTF-8)
- Error handling: Structured error responses (not exceptions)

**Deferred to Phase 2** (Advanced Versions):
- Git operations (install/update/remove via CLI)
- Full CLI commands with interactive confirmations
- Env var allowlist (permissions.env from SKILL.md)
- Per-skill timeout/output overrides
- Nicer stderr formatting in errors (syntax highlighting, context)
- script_help result caching (short TTL, per-process)

## Phase 2: Core Implementation

**Goal**: Implement CLI commands for skill management with git operations, trust confirmations, and comprehensive testing.

**Key Deliverables**:
- CLI commands: `agent skill add`, `list`, `info`, `update`, `remove`
- Git operations with SHA pinning (using GitPython)
- Trust confirmations for untrusted sources
- Script execution safety (timeouts, output limits, env var allowlist)
- Complete unit test coverage for skill subsystem
- Integration tests for skill lifecycle
- Error handling and validation
- Enhanced `agent --check` output

**Success Criteria**:
- Users can install skills from git URLs with explicit confirmation
- Users can list installed skills with metadata (name, version, enabled, SHA)
- Users can view detailed skill info (scripts, toolsets, manifest)
- Users can update skills with SHA comparison and confirmation
- Users can remove skills with cleanup verification
- All components have >80% test coverage
- Skills persist across agent restarts
- agent --check shows skill status (enabled, script count, toolset count)

## Phase 3: Integration

**Goal**: Adapt kalshi-markets reference skill, create example skills, update documentation, and validate end-to-end workflows.

**Key Deliverables**:
- Adapt kalshi-markets skill from reference implementation to agent-base format
- Create simple hello-extended skill demonstrating both patterns
- Updated README with skill system documentation
- Skill development guide (docs/SKILLS.md)
- Validation of context efficiency goals (<5K tokens)
- Token overhead measurement

**Success Criteria**:
- kalshi-markets skill works with agent-base skill system (10 scripts accessible via wrapper tools)
- hello-extended skill demonstrates both Python toolsets and standalone scripts
- Documentation enables users to create custom skills
- Context window overhead measured and validated (<5K tokens with 2 skills)
- Zero regressions in existing functionality

# Step by Step Tasks

## 1. Create Skill Subsystem Foundation

- Create `src/agent/skills/` package directory structure
- Implement `src/agent/skills/errors.py` with custom exception classes:
  - `SkillError` (base exception)
  - `SkillNotFoundError`
  - `SkillManifestError`
  - `SkillDependencyError`
  - `SkillSecurityError`
- Create unit tests in `tests/unit/skills/test_errors.py`

## 2. Implement Skill Manifest Schema

- Create `src/agent/skills/manifest.py` with Pydantic models for SKILL.md YAML front matter:
  - `SkillManifest` (root model):
    - `name: str` (required, alphanumeric + hyphens/underscores, max 64 chars)
    - `description: str` (required, max 500 chars)
    - `version: str` (optional, semver format)
    - `author: str` (optional)
    - `repository: str` (optional, git URL)
    - `license: str` (optional)
    - `min_agent_base_version: str` (optional, semver format for compatibility gating)
    - `max_agent_base_version: str` (optional, semver format for forward-incompatibility signaling)
    - `toolsets: list[str]` (optional, "module:Class" format like "toolsets.hello:HelloExtended")
    - `scripts: list[str]` (optional, auto-discovered from scripts/ if omitted)
    - `scripts_ignore: list[str]` (optional, glob patterns to exclude: "*_test.py", "_*.py")
    - `permissions: dict` (optional, {env: [str]} for env var allowlist in Phase 2)
  - `SkillRegistryEntry` (for registry persistence):
    - All fields from registry schema above
- Add YAML front matter extraction and parsing logic:
  - Extract YAML between `---` markers at start of SKILL.md
  - Parse remaining markdown as instructions (store as string)
  - Use PyYAML for parsing (NOT included in Pydantic)
- Create comprehensive unit tests in `tests/unit/skills/test_manifest.py`:
  - Valid SKILL.md parsing (YAML front matter + markdown)
  - Invalid manifest rejection (bad YAML, missing required fields)
  - Missing YAML front matter markers
  - Edge cases (empty descriptions, missing optional fields)
  - Parse kalshi-markets SKILL.md as test case

## 3. Implement Security Validation

- Create `src/agent/skills/security.py` with:
  - `sanitize_skill_name(name: str)` - validate name (alphanumeric + hyphens/underscores, no traversal)
  - `normalize_skill_name(name: str)` - convert to canonical form (lowercase, underscores→hyphens)
  - `normalize_script_name(name: str)` - handle "status" and "status.py" → "status.py"
  - `confirm_untrusted_install(skill_name: str, git_url: str)` - prompt user for confirmation
  - `pin_commit_sha(repo_path: Path)` - get current commit SHA after clone
  - `validate_manifest(manifest_path: Path)` - ensure SKILL.md exists, parses, UTF-8 encoded
- Add unit tests in `tests/unit/skills/test_security.py`:
  - Name sanitization (reject ../, absolute paths, special chars, spaces)
  - Name normalization (case-insensitive, hyphen/underscore equivalence)
  - Script name normalization ("status" == "status.py")
  - Reserved name rejection (., .., ~, __pycache__)
  - Manifest validation (encoding, YAML front matter)

## 4. Implement Skill Registry

- Create `src/agent/skills/registry.py` with:
  - `SkillRegistry` class to track installed skills
  - Methods: `register()`, `unregister()`, `list()`, `get()`, `get_by_canonical_name()`, `update_sha()`
  - Persistence to JSON file in `~/.agent/skills/registry.json`
  - Registry includes: name, name_canonical, git_url, commit_sha, branch, tag, installed_path, trusted, installed_at
  - Atomic writes: Write to temp file, then os.replace() for cross-platform safety (no file locking needed)
  - Stable sorting: Always return skills in alphabetical order by canonical name
- Add unit tests in `tests/unit/skills/test_registry.py`:
  - CRUD operations
  - Case-insensitive lookup (via name_canonical)
  - SHA pinning and updates
  - JSON serialization/deserialization
  - Atomic write simulation (mock os.replace)
  - Stable sorting verification

## 5. Implement Skill Loader

- Create `src/agent/skills/loader.py` with:
  - `SkillLoader` class to discover and load skills
  - `scan_skill_directory()` - find all SKILL.md files in configured directories
  - `load_skill()` - parse SKILL.md manifest and instantiate toolsets (if defined)
  - `discover_scripts()` - scan scripts/ directory for *.py files:
    - Exclude scripts_ignore patterns
    - Exclude non-files (directories, symbolic links for security)
    - Return metadata: list of {"name": str, "path": Path} objects
  - `validate_dependencies()` - check Python dependencies for toolsets only (scripts managed by PEP 723)
  - Dynamic import of toolset classes via importlib.util.spec_from_file_location (no permanent sys.path edits)
  - Parse toolsets as "module:Class" format, import and instantiate
  - On tool name collision: Log warning with fully qualified source (skill_name.toolset_class.tool_name)
  - `load_enabled_skills()` - main entry point that returns (skill_toolsets, script_wrapper_toolset)
  - Handle "all" → load all trusted skills; "all-untrusted" → load all (Phase 2)
  - Warn if AGENT_SKILLS=all and no trusted skills found (Phase 2)
- **Critical**: Scripts are NOT loaded into context, only metadata (name, path) registered
- Add comprehensive unit tests in `tests/unit/skills/test_loader.py`:
  - Loading skills with SKILL.md
  - Loading skills with toolsets
  - Loading skills with scripts only (like kalshi-markets)
  - Script metadata discovery (no code loading)
  - Handling missing manifests
  - Invalid toolset imports
  - Load from both core_skills_dir and user skills_dir

## 6. Implement Script Wrapper Tools

- Create `src/agent/skills/script_tools.py` with `ScriptToolset(AgentToolset)`:
  - Inherits from AgentToolset for consistency
  - Constructor takes skill registry to map skill/script names to paths
  - Implements three generic tools:

    ```python
    async def script_list(
        self,
        skill_name: Annotated[str | None, Field(description="Skill name, or None for all skills")] = None
    ) -> dict:
        """List available scripts for a skill or all skills."""
        # Normalize skill_name if provided
        # Return: {
        #   "success": True,
        #   "result": {
        #     "kalshi-markets": [
        #       {"name": "status", "path": "/path/to/status.py"},
        #       {"name": "markets", "path": "/path/to/markets.py"}
        #     ], ...
        #   },
        #   "message": "Found 15 scripts across 2 skills"
        # }
        # On error: {"success": False, "error": "not_found", "message": "Skill 'xyz' not found"}

    async def script_help(
        self,
        skill_name: Annotated[str, Field(description="Skill name (e.g., 'kalshi-markets')")],
        script_name: Annotated[str, Field(description="Script name (e.g., 'status' or 'status.py')")]
    ) -> dict:
        """Get help information for a skill script by running --help."""
        # Normalize skill_name and script_name (case-insensitive, handle .py extension)
        # Windows fallback: Try 'uv' first, fall back to sys.executable -m uv if not on PATH
        # Run: uv run <skill_path>/scripts/<script_name>.py --help
        # (shell=False, args as list, timeout=60s, read stdout/stderr as UTF-8)
        # Return: {"success": True, "result": {"help_text": "...", "usage": "..."}, "message": "Retrieved help for status"}
        # On error: {"success": False, "error": "not_found|invalid_name|timeout|execution_failed", "message": "...\nstderr: <last 500 bytes>"}

    async def script_run(
        self,
        skill_name: Annotated[str, Field(description="Skill name")],
        script_name: Annotated[str, Field(description="Script name")],
        args: Annotated[list[str] | None, Field(description="Script arguments")] = None,
        json: Annotated[bool, Field(description="Request JSON output")] = True
    ) -> dict:
        """Execute a skill script with arguments."""
        # Validate: max 100 args or 4KB total length → args_too_large error
        # Normalize: skill_name, script_name (case-insensitive), args (None → [])
        # Windows fallback: Try 'uv' first, fall back to sys.executable -m uv if not on PATH
        # Run: uv run <skill_path>/scripts/<script_name>.py <args> [--json]
        # (shell=False, timeout=60s, max_output=1MB, cwd=script_parent, read as UTF-8)
        # When json=True: Parse stdout as JSON, treat non-JSON as parse_error (include stderr tail in message)
        # Return: {"success": True, "result": {...parsed JSON...}, "message": "Executed status script"}
        # Error codes: not_found|invalid_name|args_too_large|timeout|parse_error|execution_failed|permission_denied
        # On error: {"success": False, "error": "<code>", "message": "Script timed out after 60s\nstderr: <last 500 bytes>"}
    ```

  - Add execution safety (Phase 1 - basic):
    - Hard timeout: 60s (TimeoutExpired → structured error)
    - Max output size: 1MB on stdout (truncate with warning if exceeded)
    - Max args: 100 arguments or 4KB total length
    - Working directory: Set to script's parent directory
    - Subprocess: shell=False, args as list (no shell injection)
    - Encoding: Read stdout/stderr as UTF-8
    - Capture stdout and stderr separately (stderr only in errors, truncated to 500 bytes)
    - Windows fallback: Try 'uv' first, fall back to sys.executable -m uv if not on PATH
    - Return structured errors, not exceptions
  - Store script metadata: `self.scripts = {skill_name: [{"name": str, "path": Path}, ...]}`
  - Add `script_count` property for logging
  - Error codes: not_found, invalid_name, args_too_large, timeout, parse_error, execution_failed, permission_denied

- Add unit tests in `tests/unit/skills/test_script_tools.py`:
  - script_list with specific skill and all skills
  - script_help execution and parsing
  - script_run with JSON output (valid JSON parsing)
  - script_run with plain text output (json=False)
  - script_run with invalid JSON when json=True (parse error)
  - Name normalization (case-insensitive, "status" == "status.py")
  - Error handling (script not found, execution failure, non-zero exit)
  - Timeout handling (60s hard timeout, structured error)
  - Output size limits (1MB truncation, warning in message)
  - Stderr capture in error messages
  - Args normalization (None → [])

## 7. Update AgentConfig for Skills

- Modify `src/agent/config.py`:
  - Add `agent_skills_dir: Path` (default: `~/.agent/skills`)
  - Add `core_skills_dir: Path` (default: `<repo>/skills/core`)
  - Add `enabled_skills: list[str]` (from AGENT_SKILLS env variable)
  - Add `script_timeout: int` (default: 60)
  - Add `max_script_output: int` (default: 1048576 = 1MB)
  - Update `from_env()` to parse AGENT_SKILLS (~line 90):
    ```python
    # Parse AGENT_SKILLS: "kalshi-markets,hello-extended", "all", "all-untrusted", "none", or empty
    skills_str = os.getenv("AGENT_SKILLS", "").strip()
    if skills_str in ("", "none"):
        config.enabled_skills = []
    elif skills_str == "all":
        config.enabled_skills = ["all"]  # Special marker: load all TRUSTED skills
    elif skills_str == "all-untrusted":
        config.enabled_skills = ["all-untrusted"]  # Special marker: load ALL skills (Phase 2)
    else:
        config.enabled_skills = [s.strip() for s in skills_str.split(",")]
    ```
  - Update `validate()` to check enabled skills exist (if not "all")
- Add unit tests for skill configuration in `tests/unit/core/test_config.py`:
  - Parse comma-separated list
  - Handle "all" and "none"
  - Whitespace handling
  - Empty string handling

## 8. Update Agent Class for Skill Loading

- Modify `src/agent/agent.py`:
  - In `__init__()`, after HelloTools initialization (~line 90):
    ```python
    # Initialize toolsets (avoid global state)
    if toolsets is None:
        toolsets = [HelloTools(self.config)]

        # Load skills if enabled
        if self.config.enabled_skills:
            from agent.skills import SkillLoader
            skill_loader = SkillLoader(self.config)
            try:
                skill_toolsets, script_tools = skill_loader.load_enabled_skills()
                toolsets.extend(skill_toolsets)  # Add skill toolsets
                toolsets.append(script_tools)    # Add script wrapper tools
                logger.info(
                    f"Loaded {len(skill_toolsets)} skill toolsets, "
                    f"{script_tools.script_count} scripts"
                )
            except Exception as e:
                logger.error(f"Failed to load skills: {e}", exc_info=True)
                # Continue without skills - graceful degradation

    self.toolsets = toolsets
    ```
  - Add error handling for skill loading failures (log and continue)
  - Log loaded skill names at INFO level
- Ensure backward compatibility (skills optional, no breaking changes)
- Add unit tests in `tests/unit/core/test_agent.py`:
  - Agent with no skills (backward compat)
  - Agent with kalshi-markets (scripts only)
  - Agent with hello-extended (hybrid)
  - Graceful degradation on skill load failure

## 9. Implement Skill Manager (Phase 2)

- Create `src/agent/skills/manager.py` with:
  - `SkillManager` class for lifecycle operations
  - `install(git_url, skill_name=None, trusted=False)`:
    - Confirm if not trusted: "Install untrusted skill from <url>? [y/N]"
    - Clone to `~/.agent/skills/<name>` (or skills/core/ for bundled)
    - Pin to commit SHA, record in registry
    - Validate SKILL.md exists and parses
    - Rollback on failure
  - `update(skill_name, confirm=True)`:
    - Show current SHA vs new SHA
    - Confirm update: "Update <name> from <old_sha> to <new_sha>? [y/N]"
    - Strategy: Clean update via git reset --hard or fresh clone (no merges - local changes not supported)
    - Update SHA in registry
  - `remove(skill_name)` - delete skill directory and unregister
  - `list_installed()` - list all installed skills with metadata
  - `info(skill_name)` - show detailed metadata (manifest, SHA, scripts, toolsets)
- Use GitPython for git operations
- Add unit tests in `tests/unit/skills/test_manager.py` (mock git operations):
  - Install with confirmation
  - SHA pinning
  - Update flow with SHA comparison
  - Rollback on failure
  - Remove cleanup

## 10. Implement Skill CLI Commands (Phase 2)

- Create `src/agent/cli/skill_commands.py` with command implementations:
  - `skill_add(git_url, name=None, trusted=False)` - install skill with confirmation
  - `skill_list()` - list installed skills (name, version, enabled, SHA, source)
  - `skill_info(name)` - show detailed metadata (manifest, SHA, scripts, toolsets)
  - `skill_update(name, confirm=True)` - update skill with SHA diff
  - `skill_remove(name)` - remove skill with confirmation
- Modify `src/agent/cli/app.py` to add skill subcommand group:
  ```python
  skill_app = typer.Typer(help="Manage agent skills")
  app.add_typer(skill_app, name="skill")

  @skill_app.command("add")
  def add_skill(
      git_url: str,
      name: str = typer.Option(None, help="Custom skill name"),
      trusted: bool = typer.Option(False, help="Skip trust confirmation")
  ):
      """Install a skill from a git repository."""
      ...
  ```
- Update `agent --check` in `app.py` to show enabled skills with load status:
  ```
  Skills:
    ✓ kalshi-markets (enabled) - 10 scripts, 0 toolsets [abc123de]
    ✓ hello-extended (enabled) - 1 script, 1 toolset [def456gh]
    ○ github-devops (disabled) - 5 scripts, 2 toolsets [789abc12]
    ✗ broken-skill (enabled) - Load failed: Invalid manifest (missing 'description')
  ```
  - Show short reason for load failures (manifest invalid, import error, missing scripts dir)
- Add help text, error messages, rich formatting
- Create integration tests in `tests/integration/skills/test_skill_cli.py`:
  - Install with confirmation flow
  - List output formatting
  - Info command output
  - Update with SHA comparison
  - Remove cleanup verification

## 11. Adapt Kalshi-Markets Reference Skill

- Copy kalshi-markets skill from `ai-examples/beyond-mcp/apps/4_skill/.claude/skills/kalshi-markets/` to `skills/core/kalshi-markets/`
- Review SKILL.md to ensure it follows our schema (should already be compliant)
- Verify all 10 scripts work with `uv run` and PEP 723 dependencies:
  ```bash
  uv run skills/core/kalshi-markets/scripts/status.py --help
  uv run skills/core/kalshi-markets/scripts/status.py --json
  ```
- Manually add to registry (or use CLI in Phase 2)
- Test loading: `export AGENT_SKILLS="kalshi-markets" && agent --check`
- Test script wrapper tools:
  ```bash
  agent -p "Use script_help to learn about kalshi-markets status script"
  agent -p "Use script_run to check Kalshi exchange status"
  ```

## 12. Create Hello-Extended Example Skill

- Create `skills/core/hello-extended/` structure:
  - `SKILL.md` with YAML front matter:
    ```yaml
    ---
    name: hello-extended
    description: Extended hello skill demonstrating both Python toolsets and standalone scripts.
    version: 1.0.0
    toolsets:
      - toolsets.hello:HelloExtended
    scripts_ignore:
      - "*_test.py"
    ---
    ```
  - `toolsets/__init__.py` (empty)
  - `toolsets/hello.py` with HelloExtended(AgentToolset):
    - Demonstrate Python toolset pattern
    - Add a few simple tools (greet_in_language, greet_multiple, etc.)
  - `scripts/advanced_greeting.py` - standalone PEP 723 script:
    - Demonstrate script pattern with `--help` and `--json`
    - More complex greeting logic (time-based, personalization, etc.)
  - Both patterns in one skill to show hybrid approach
- Test manual installation and loading
- Verify both toolset and script wrapper work

## 13. Create Integration Tests

- Create `tests/integration/skills/test_skill_lifecycle.py`:
  - Full workflow: manual install → enable → load → use tools → use scripts
  - Test skill isolation (one skill doesn't affect another)
  - Test kalshi-markets skill loading and script execution
  - Test hello-extended skill with both toolsets and scripts
  - Test AGENT_SKILLS=all (only loads trusted skills)
  - Test name normalization (Kalshi-Markets == kalshi_markets)
  - Test error scenarios (missing dependencies, invalid manifest)
  - Verify tool name collisions are handled (log warning, use first)
- Create `tests/integration/skills/test_skill_cli.py` (Phase 2):
  - Install from git → enable → list → info → update → remove
  - Mock git operations in tests using pytest fixtures

## 14. Update Documentation

- Update `README.md`:
  - Add "Skills" section explaining the plugin system
  - Reference kalshi-markets as primary example
  - Show script_list, script_help, and script_run usage examples
  - Add installation examples for skills
  - Add environment variable documentation (AGENT_SKILLS with all values)
  - Document script conventions (--help, --json, JSON-only stdout)
- Create `.env.example` with:
  ```bash
  # Skills Configuration
  # AGENT_SKILLS=kalshi-markets,hello-extended  # Comma-separated list (case-insensitive)
  # AGENT_SKILLS=all                             # Enable all TRUSTED skills
  # AGENT_SKILLS=all-untrusted                   # Enable all skills (including untrusted, Phase 2)
  # AGENT_SKILLS=none                            # Disable all (or leave unset)

  # Script execution safety (Phase 1 uses hard-coded defaults)
  # SCRIPT_TIMEOUT=60                            # Seconds (Phase 2)
  # MAX_SCRIPT_OUTPUT=1048576                    # 1MB (Phase 2)
  ```
- Add inline documentation and docstrings throughout skill subsystem

## 15. Add Skill Development Guide

- Create `docs/SKILLS.md`:
  - How to create a custom skill (follow kalshi-markets pattern)
  - Minimal SKILL.md YAML reference inline:
    ```yaml
    ---
    name: my-skill
    description: Brief description of what this skill does.
    toolsets:
      - toolsets.mytools:MyToolset
    ---
    ```
  - SKILL.md manifest reference (YAML front matter format, required vs optional fields)
  - Toolset format: "module:Class" (e.g., "toolsets.hello:HelloExtended")
  - Toolset vs script guidelines (when to use each):
    - Toolsets: Frequent operations, need testing, share state, type-safe
    - Scripts: Infrequent operations, context-heavy, standalone, progressive disclosure
  - Progressive disclosure best practices
  - Script conventions:
    - Must support `--help` flag
    - Should support `--json` flag
    - When `--json`: Emit ONLY valid JSON to stdout (no banners)
    - Use stderr for logs/warnings
    - Exit code 0 for success
    - PEP 723 for dependencies
  - Name normalization (case-insensitive, hyphens/underscores)
  - Testing patterns for skills
  - Publishing skills (git repository, README, examples)
  - Walkthrough: adapting kalshi-markets as example
  - Path sanitization requirements

## 16. Validate Context Efficiency

- Create `tests/validation/test_context_overhead.py`:
  - Measure token count with no skills loaded (baseline)
  - Measure token count with kalshi-markets loaded
  - Measure token count with kalshi-markets + hello-extended loaded
  - Validate <5K token overhead goal
  - Verify scripts NOT loaded until executed (only SKILL.md and script metadata)
  - Use tiktoken to count tokens in tool schemas
  - Count only what the framework sends to the model (function descriptors + instructions)
  - Ensure full SKILL.md is NOT injected into system prompt unless explicitly requested
  - Measure on Windows and Linux for path handling verification
- Document results in test output
- Add to validation commands

## 17. Run Full Validation Suite

- Execute all validation commands (see Validation Commands section)
- Fix any regressions
- Ensure zero breaking changes to existing functionality
- Validate skill system with real-world scenarios
- Verify kalshi-markets scripts execute correctly
- Verify hello-extended hybrid approach works

# Testing Strategy

## Unit Tests

- **Manifest Parsing** (`test_manifest.py`):
  - Valid SKILL.md parsing (YAML front matter + markdown)
  - Invalid manifest rejection (bad YAML, missing required fields)
  - Missing YAML front matter markers
  - Edge cases (empty descriptions, missing optional fields)
  - Parse kalshi-markets SKILL.md as test case
  - Required field validation
  - Optional field handling

- **Skill Loader** (`test_loader.py`):
  - Directory scanning and SKILL.md discovery
  - Toolset instantiation from skill packages
  - Script discovery in scripts/ directories (metadata only)
  - Load kalshi-markets (scripts only, no toolsets)
  - Load hello-extended (both toolsets and scripts)
  - Error handling for missing files, invalid imports
  - Load from core_skills_dir and user skills_dir
  - Handle "all" special marker in enabled_skills

- **Skill Manager** (`test_manager.py`):
  - Git operations (install, update, remove) with mocked GitPython
  - Registry updates on lifecycle operations
  - Conflict handling (duplicate skill names)
  - Rollback on failed installations
  - SHA pinning and tracking
  - Trust confirmation flow

- **Skill Registry** (`test_registry.py`):
  - Registration and persistence
  - Query operations (list, get)
  - SHA update tracking
  - Concurrent access safety
  - JSON serialization/deserialization
  - Migration from older registry formats (if applicable)

- **Script Wrapper Tools** (`test_script_tools.py`):
  - script_list with specific skill and all skills
  - script_help execution and output parsing
  - script_run with JSON output (valid JSON)
  - script_run with plain text output (json=False)
  - script_run with invalid JSON when json=True (parse error handling)
  - Name normalization (case-insensitive, .py extension handling)
  - Error handling (script not found, execution failure, non-zero exit)
  - Timeout handling (60s, structured error response)
  - Output size limits (1MB truncation)
  - Stderr capture in error messages (truncated tail)
  - Args normalization (None → [])
  - Windows path resolution

- **Security** (`test_security.py`):
  - Name sanitization (alphanumeric + hyphens)
  - Path traversal prevention (../, absolute paths)
  - Reserved name rejection (., .., ~)
  - Manifest validation
  - Trust confirmation (mocked user input)

- **Configuration** (`test_config.py`):
  - AGENT_SKILLS parsing (comma-separated, whitespace handling)
  - "all" (trusted only), "all-untrusted", and "none" special values
  - Skill directory path resolution (core_skills_dir, agent_skills_dir)
  - Backward compatibility (config works without skills)
  - Script timeout, max output, and max args defaults
  - Version compatibility validation (min/max_agent_base_version)

## Integration Tests

- **Skill Lifecycle** (`test_skill_lifecycle.py`):
  - Manual install → enable in config → load → use toolset → use script → disable
  - Multiple skills loaded simultaneously
  - Skill isolation (namespace conflicts, dependency conflicts)
  - kalshi-markets end-to-end (load, script_list, script_help, script_run)
  - hello-extended end-to-end (load, toolset methods, script_run)
  - AGENT_SKILLS=all respects trust (only loads trusted)
  - AGENT_SKILLS=all-untrusted loads all (Phase 2)
  - Name normalization (Kalshi-Markets == kalshi_markets)
  - Stable sorting of skill lists

- **CLI Commands** (`test_skill_cli.py` - Phase 2):
  - `agent skill add` with various git URLs
  - `agent skill list` output formatting
  - `agent skill info` detailed output
  - `agent skill update` with git conflicts
  - `agent skill remove` cleanup verification
  - Error handling and user-friendly messages
  - Trust confirmation flows

- **Agent Integration** (`test_agent_with_skills.py`):
  - Agent loads skills based on config
  - Tools from skills available to LLM
  - Script wrapper tools registered (script_list, script_help, script_run)
  - Skill tools follow AgentToolset contract (success, result, message)
  - Graceful degradation if skill fails to load (log error, continue)
  - No skills loaded (backward compat)
  - Tool name collisions handled (log warning, document guidelines to avoid)

## Edge Cases

- **Path Sanitization and Name Normalization**:
  - `../../../etc/passwd` → Rejected (path traversal)
  - `/absolute/path` → Rejected (absolute path)
  - `my-skill-123` → Accepted, canonical: `my-skill-123`
  - `My_Skill_123` → Accepted, canonical: `my-skill-123`
  - `Kalshi-Markets` → Accepted, canonical: `kalshi-markets`
  - `.hidden` → Rejected (reserved)
  - `~` → Rejected (reserved)
  - `__pycache__` → Rejected (reserved)
  - `skill name with spaces` → Rejected (invalid chars)
  - Script: `Status` → Normalized to `status.py`
  - Script: `status.py` → Normalized to `status.py`
  - Script: `status` → Normalized to `status.py`

- **Missing Dependencies**:
  - Skill requires Python package not installed → Clear error message
  - Toolset import failure → Log error, skip skill, continue
  - Script PEP 723 dependency missing → Error returned from script execution

- **Invalid Manifest**:
  - Malformed YAML → Validation error with line numbers
  - Missing required fields → Clear error listing missing fields
  - Invalid field values → Type validation errors
  - No YAML front matter → Error: "SKILL.md must start with YAML front matter"

- **Git Repository Issues** (Phase 2):
  - Repository not found → User-friendly error
  - Network timeout → Retry with exponential backoff (3 attempts)
  - Authentication required → Error: "Repository requires authentication"
  - Merge conflicts on update → Stash changes, pull, apply (or error if conflicts)

- **Script Execution Failures**:
  - PEP 723 script missing dependency → Error from uv with installation hint
  - Script timeout (60s) → {"success": False, "error": "timeout", "message": "Script timed out after 60s\nstderr: <last 500 bytes>"}
  - Output too large (>1MB) → Truncate stdout at 1MB, include warning in message
  - Args too large (>100 args or >4KB) → {"success": False, "error": "args_too_large", "message": "Too many arguments: 150 (max 100)"}
  - Invalid JSON when json=True → {"success": False, "error": "parse_error", "message": "Expected JSON output, got: <first 200 chars>\nstderr: <last 500 bytes>"}
  - Non-zero exit code → {"success": False, "error": "execution_failed", "message": "Script failed with exit code X\nstderr: <last 500 bytes>"}
  - Script not found → {"success": False, "error": "not_found", "message": "Script 'xyz' not found in skill 'kalshi-markets'"}
  - Skill not found → {"success": False, "error": "not_found", "message": "Skill 'unknown-skill' not loaded or installed"}
  - Invalid skill/script name → {"success": False, "error": "invalid_name", "message": "Invalid skill name: '../etc'"}
  - Permission denied (Phase 2) → {"success": False, "error": "permission_denied", "message": "Env var 'SECRET_KEY' not in allowlist"}

- **Skill Name Conflicts**:
  - Two skills with same name → Error during registration
  - Prompt user to rename or choose different source

- **Backward Compatibility**:
  - agent-base works perfectly without any skills installed
  - AGENT_SKILLS unset → No skills loaded, agent works normally
  - Empty skills directory → Agent works normally

- **Skill Update with Breaking Changes**:
  - SKILL.md schema changes → Migration path or error
  - Toolset signature changes → Depends on Python compatibility

- **Disk Space**:
  - Installing large skill → Check available space or stream installation (Phase 2)
  - Warn if <100MB free

- **Concurrent Modifications**:
  - Two processes installing skills simultaneously → File locking or atomic writes

# Acceptance Criteria

1. **Skill Installation**:
   - Users can install skills by copying to skills/core/ (Phase 1)
   - Users can install skills using `agent skill add <git-url>` with explicit confirmation (Phase 2)
   - Installation validates SKILL.md manifest and reports errors clearly
   - Installed skills are registered in `~/.agent/skills/registry.json` with full metadata

2. **Skill Loading**:
   - Agent loads only skills listed in AGENT_SKILLS environment variable
   - Support comma-separated list, "all", "none", and empty
   - Skill toolsets integrate seamlessly with existing tools
   - Skill scripts are registered via wrapper tools (NOT loaded into context)
   - Loading failures are logged with actionable error messages
   - Graceful degradation if skill fails to load

3. **Script Wrapper Tools**:
   - `script_list(skill_name)` returns available scripts with metadata (name, path)
   - `script_help(skill_name, script_name)` returns help text from `--help`
   - `script_run(skill_name, script_name, args, json)` executes script and returns structured response
   - LLM can discover available scripts → get help → execute (progressive disclosure workflow)
   - All responses follow AgentToolset standard (success, result, message)
   - Works with any PEP 723 script following conventions
   - Name matching is case-insensitive ("Status" == "status.py" == "status")
   - Error codes: not_found, invalid_name, args_too_large, timeout, parse_error, execution_failed, permission_denied
   - Max 100 args or 4KB total length (prevent abuse)
   - UTF-8 encoding for stdout/stderr
   - Windows fallback: sys.executable -m uv if uv not on PATH

4. **Context Efficiency**:
   - Base agent with no skills loaded: <2K token overhead
   - Agent with kalshi-markets (10 scripts) loaded: <3K token overhead
   - Agent with kalshi-markets + hello-extended loaded: <5K token overhead
   - Standalone scripts are NOT loaded until invoked (verified with kalshi-markets 10 scripts)
   - Only SKILL.md manifest and script metadata contribute to context

5. **Security**:
   - Path sanitization prevents directory traversal
   - Reserved names rejected
   - Trust confirmation required for git installs (Phase 2)
   - SHA pinning for reproducibility (Phase 2)
   - Manifest validated before installation completes

6. **CLI Usability** (Phase 2):
   - `agent skill list` shows all installed skills with metadata (name, version, active via AGENT_SKILLS, SHA)
   - "Active" displayed instead of "enabled" (clarifies it's runtime via env var, not persisted)
   - Stable sorted by canonical name
   - `agent skill info <name>` shows detailed info (scripts, toolsets, manifest, fully qualified tool names)
   - `agent skill update <name>` updates via clean reset or fresh clone (no merge conflicts, local changes discarded)
   - `agent skill remove <name>` cleans up all files and registry entries
   - `agent --check` shows skill status:
     - Active/inactive (via AGENT_SKILLS env var)
     - Script count, toolset count, SHA
     - Load failures with short reasons
     - Hint: "To enable: export AGENT_SKILLS=skill-name"

7. **Testing**:
   - All skill subsystem components have >80% unit test coverage
   - Integration tests validate full skill lifecycle with kalshi-markets and hello-extended
   - Edge cases handled gracefully with clear error messages
   - Zero regressions in existing agent functionality

8. **Documentation**:
   - README explains skill system with kalshi-markets as primary example
   - Shows script_help and script_run usage
   - Skill development guide (docs/SKILLS.md) enables users to create custom skills
   - .env.example includes AGENT_SKILLS configuration examples
   - Inline documentation throughout skill subsystem

9. **Backward Compatibility**:
   - agent-base works identically without any skills installed
   - Existing toolset pattern (HelloTools) continues working
   - No breaking changes to Agent or AgentConfig APIs
   - AGENT_SKILLS unset or empty → no skills loaded, agent works normally

10. **Reference Skills**:
    - kalshi-markets skill demonstrates pure script-based skill (10 standalone scripts)
    - hello-extended skill demonstrates hybrid approach (toolsets + scripts)
    - Both include comprehensive SKILL.md with usage instructions
    - Can be used as templates for new skills
    - All scripts in kalshi-markets executable via wrapper tools

# Validation Commands

Execute every command to validate the feature works correctly with zero regressions.

```bash
# Phase 1 Validation (Foundation)

# 1. Run all unit tests
cd /Users/danielscholl/source/github/danielscholl/agent-base && uv run pytest tests/unit/ -v

# 2. Run skill-specific unit tests
uv run pytest tests/unit/skills/ -v -m unit

# 3. Manually install kalshi-markets to skills/core/
cp -r ai-examples/beyond-mcp/apps/4_skill/.claude/skills/kalshi-markets skills/core/

# 4. Validate kalshi-markets skill loading
export AGENT_SKILLS="kalshi-markets"
uv run agent --check  # Should show: kalshi-markets (enabled) - 10 scripts, 0 toolsets

# 5. Test script_list wrapper
uv run agent -p "Use script_list to see all available scripts in kalshi-markets"

# 6. Test script_help wrapper
uv run agent -p "Use script_help to learn about the kalshi-markets status script"

# 7. Test script_run wrapper with status script
uv run agent -p "Use script_run to check the Kalshi exchange status"

# 8. Test script_run with search script
uv run agent -p "Use script_run to search kalshi markets for 'bitcoin'"

# 9. Test name normalization (case-insensitive)
uv run agent -p "Use script_run with skill 'Kalshi-Markets' and script 'Status' to check status"

# 10. Manually install hello-extended (after creating it)
# (Copy to skills/core/ once created in step 12)

# 11. Enable both skills
export AGENT_SKILLS="kalshi-markets,hello-extended"
uv run agent --check  # Should show both skills

# 12. Test script_list for all skills
uv run agent -p "Use script_list to see all available scripts across all skills"

# 13. Test hello-extended toolset
uv run agent -p "Use the hello-extended skill to greet me in Spanish"

# 14. Test hello-extended script
uv run agent -p "Use script_list to see hello-extended scripts"
uv run agent -p "Use script_help to learn about hello-extended advanced greeting"
uv run agent -p "Use script_run to execute hello-extended advanced greeting with args"

# 15. Test backward compatibility (no skills)
unset AGENT_SKILLS
uv run agent -p "Say hello"  # Should work normally with HelloTools

# 16. Test "all" special value (trusted only)
export AGENT_SKILLS="all"
uv run agent --check  # Should show only trusted/bundled skills

# 17. Test "none" special value
export AGENT_SKILLS="none"
uv run agent --check  # Should show no skills loaded

# 18. Test case-insensitive matching
export AGENT_SKILLS="Kalshi-Markets,Hello_Extended"
uv run agent --check  # Should load both (normalized to canonical names)

# 15. Run integration tests
uv run pytest tests/integration/skills/ -v -m integration

# 16. Run full test suite with coverage
uv run pytest tests/ --cov=src/agent/skills --cov-report=term-missing

# 17. Run mypy type checking
uv run mypy src/agent/skills/

# 18. Run ruff linting
uv run ruff check src/agent/skills/

# 19. Run black formatting check
uv run black --check src/agent/skills/

# 20. Validate context overhead
export AGENT_SKILLS="kalshi-markets,hello-extended"
uv run pytest tests/validation/test_context_overhead.py -v
# Should validate <5K token overhead with both skills


# Phase 2 Validation (CLI - when implemented)

# 27. Test skill add from git
uv run agent skill add https://github.com/example/test-skill
# Should prompt for confirmation, clone, pin SHA, register

# 28. Test skill list
uv run agent skill list
# Should show all installed skills with metadata, stable sorted

# 29. Test skill info
uv run agent skill info kalshi-markets
# Should show detailed info: scripts, toolsets, SHA, manifest

# 30. Test skill update
uv run agent skill update kalshi-markets
# Should show SHA diff, prompt for confirmation, update via clean reset

# 31. Test skill remove
uv run agent skill remove test-skill
# Should prompt for confirmation, delete directory, unregister

# 32. Test enhanced agent --check with load failure
# (Create invalid skill to test failure display)
uv run agent --check
# Should show skill status with enabled/disabled, counts, SHAs, load failures with reasons

# 33. Test git update conflict handling
# (Make local changes to installed skill, attempt update)
uv run agent skill update test-skill
# Should warn about local changes, offer clean reset
```

# Notes

## Phase 1 MVP Scope

**Goal**: Ship functional skill loading without full CLI lifecycle

**What's Included**:
1. Manifest parsing (`manifest.py`)
2. Skill loader with script discovery (`loader.py`)
3. Script wrapper tools (`script_tools.py`)
4. Registry with JSON persistence (`registry.py`)
5. Security validation (`security.py`)
6. Config integration (`config.py`, `agent.py`)
7. Unit tests for all above
8. Manual skill installation (copy to skills/core/)
9. agent --check shows loaded skills
10. kalshi-markets skill adapted and working
11. hello-extended skill created and working

**What's Deferred**:
- Git operations (install/update/remove via CLI)
- Full CLI commands with interactive confirmations
- Script execution safety (timeouts, output limits) - basic version in Phase 1
- Enhanced agent --check formatting

**Validation**:
```bash
# Manually copy kalshi-markets to skills/core/
cp -r ai-examples/beyond-mcp/apps/4_skill/.claude/skills/kalshi-markets skills/core/

# Enable and test
export AGENT_SKILLS="kalshi-markets"
agent --check  # Should show kalshi-markets loaded with 10 scripts
agent -p "Use script_help to see what kalshi scripts are available"
agent -p "Use script_run to check Kalshi exchange status"
```

## Future Considerations

1. **Skill Registry Server**: Optional central registry for discovering community skills (like npm, PyPI)
2. **Skill Versioning**: Support for semantic versioning and compatibility matrices
3. **Skill Dependencies**: Skills can depend on other skills, creating a dependency graph
4. **Skill Sandboxing**: Security isolation for untrusted skills (separate Python processes, resource limits, cgroups)
5. **Skill Marketplace**: Web UI for browsing and installing skills
6. **Skill Templates**: `agent skill create <name>` scaffolding command with cookiecutter
7. **Hot Reload**: Reload skills without restarting agent (watchdog for file changes)
8. **Skill Analytics**: Track usage, performance metrics, errors (opt-in telemetry)
9. **Skill Permissions**: Declare required permissions in SKILL.md (filesystem, network, env vars)
10. **Skill Testing Framework**: Built-in testing utilities for skill developers
11. **script_help Caching**: Cache help results per-process with short TTL (avoid repeated subprocess calls in single session)
12. **AGENT_SKILLS=all Warning**: If no trusted skills found, show gentle warning: "No trusted skills installed. Install skills with 'agent skill add' or use AGENT_SKILLS=all-untrusted"
13. **Auto-Prefix on Collision**: Behind config flag SKILL_AUTO_PREFIX=true, auto-prefix conflicting tool names with skill name

## Architecture Decisions

1. **Why Git-Based Distribution?**
   - Familiar to developers (like kubectl plugins, VS Code extensions)
   - Built-in versioning and history
   - Easy to fork and customize
   - No central infrastructure required
   - Works offline once cloned
   - Natural fit for open-source collaboration

2. **Why Hybrid Toolsets + Scripts?**
   - Toolsets (Python classes): Testable, type-safe, IDE-friendly, but consume context
   - Scripts (PEP 723): Zero context until invoked, perfect for rare/complex operations
   - Balance between DX and LLM efficiency
   - kalshi-markets proves this works: 10 scripts, ~200-300 lines each, zero context until used
   - Developers choose based on use case

3. **Why SKILL.md with YAML Front Matter?**
   - Combines machine-readable metadata with human-readable instructions
   - LLMs can read the full context (manifest + usage guide) in one file
   - Proven pattern from kalshi-markets reference implementation
   - Can be parsed without executing code (security)
   - Easy for tools to read and modify
   - Familiar format (similar to Jekyll, Hugo, other static site generators)

4. **Why Not MCP Servers?**
   - MCP servers are great for standardization
   - But cost 15K+ tokens per session (full schema loaded)
   - Skills provide 98% context reduction via progressive disclosure
   - kalshi-markets demonstrates: 10 tools available, but only SKILL.md loaded (~50 lines)
   - Skills can wrap MCP servers if needed
   - Simpler deployment (no separate server process)

5. **Why Adapt kalshi-markets as Reference?**
   - Real-world, production-ready skill with 10 working scripts
   - Demonstrates progressive disclosure pattern perfectly
   - Proven architecture from beyond-mcp research
   - Shows standalone scripts can be powerful without toolset complexity
   - Provides immediate value (prediction market data access)
   - Already follows PEP 723 conventions

6. **Why Script Wrapper Tools Instead of Per-Script Registration?**
   - Agent framework infers tool schemas from Python callables
   - PEP 723 scripts don't have static type info
   - Registering individual scripts would require guessing parameters
   - Generic wrappers preserve progressive disclosure
   - LLM can discover usage via script_help before execution
   - Works with any script following conventions (--help, --json)

7. **Why Simple Config-Based Activation?**
   - Avoids complexity of keyword matching (regex, RAG, false positives/negatives)
   - User has explicit control
   - Predictable behavior
   - Easy to debug ("Why isn't my skill loading?" → Check AGENT_SKILLS)
   - Can add smart activation later if needed

8. **How Are Tool Name Collisions Handled?**
   - If two skills define tools with the same name, the framework may confuse them
   - **Phase 1 approach**: Log warning with fully qualified source, use first occurrence
     - Log format: "Tool name collision: 'search' from kalshi-markets.KalshiTools.search conflicts with github-devops.GitHubTools.search (using first)"
   - **Guidelines for skill developers**:
     - Prefix tool names with skill context (e.g., `kalshi_search`, `github_search` instead of `search`)
     - Or namespace via toolset class name (e.g., class KalshiMarketTools)
   - **Future consideration**: Auto-prefix on collision behind config flag (SKILL_AUTO_PREFIX=true)

9. **How Are Toolsets Dynamically Imported?**
   - Use `importlib.util.spec_from_file_location()` to avoid permanent sys.path edits
   - Parse "module:Class" format (e.g., "toolsets.hello:HelloExtended")
   - Import module, get class, instantiate with config
   - Validate class exists and inherits from AgentToolset
   - Log and skip on import failure (graceful degradation)

## Dependencies to Add

**Add to pyproject.toml**:
```toml
dependencies = [
    # ... existing
    "gitpython>=3.1.40",     # Git operations
    "pyyaml>=6.0.1",         # YAML parsing (Pydantic does NOT include this)
]

[project.optional-dependencies]
dev = [
    # ... existing
    "tiktoken>=0.5.0",       # Token counting for validation
]
```

**Critical**: PyYAML is NOT included in Pydantic. Must be added explicitly.

**Alternative**: Consider `ruamel.yaml` for better error messages and round-trip preservation.

**Note**: kalshi-markets scripts already have embedded dependencies via PEP 723 (httpx, click) - no global installation needed!

## Implementation Notes

### Dynamic Import Strategy

```python
# In loader.py
from importlib.util import spec_from_file_location, module_from_spec

def _import_toolset(skill_path: Path, toolset_def: str, config: AgentConfig) -> AgentToolset | None:
    """Import and instantiate a toolset from "module:Class" format.

    Example: "toolsets.hello:HelloExtended"
    """
    module_path, class_name = toolset_def.split(":")
    file_path = skill_path / f"{module_path.replace('.', '/')}.py"

    spec = spec_from_file_location(f"skill.{module_path}", file_path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    toolset_class = getattr(module, class_name)
    if not issubclass(toolset_class, AgentToolset):
        raise SkillError(f"{class_name} must inherit from AgentToolset")

    return toolset_class(config)
```

### Tool Name Collision Guidelines

**Document in docs/SKILLS.md**:
- Avoid generic names like `get`, `list`, `search`
- Prefix with context: `kalshi_search`, `hello_greet_multilang`
- Or use class naming: `KalshiMarketTools.search()`
- Agent logs warning on collision with fully qualified source:
  - "Tool collision: 'search' from kalshi-markets.KalshiTools.search vs github-devops.GitHubTools.search (using first)"
- Future: Auto-prefix behind config flag (SKILL_AUTO_PREFIX=true)

### Git Update Strategy

**No Merge Conflicts** (Phase 2):
- **Strategy**: Clean updates only - local changes NOT supported
- **Implementation Options**:
  - Option 1: `git reset --hard origin/<branch>` (fast, destructive)
  - Option 2: Fresh clone to temp dir, atomic swap (safer, slower)
- **Rationale**: Avoid merge complexity, treat git installs as immutable
- **Document**: Local changes to installed skills are discarded on update
- **Recommendation**: Fork skill to make changes, install from your fork
- **Warning on update**: "This will discard any local changes. Continue? [y/N]"

## Migration Path

Existing tools can be migrated to skills:
1. Create skill directory structure (follow kalshi-markets pattern)
2. Move toolset class to `toolsets/` OR convert to scripts/ (or both)
3. Create SKILL.md manifest with YAML front matter
4. Test locally by copying to skills/core/
5. Publish to git repository (Phase 2)
6. Update AGENT_SKILLS configuration
7. Remove from core if appropriate

This enables gradual migration without breaking changes.

## Reference Implementation Details

The kalshi-markets skill (`ai-examples/beyond-mcp/apps/4_skill/.claude/skills/kalshi-markets/`) provides the baseline for our implementation:

**Adaptation Steps**:
1. Copy directory structure to `skills/core/kalshi-markets/`
2. Keep SKILL.md format (YAML front matter + markdown instructions)
3. Keep all 10 scripts unchanged (already using PEP 723)
4. No toolset needed - pure script-based skill
5. Verify scripts work:
   ```bash
   uv run skills/core/kalshi-markets/scripts/status.py --help
   uv run skills/core/kalshi-markets/scripts/status.py --json
   ```
6. Test via wrapper tools:
   ```bash
   export AGENT_SKILLS="kalshi-markets"
   agent -p "Use script_help to learn about status script"
   agent -p "Use script_run to check exchange status"
   ```

**What We Learn**:
- Scripts should be self-contained (embedded HTTP client, CLI args via click/typer)
- Each script ~200-300 lines is optimal balance
- `--help` and `--json` flags are essential conventions
- SKILL.md should instruct: "Don't read scripts unless needed - use --help first"
- Progressive disclosure works: 10 tools available, <500 token overhead
- PEP 723 dependency management works seamlessly with `uv run`

This reference validates our hybrid approach: kalshi-markets proves scripts work beautifully, hello-extended will show toolsets complement them.

## Security Considerations

1. **Trust Model**:
   - Bundled skills (skills/core/) are implicitly trusted
   - User-installed skills require explicit confirmation
   - SHA pinning ensures reproducibility
   - Manifest validation before finalization

2. **Path Sanitization**:
   - Prevent directory traversal (../, absolute paths)
   - Alphanumeric + hyphens only
   - Max 64 characters
   - Reserved names rejected

3. **Script Isolation** (Phase 2+):
   - Subprocess execution (already isolated)
   - Timeout enforcement
   - Output size limits
   - Env var allowlist (only forward specified vars)
   - Working directory set to script parent
   - Future: cgroups, resource limits, network restrictions

4. **Code Execution Risks**:
   - Toolsets execute in main process (same as HelloTools)
   - Scripts execute in subprocess (better isolation)
   - Users should review SKILL.md and code before installing
   - Trust confirmation makes risk explicit

5. **Dependency Management**:
   - Toolsets share global dependencies (potential conflicts)
   - Scripts use PEP 723 (isolated per-script)
   - Consider per-skill virtual environments (future)

## Observability Integration

**Skill Operations Should Be Traced** (align with existing observability):
- Skill loading: Add span for `load_enabled_skills()` with attributes (skill names, counts)
- Script execution: Add span for each `script_run()` call with attributes (skill, script, duration, success)
- Use existing `agent_framework.observability.get_tracer()` pattern
- Add custom attributes:
  - `skill.name`, `skill.script`, `skill.execution.duration_ms`
  - `skill.execution.status` (success/timeout/error)
  - `skill.error_type` (timeout|parse_error|execution_failed|...)
  - `skill.stdout_bytes`, `skill.stderr_bytes` (for triage)
- Helps debug skill issues in production

**Phase 1**: Basic logging (INFO level for success, ERROR for failures with skill/script names)
**Phase 2**: Full OTEL spans with attributes
