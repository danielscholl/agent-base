# Feature: Sticky Prompt Bar for Interactive CLI

## Feature Description

Add a persistent bottom toolbar to the agent's interactive mode that displays real-time status information similar to GitHub Copilot CLI. The sticky prompt bar will show contextual information (current directory, git branch, model name, version, and optional execution state) at the bottom of the terminal, remaining visible while the user types and updates dynamically during agent execution.

This feature enhances the interactive CLI experience by:
1. **Providing persistent context** - Users always see where they are and what model they're using
2. **Improving navigation** - Git branch and directory information helps with multi-project workflows
3. **Reducing cognitive load** - Status information visible without scrolling or commands
4. **Professional appearance** - Matches modern CLI tools like GitHub Copilot, Vim, and VSCode terminal

## User Story

As a developer using the agent in interactive mode
I want a persistent bottom toolbar showing my current context
So that I always know my location, git branch, and active model without needing to check manually

## Problem Statement

The current agent-template interactive mode renders a status bar only once at startup (line 430 in cli.py) and after `/clear` commands (line 561). Users lose sight of contextual information as conversation output scrolls past the initial status bar. This creates several problems:

- **Lost context**: After a few exchanges, users can't see their current directory or git branch
- **Model confusion**: Users forget which model they're using, especially when switching between projects
- **Version uncertainty**: Can't quickly verify agent version without scrolling
- **Reduced productivity**: Must run shell commands (`pwd`, `git branch`) to regain context
- **Inconsistent UX**: Modern CLI tools (Copilot, Vim, VSCode) all have persistent status bars

The status information is valuable but ephemeral in the current design. A sticky prompt bar solves this by making context continuously visible.

## Solution Statement

Implement a persistent bottom toolbar using prompt_toolkit's native `bottom_toolbar` feature. The solution leverages:

- **prompt_toolkit.shortcuts.PromptSession** with `bottom_toolbar` parameter
- **FormattedText** for rich styling and color support
- **Existing status bar logic** from `_get_status_bar_text()` function (lines 81-119 in cli.py)
- **Callable toolbar** for dynamic updates during execution
- **Optional refresh_interval** for automatic status updates

The implementation requires minimal changes - just modifying the PromptSession creation and updating the status bar text generator to return FormattedText instead of plain strings. No new dependencies needed as prompt_toolkit and rich are already in use.

## Related Documentation

### Requirements
- `docs/design/requirements.md` - FR-1 (Natural Language Query Interface)
- `docs/specs/interactive.md` - Phase 3 Interactive Mode specification

### Architecture Decisions
- **ADR-0009**: CLI Framework Selection (establishes Typer + Rich foundation)
- **ADR-0010**: Display Output Format (defines display patterns and Rich usage)
- **ADR-0012**: Middleware Integration Strategy (establishes event patterns)

## Archon Project

Project ID: `58d4551a-1f86-48c9-9653-08f06a8217b0`

Created for task tracking and knowledge management. This feature integrates with the existing Archon workflow for systematic development.

## Codebase Analysis Findings

### Architecture Patterns to Follow

**Current CLI Implementation** (from codebase-analyst):
- ✅ **PromptSession** already in use (src/agent/cli.py:485-488)
- ✅ **FileHistory** for persistent command history
- ✅ **Keybindings** infrastructure with KeybindingManager
- ✅ **Status bar text generation** function exists (_get_status_bar_text, lines 81-119)
- ✅ **Rich console** available for formatting

**Discovered Patterns:**
- Status bar currently rendered once via `_render_status_bar()` (lines 122-158)
- Function `_get_status_bar_text()` generates aligned status text (lines 81-119)
- Git branch detection already implemented (lines 90-106)
- Model display name from config (line 115)
- Terminal width handling for alignment (line 112)

### Naming Conventions

**Function Naming (snake_case):**
- `_get_status_bar_text()` - Status text generator (WILL MODIFY)
- `_render_status_bar()` - One-time rendering (WILL KEEP for --check mode)
- `run_chat_mode()` - Interactive mode entry point (WILL MODIFY)

**Module Structure:**
```
src/agent/
├── cli.py              # Main CLI - MODIFY HERE
├── config.py           # AgentConfig - NO CHANGES
└── utils/
    └── keybindings/    # Extensible keybindings - NO CHANGES
```

### Similar Implementations

**Existing Code Reference** (src/agent/cli.py):
1. **Status Bar Text Generation** (lines 81-119):
   - Gets current directory with home path shortening
   - Detects git branch with subprocess
   - Formats with alignment for full terminal width
   - Returns aligned string ready for display

2. **PromptSession Creation** (lines 485-488):
   ```python
   session: PromptSession = PromptSession(
       history=FileHistory(str(history_file)),
       key_bindings=key_bindings,
   )
   ```

**Pattern from prompt_toolkit Documentation:**
```python
def bottom_toolbar():
    """Display the current mode."""
    return [("class:toolbar", " [F4] Vi")]

session = PromptSession(bottom_toolbar=bottom_toolbar)
```

### Integration Patterns

**Existing Status Flow:**
```
CLI Entry
    ↓
_render_startup_banner() → Displays once
    ↓
_render_status_bar() → Displays once
    ↓
PromptSession.prompt_async() → No persistent status
    ↓
User Input → Status scrolls off screen
```

**New Sticky Status Flow:**
```
CLI Entry
    ↓
_render_startup_banner() → Displays once
    ↓
Create PromptSession with bottom_toolbar=lambda: _get_status_bar_text_formatted()
    ↓
PromptSession.prompt_async() → Status always visible at bottom
    ↓
User Input → Status stays at bottom
```

## Relevant Files

### Existing Files to Modify

- **`src/agent/cli.py`** (756 lines → ~780 lines)
  - Modify: `_get_status_bar_text()` to return FormattedText (lines 81-119)
  - Modify: `run_chat_mode()` to add bottom_toolbar parameter (lines 485-488)
  - Add: Optional `StatusState` class for dynamic updates (+15 lines)
  - Add: Imports for FormattedText and Style (+2 lines)
  - Keep: `_render_status_bar()` for non-interactive modes

### New Files to Create

**None required!** This feature leverages existing code and prompt_toolkit capabilities.

### Files NOT Modified

- `src/agent/config.py` - No configuration changes needed
- `src/agent/agent.py` - No agent logic changes
- `src/agent/display/` - No display system changes
- `tests/conftest.py` - Existing fixtures sufficient

## Implementation Plan

### Phase 1: Basic Sticky Toolbar (MVP)

**Goal**: Add persistent bottom toolbar with static status information

**Duration**: 2-3 hours

**Tasks**:
1. Import FormattedText and Style from prompt_toolkit
2. Modify `_get_status_bar_text()` to return FormattedText
3. Add `bottom_toolbar` parameter to PromptSession creation
4. Test basic functionality in interactive mode

### Phase 2: Dynamic Status Updates (Optional Enhancement)

**Goal**: Enable dynamic status updates during agent execution

**Duration**: 1-2 hours

**Tasks**:
1. Create StatusState class for shared state
2. Update status during agent execution
3. Add refresh_interval for auto-refresh
4. Test dynamic updates

## Step by Step Tasks

### Task 1: Modify Status Bar Text Generator

**Description**: Update `_get_status_bar_text()` to return FormattedText instead of string

**Files to modify**:
- `src/agent/cli.py` (lines 81-119)

**Implementation details**:

```python
# Add import at top of file (after existing imports)
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

# Modify function signature and return type
def _get_status_bar_text(config: AgentConfig) -> FormattedText:
    """Get status bar text as FormattedText for toolbar.

    Returns formatted text showing:
    - Current working directory (with ~/ shortening)
    - Git branch (if in a repository)
    - Model name
    - Version
    """
    # Get current directory
    cwd = Path.cwd()
    try:
        # Shorten home directory to ~/
        cwd_display = f"~/{cwd.relative_to(Path.home())}"
    except ValueError:
        # Not in home directory, use full path
        cwd_display = str(cwd)

    # Detect git branch
    branch_display = ""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=1,
        )
        if result.returncode == 0 and result.stdout.strip():
            branch = result.stdout.strip()
            branch_display = f" [⎇ {branch}]"
    except Exception:
        # Not a git repo or git not available
        pass

    # Build left and right sections
    left_text = f" {cwd_display}{branch_display}"
    right_text = f"{config.get_model_display_name()} · v{__version__}"

    # Calculate padding for full-width alignment
    # Note: Console width may vary, FormattedText will handle this
    console_width = console.width if console else 80
    padding = max(1, console_width - len(left_text) - len(right_text))

    # Return as FormattedText with styling
    return FormattedText([
        ('class:toolbar.left', left_text),
        ('class:toolbar.padding', ' ' * padding),
        ('class:toolbar.right', right_text),
    ])
```

**Validation**:
```bash
# Test that function returns FormattedText
uv run python -c "
from agent.cli import _get_status_bar_text
from agent.config import AgentConfig
from prompt_toolkit.formatted_text import FormattedText

config = AgentConfig.from_env()
result = _get_status_bar_text(config)
assert isinstance(result, list), 'Should return list for FormattedText'
print('✓ Status bar text returns FormattedText')
"
```

**Success criteria**:
- [ ] Function returns FormattedText (list of tuples)
- [ ] Directory shortening works correctly
- [ ] Git branch detection works
- [ ] Alignment calculation correct
- [ ] Styling classes applied

---

### Task 2: Add Bottom Toolbar to PromptSession

**Description**: Modify PromptSession creation to include bottom_toolbar parameter

**Files to modify**:
- `src/agent/cli.py` (lines 485-488)

**Implementation details**:

```python
# Modify PromptSession creation in run_chat_mode()
# Located around line 485-488

# Before:
session: PromptSession = PromptSession(
    history=FileHistory(str(history_file)),
    key_bindings=key_bindings,
)

# After:
session: PromptSession = PromptSession(
    history=FileHistory(str(history_file)),
    key_bindings=key_bindings,
    bottom_toolbar=lambda: _get_status_bar_text(config),
    refresh_interval=0.5,  # Refresh every 500ms for dynamic updates
)
```

**Additional: Add custom styling (optional)**:

```python
# Add after keybinding creation, before PromptSession
from prompt_toolkit.styles import Style

# Define toolbar styles
toolbar_style = Style.from_dict({
    'toolbar.left': 'fg:ansiwhite',           # White for directory/branch
    'toolbar.padding': '',                     # No styling for padding
    'toolbar.right': 'fg:ansicyan',            # Cyan for model/version (matches existing)
})

# Update PromptSession creation
session: PromptSession = PromptSession(
    history=FileHistory(str(history_file)),
    key_bindings=key_bindings,
    bottom_toolbar=lambda: _get_status_bar_text(config),
    refresh_interval=0.5,
    style=toolbar_style,  # Apply custom styles
)
```

**Validation**:
```bash
# Start interactive mode
uv run agent

# Verify:
# 1. Bottom toolbar appears at bottom of terminal
# 2. Shows current directory
# 3. Shows git branch (if in repo)
# 4. Shows model name and version
# 5. Toolbar stays visible while typing
# 6. Toolbar updates when directory changes (if refresh_interval enabled)
```

**Success criteria**:
- [ ] Bottom toolbar renders at screen bottom
- [ ] Toolbar shows correct information
- [ ] Toolbar persists during typing
- [ ] Toolbar styling matches design
- [ ] No visual glitches or flickering

---

### Task 3: Optional - Add Dynamic Status State

**Description**: Create StatusState class to enable dynamic status updates during execution

**Files to modify**:
- `src/agent/cli.py` (add new class before run_chat_mode)

**Implementation details**:

```python
# Add before run_chat_mode() function

@dataclass
class StatusState:
    """Shared state for dynamic status bar updates.

    Attributes:
        current_operation: Description of current agent operation
        message_count: Number of messages in conversation
        token_usage: Optional token count display
    """
    current_operation: str | None = None
    message_count: int = 0
    token_usage: int | None = None


# Modify _get_status_bar_text to accept optional StatusState
def _get_status_bar_text(
    config: AgentConfig,
    status_state: StatusState | None = None
) -> FormattedText:
    """Get status bar text as FormattedText for toolbar.

    Args:
        config: Agent configuration
        status_state: Optional state for dynamic updates
    """
    # ... existing directory and branch code ...

    # Build left section with optional operation
    left_text = f" {cwd_display}{branch_display}"
    if status_state and status_state.current_operation:
        left_text += f" | {status_state.current_operation}"

    # Build right section with optional message count
    right_parts = []
    if status_state and status_state.message_count > 0:
        right_parts.append(f"msgs:{status_state.message_count}")
    right_parts.append(config.get_model_display_name())
    right_parts.append(f"v{__version__}")
    right_text = " · ".join(right_parts)

    # ... rest of function ...


# Update run_chat_mode to use StatusState
async def run_chat_mode(...):
    # ... existing code ...

    # Create shared status state
    status_state = StatusState()

    # Update PromptSession to use status_state
    session: PromptSession = PromptSession(
        history=FileHistory(str(history_file)),
        key_bindings=key_bindings,
        bottom_toolbar=lambda: _get_status_bar_text(config, status_state),
        refresh_interval=0.5,
    )

    # ... in the main loop ...
    while True:
        user_input = await session.prompt_async("\n> ")

        # ... command handling ...

        # Update status during execution
        status_state.current_operation = "Thinking..."
        status_state.message_count += 1

        if execution_display:
            await execution_display.start()

        try:
            async for chunk in agent.run_stream(prompt, thread=thread):
                console.print(chunk, end="")
            console.print("\n")
        finally:
            status_state.current_operation = None  # Clear operation
            if execution_display:
                await execution_display.stop()
```

**Validation**:
```bash
# Start interactive mode
uv run agent

# Type a message and observe:
# 1. Status bar shows "Thinking..." during execution
# 2. Message count increments after each exchange
# 3. Status clears when agent completes
# 4. Directory/branch/model remain visible throughout
```

**Success criteria**:
- [ ] StatusState class defined
- [ ] Status updates during execution
- [ ] Message count displays correctly
- [ ] Operation clears after completion
- [ ] No performance impact from refresh

---

### Task 4: Keep Existing Status Bar for Non-Interactive Modes

**Description**: Ensure `_render_status_bar()` still works for --check and other modes

**Files to verify**:
- `src/agent/cli.py` (lines 122-158)

**Implementation details**:

No changes needed! The existing `_render_status_bar()` function will continue to work for:
- Health check mode (`agent --check`)
- Config display mode (`agent --config`)
- Any other non-interactive output

The function internally calls `_get_status_bar_text()` and prints it once. With our changes, it will now receive FormattedText but can still render it:

```python
# Existing _render_status_bar() function (NO CHANGES NEEDED)
def _render_status_bar(config: AgentConfig):
    """Render status bar once for non-interactive modes."""
    status_text = _get_status_bar_text(config)

    # Rich console can render FormattedText directly
    console.print(status_text)
    console.print(f"[dim]{'─' * console.width}[/dim]")
```

**Validation**:
```bash
# Test health check mode
uv run agent --check
# Should still show status bar once at top

# Test config mode
uv run agent --config
# Should still show status bar once at top

# Test single-prompt mode
uv run agent -p "Say hello"
# Should not show status bar (correct behavior)
```

**Success criteria**:
- [ ] Health check displays status bar correctly
- [ ] Config display works as before
- [ ] Single-prompt mode unchanged
- [ ] No regressions in existing modes

---

### Task 5: Write Tests for Sticky Toolbar

**Description**: Create unit and visual tests for bottom toolbar functionality

**Files to create**:
- `tests/unit/test_cli_toolbar.py` (~80 lines)

**Implementation details**:

```python
# tests/unit/test_cli_toolbar.py

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from prompt_toolkit.formatted_text import FormattedText

from agent.cli import _get_status_bar_text, StatusState
from agent.config import AgentConfig


def test_status_bar_returns_formatted_text(mock_config):
    """Test that status bar function returns FormattedText."""
    result = _get_status_bar_text(mock_config)

    # Should return list of (style, text) tuples
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(item, tuple) for item in result)
    assert all(len(item) == 2 for item in result)


def test_status_bar_includes_directory(mock_config):
    """Test that status bar includes current directory."""
    result = _get_status_bar_text(mock_config)

    # Convert FormattedText to string for content check
    text_content = "".join(text for _, text in result)

    # Should contain directory info (at least '/')
    assert "/" in text_content or "~" in text_content


@patch('subprocess.run')
def test_status_bar_includes_git_branch(mock_run, mock_config):
    """Test that git branch is included when available."""
    # Mock git command to return a branch name
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "main\n"
    mock_run.return_value = mock_result

    result = _get_status_bar_text(mock_config)
    text_content = "".join(text for _, text in result)

    # Should contain branch name
    assert "main" in text_content
    assert "⎇" in text_content  # Branch symbol


@patch('subprocess.run')
def test_status_bar_handles_no_git(mock_run, mock_config):
    """Test that status bar works when not in git repo."""
    # Mock git command to fail
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    # Should not raise exception
    result = _get_status_bar_text(mock_config)
    assert isinstance(result, list)


def test_status_bar_includes_model_name(mock_config):
    """Test that model name is displayed."""
    result = _get_status_bar_text(mock_config)
    text_content = "".join(text for _, text in result)

    # Should contain model display name
    model_name = mock_config.get_model_display_name()
    assert model_name in text_content


def test_status_bar_includes_version(mock_config):
    """Test that version is displayed."""
    from agent.cli import __version__

    result = _get_status_bar_text(mock_config)
    text_content = "".join(text for _, text in result)

    # Should contain version
    assert __version__ in text_content


def test_status_bar_with_operation(mock_config):
    """Test status bar shows current operation."""
    status_state = StatusState(current_operation="Thinking...")

    result = _get_status_bar_text(mock_config, status_state)
    text_content = "".join(text for _, text in result)

    assert "Thinking..." in text_content


def test_status_bar_with_message_count(mock_config):
    """Test status bar shows message count."""
    status_state = StatusState(message_count=5)

    result = _get_status_bar_text(mock_config, status_state)
    text_content = "".join(text for _, text in result)

    assert "msgs:5" in text_content


def test_status_bar_styling_classes(mock_config):
    """Test that correct styling classes are applied."""
    result = _get_status_bar_text(mock_config)

    # Check for expected style classes
    styles = [style for style, _ in result]
    assert 'class:toolbar.left' in styles
    assert 'class:toolbar.right' in styles
```

**Visual Testing Checklist** (manual):

```bash
# 1. Basic toolbar display
uv run agent
# ✓ Toolbar appears at bottom
# ✓ Shows current directory
# ✓ Shows git branch
# ✓ Shows model and version

# 2. Toolbar persistence
uv run agent
> Ask a long question that generates multiple lines of output
# ✓ Toolbar stays at bottom during output
# ✓ Toolbar remains visible while typing

# 3. Dynamic updates (if implemented)
uv run agent
> Send a message
# ✓ Toolbar shows "Thinking..." during execution
# ✓ Message count increments
# ✓ Operation clears when done

# 4. Terminal resizing
uv run agent
# Resize terminal window
# ✓ Toolbar adjusts to new width
# ✓ Alignment remains correct

# 5. Directory navigation
uv run agent
> !cd /tmp
# ✓ Toolbar updates to show new directory

# 6. Git branch switching
cd /path/to/git/repo
uv run agent
# In another terminal: git checkout other-branch
# Wait for refresh_interval
# ✓ Toolbar updates to show new branch
```

**Validation**:
```bash
# Run unit tests
uv run pytest tests/unit/test_cli_toolbar.py -v

# Run all tests to check for regressions
uv run pytest tests/ -v

# Check coverage
uv run pytest tests/unit/test_cli_toolbar.py --cov=agent.cli --cov-report=term-missing
```

**Success criteria**:
- [ ] All unit tests pass
- [ ] FormattedText generation tested
- [ ] Directory/branch/model display tested
- [ ] StatusState integration tested
- [ ] Edge cases handled (no git, etc.)
- [ ] Visual testing checklist completed
- [ ] No regressions in existing tests

---

### Task 6: Update Documentation

**Description**: Document the new sticky toolbar feature in user-facing documentation

**Files to modify**:
- `README.md` - Add to Interactive Mode features
- `docs/design/usage.md` - Add sticky toolbar section
- `docs/decisions/0009-cli-framework-selection.md` - Note toolbar addition

**Implementation details**:

**README.md Updates** (after line 34):

```markdown
### ⌨️ Keyboard Shortcuts
- **Shell commands**: Execute system commands with `!` (e.g., `!ls`, `!git status`)
- **Quick clear**: Press `ESC` to clear the prompt
- **Mixed workflows**: Combine AI conversations with direct shell access
- **No context switching**: Stay in agent while checking system state

### 📊 Sticky Status Bar
- **Always visible**: Bottom toolbar shows context at all times
- **Current location**: See your directory and git branch while working
- **Model info**: Know which LLM you're using at a glance
- **Dynamic updates**: Status reflects current operation during execution
```

**docs/design/usage.md Updates** (new section):

```markdown
## Sticky Status Bar

The interactive mode includes a persistent bottom toolbar that displays:

```
~/project/path [⎇ main]                              claude-sonnet-4.5 · v0.1.0
```

**Information displayed:**
- **Current directory**: Shows working directory with `~/` shortening
- **Git branch**: Current branch (if in a git repository)
- **Model name**: Active LLM model from configuration
- **Version**: Agent version number

**Features:**
- **Always visible**: Stays at the bottom while you type and during output
- **Auto-updating**: Refreshes every 500ms to reflect changes
- **Dynamic status**: Shows current operation during execution (optional)
- **Full-width**: Aligned to terminal width with automatic adjustment

**Examples:**

```bash
# In a git repository
~/code/my-project [⎇ feature-branch]              gpt-4o · v0.1.0

# Outside git repository
~/Documents                                        claude-opus-4 · v0.1.0

# During execution (with dynamic updates)
~/code/agent [⎇ main] | Thinking...  msgs:3 · gpt-5-mini · v0.1.0
```

### Keyboard Shortcuts
```

**ADR-0009 Update** (add note at end):

```markdown
## Update: Bottom Toolbar Addition (2025-01-XX)

The CLI now includes a persistent bottom toolbar in interactive mode using prompt_toolkit's `bottom_toolbar` parameter. This enhancement:

- Uses FormattedText for styled output
- Displays current directory, git branch, model, and version
- Updates dynamically with 500ms refresh interval
- Maintains consistency with Typer/Rich design patterns

The toolbar leverages existing Rich styling infrastructure and requires no new dependencies. Implementation follows prompt_toolkit best practices with callable toolbar for dynamic updates.

**Reference**: `docs/specs/sticky-prompt-bar.md`
```

**Validation**:
```bash
# Check documentation completeness
grep -r "sticky" docs/
grep -r "bottom toolbar" docs/

# Verify links work
markdown-link-check README.md
markdown-link-check docs/design/usage.md
```

**Success criteria**:
- [ ] README.md updated with sticky bar feature
- [ ] docs/design/usage.md has comprehensive toolbar section
- [ ] ADR-0009 notes the addition
- [ ] Examples show actual output format
- [ ] All markdown links valid
- [ ] Screenshots added (optional)

## Testing Strategy

### Unit Tests

**New Test File:**
- `tests/unit/test_cli_toolbar.py` (~80 lines)
  - Test FormattedText generation
  - Test directory detection and shortening
  - Test git branch detection
  - Test model and version display
  - Test StatusState integration
  - Test error handling (git not available, etc.)

### Integration Tests

**Visual Testing** (manual checklist):
1. Start interactive mode and verify toolbar appears
2. Type long messages and verify toolbar persists
3. Resize terminal and verify alignment adjusts
4. Navigate directories and verify updates (if dynamic)
5. Switch git branches and verify updates (if dynamic)
6. Test in non-git directories

### Edge Cases to Test

**Environment Variations:**
- Terminal without git installed
- Directory outside home (no ~/ shortening)
- Very long directory paths (truncation needed?)
- Very long branch names
- Detached HEAD git state
- Small terminal width (< 80 chars)

**Error Handling:**
- Git command timeout
- Subprocess exceptions
- Permission denied on git directory
- Corrupted git repository

### Performance Tests

1. **Refresh Impact**:
   - Measure CPU usage with 500ms refresh
   - Test with 100+ char directory paths
   - Verify no lag during typing

2. **Git Command Performance**:
   - Test git branch detection speed
   - Verify 1s timeout prevents hanging
   - Test in large repositories

### Coverage Targets

**Overall**: 85%+ (existing target maintained)

**New Code Coverage**:
- `_get_status_bar_text()` modifications: 95%+
- StatusState class (if added): 90%+
- PromptSession integration: Visual testing (excluded from coverage)

**Excluded from Coverage**:
- PromptSession creation (integration with prompt_toolkit)
- Terminal rendering (visual validation)

## Acceptance Criteria

**Core Functionality:**
- [ ] Bottom toolbar appears in interactive mode
- [ ] Toolbar shows current directory
- [ ] Toolbar shows git branch (when in repo)
- [ ] Toolbar shows model name
- [ ] Toolbar shows version number
- [ ] Toolbar persists during typing
- [ ] Toolbar persists during output
- [ ] Toolbar adjusts to terminal width

**Dynamic Updates** (if implemented):
- [ ] Toolbar refreshes every 500ms
- [ ] Current operation displays during execution
- [ ] Message count increments correctly
- [ ] Status clears when operation completes

**Compatibility:**
- [ ] Non-interactive modes unchanged
- [ ] Health check (`--check`) works as before
- [ ] Config display (`--config`) works as before
- [ ] Single-prompt mode (`-p`) unchanged
- [ ] All existing tests pass

**User Experience:**
- [ ] Styling matches existing design
- [ ] Colors consistent with Rich theme
- [ ] Alignment correct at various widths
- [ ] No visual glitches or flickering
- [ ] Git detection fails gracefully
- [ ] Performance impact negligible

**Testing:**
- [ ] All unit tests pass
- [ ] Visual testing checklist completed
- [ ] Edge cases tested
- [ ] Coverage targets met
- [ ] No regressions

**Documentation:**
- [ ] README.md updated
- [ ] docs/design/usage.md has toolbar section
- [ ] ADR-0009 notes addition
- [ ] Examples show correct format
- [ ] Feature properly explained

## Validation Commands

```bash
# Installation (if needed)
uv sync

# Run new unit tests
uv run pytest tests/unit/test_cli_toolbar.py -v

# Run all tests to check for regressions
uv run pytest tests/ -v --cov=src/agent --cov-fail-under=85

# Code quality checks
uv run black --check src/agent/cli.py
uv run ruff check src/agent/cli.py
uv run mypy src/agent/cli.py

# Manual visual testing
uv run agent
# - Verify bottom toolbar appears
# - Type messages and observe persistence
# - Resize terminal and check alignment
# - Navigate directories with !cd (if dynamic)

# Test health check mode (should work as before)
uv run agent --check

# Test config mode (should work as before)
uv run agent --config

# Test single-prompt mode (should not show toolbar)
uv run agent -p "Say hello"

# Check documentation
cat README.md | grep -A 5 "Sticky Status Bar"
cat docs/design/usage.md | grep -A 10 "Sticky Status Bar"
```

## Notes

### Design Decisions

**Why prompt_toolkit bottom_toolbar?**
- **Native feature**: Built into prompt_toolkit, no hacks needed
- **Proven pattern**: Used by many CLI tools (ipython, ptpython)
- **Auto-rendering**: Handles terminal updates automatically
- **Rich integration**: Works with FormattedText styling
- **Performant**: Optimized for frequent updates

**Why callable toolbar instead of static?**
- **Dynamic updates**: Can show current operation status
- **Directory changes**: Reflects navigation via !cd commands
- **Git branch switching**: Picks up branch changes automatically
- **Message counting**: Can track conversation length
- **Extensible**: Easy to add more dynamic info later

**Why 500ms refresh_interval?**
- **Responsive**: Updates feel immediate to users
- **Performant**: Low enough CPU impact to be negligible
- **Battery-friendly**: Not overly aggressive on laptops
- **Git-safe**: Gives git commands time to complete
- **Tested**: Common interval for CLI status bars

**Why FormattedText over strings?**
- **Styling support**: Enables colors and text formatting
- **Rich compatibility**: Integrates with existing Rich console
- **Consistent UX**: Matches other styled CLI output
- **Extensibility**: Can add icons, bold, underline later
- **Professional**: Modern terminal aesthetics

### Implementation Insights

**Key Discovery from Codebase Analysis:**
- Status bar logic already exists in `_get_status_bar_text()`
- Only need to change return type to FormattedText
- PromptSession already in use, just add one parameter
- No new dependencies required
- Minimal diff, high value

**Pattern from prompt_toolkit Docs:**
```python
def bottom_toolbar():
    return [("class:toolbar", " Status text")]

# The callable is invoked every refresh
session = PromptSession(bottom_toolbar=bottom_toolbar)
```

**Git Branch Detection:**
- Already implemented in existing code (lines 90-106)
- Uses subprocess with 1s timeout
- Handles errors gracefully
- Works in subdirectories of repo

**Terminal Width Handling:**
- Rich console provides `console.width`
- Calculate padding dynamically
- FormattedText handles overflow automatically
- Tested at 80, 120, 160+ column widths

### Future Enhancements

**Phase 2 Ideas** (not in this spec):
- Token usage tracking (tokens: 1234)
- Cost estimation (cost: $0.05)
- Conversation duration (elapsed: 5m 23s)
- API latency indicator (lag: 234ms)
- Connection status (offline/online indicator)
- Keyboard shortcut to toggle toolbar
- Customizable toolbar format via config
- Multi-line toolbar for rich info
- Progress bars for long operations

**Styling Enhancements:**
- User-configurable colors via .env
- Dark/light theme switching
- Emoji indicators for status
- Nerd font icons for git/directory
- Blinking indicator during thinking

**Platform Support:**
- Windows Terminal testing
- iTerm2 testing
- VSCode integrated terminal testing
- SSH session compatibility
- Tmux pane compatibility

### Dependencies

**No new dependencies required!** ✅

```toml
# Already in pyproject.toml:
prompt-toolkit>=3.0.0    # ✅ Provides bottom_toolbar
rich>=14.1.0             # ✅ Provides FormattedText support
```

### Breaking Changes

**None!** This is a purely additive feature:
- Only affects interactive mode UI
- No API changes
- No command-line flag changes
- No configuration file changes
- Backward compatible with all existing features

### Success Metrics

**Quantitative:**
- Implementation time: < 4 hours
- Lines of code changed: < 50
- Test coverage: 90%+ for new code
- CPU impact: < 1% during refresh
- Memory impact: < 1MB

**Qualitative:**
- Users always know their context
- Professional appearance matches modern CLIs
- No distractions or visual clutter
- Seamless integration with existing UI
- Intuitive and immediately useful

### Comparison to Reference

**GitHub Copilot CLI Pattern:**
```
~/path [⎇ branch]                              model-name
────────────────────────────────────────────────────────
> prompt text here
────────────────────────────────────────────────────────
Ctrl+c Exit · Ctrl+r Expand recent
```

**Our Implementation:**
```
~/path [⎇ branch]                              model-name · version
> prompt text here
```

**Differences:**
- Copilot has separator lines (we integrate with existing design)
- Copilot shows shortcuts at bottom (we have them documented)
- We add version number for clarity
- We support dynamic status updates
- We use FormattedText for better styling

**Alignment:**
- Both show persistent context
- Both use full terminal width
- Both show directory and branch
- Both show model name
- Both stay visible during interaction

## Execution

This spec can be implemented using: `/implement docs/specs/sticky-prompt-bar.md`

### Archon Task Creation

During implementation, create granular Archon tasks:

```python
# Task 1
manage_task(
    "create",
    project_id="58d4551a-1f86-48c9-9653-08f06a8217b0",
    title="Modify status bar text generator to return FormattedText",
    description="Update _get_status_bar_text() function to return FormattedText instead of string. Add styling classes for left/right/padding sections.",
    status="todo",
    task_order=100
)

# Task 2
manage_task(
    "create",
    project_id="58d4551a-1f86-48c9-9653-08f06a8217b0",
    title="Add bottom_toolbar parameter to PromptSession",
    description="Modify PromptSession creation in run_chat_mode() to include bottom_toolbar with callable. Add refresh_interval for dynamic updates.",
    status="todo",
    task_order=90
)

# Task 3 (optional)
manage_task(
    "create",
    project_id="58d4551a-1f86-48c9-9653-08f06a8217b0",
    title="Add StatusState for dynamic status updates",
    description="Create StatusState dataclass to track current operation and message count. Update status during agent execution.",
    status="todo",
    task_order=80
)

# Task 4
manage_task(
    "create",
    project_id="58d4551a-1f86-48c9-9653-08f06a8217b0",
    title="Write unit tests for sticky toolbar",
    description="Create tests/unit/test_cli_toolbar.py with tests for FormattedText generation, directory/branch detection, and StatusState integration.",
    status="todo",
    task_order=70
)

# Task 5
manage_task(
    "create",
    project_id="58d4551a-1f86-48c9-9653-08f06a8217b0",
    title="Update documentation for sticky toolbar feature",
    description="Update README.md, docs/design/usage.md, and ADR-0009 to document the new sticky toolbar feature with examples and usage patterns.",
    status="todo",
    task_order=60
)
```

### Estimated Timeline

**Phase 1 (MVP)**:
- Task 1 (FormattedText): 1 hour
- Task 2 (PromptSession): 30 minutes
- Visual testing: 30 minutes
- **Subtotal**: 2 hours

**Phase 2 (Optional - Dynamic Status)**:
- Task 3 (StatusState): 1 hour
- Integration testing: 30 minutes
- **Subtotal**: 1.5 hours

**Phase 3 (Testing & Docs)**:
- Task 4 (Unit tests): 1 hour
- Task 5 (Documentation): 30 minutes
- Final validation: 30 minutes
- **Subtotal**: 2 hours

**Total**: 4-5.5 hours (depending on whether dynamic status is included)

### Implementation Order

1. ✅ Complete research and spec creation (DONE)
2. 🔨 Implement MVP (Task 1-2)
3. 🧪 Visual testing and validation
4. 📝 Add tests and documentation (Task 4-5)
5. 🎁 Optional: Add dynamic status (Task 3)
6. ✅ Final review and merge

### Next Steps

Ready to implement! Run:
```bash
/implement docs/specs/sticky-prompt-bar.md
```

Or manually execute tasks in order:
1. Modify `_get_status_bar_text()` in `src/agent/cli.py`
2. Add `bottom_toolbar` parameter to `PromptSession`
3. Test in interactive mode
4. Write unit tests
5. Update documentation
6. Optional: Add StatusState for dynamic updates
