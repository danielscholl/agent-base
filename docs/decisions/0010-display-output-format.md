---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Display Output Format and Verbosity Levels

## Context and Problem Statement

Agent execution involves multiple LLM calls and tool executions that happen in sequence. Users need visibility into what the agent is doing, but a flat stream of events becomes overwhelming and difficult to follow. How should we present execution information to provide useful feedback without creating noise?

## Decision Drivers

- Users need to see progress during long-running operations
- Flat event streams are hard to follow and create visual clutter
- Different contexts require different verbosity levels (debugging vs production)
- Display should work in both interactive and single-query CLI modes
- Real-time updates should be smooth without excessive CPU usage

## Considered Options

1. **Flat event stream** - Display each event (LLM call, tool call) as it happens
2. **Phase-based grouping** - Group LLM thinking + resulting tool calls into logical phases
3. **Streaming-only output** - Only show LLM response text, hide all execution details
4. **No visualization** - Rely on logs for debugging, show only final output

## Decision Outcome

Chosen option: **"Phase-based grouping with MINIMAL/VERBOSE modes"**, because:

- **Reduces noise**: Groups related operations (reasoning + actions) into coherent phases
- **User-configurable**: MINIMAL mode for clean output, VERBOSE mode for debugging
- **Focuses attention**: Shows only active work in MINIMAL mode, completed phases collapse
- **Matches mental model**: Users think in terms of "the agent thought, then did X" not individual events
- **Proven pattern**: Butler-agent successfully uses this approach in production

### Implementation Details

**Display Modes:**
- `MINIMAL` (default): Show only active phase with current work
  - Example: `● working... (msg:3 tool:2)`
  - Clean, minimal visual footprint

- `VERBOSE`: Show all phases with full timing and details
  - Example: `• Phase 1: hello_world (1.2s)`
  - Useful for debugging and understanding execution flow

**Refresh Rate:**
- 5Hz (200ms) provides smooth updates without excessive CPU
- Rich Live display handles rendering efficiently

**Phase Structure:**
```
Phase N: [Tool Name]
  ● Thinking (3 messages)
  → tool_name (arg_value) - Summary (0.5s)
```

### Consequences

**Positive:**
- Dramatically reduces visual noise compared to flat event streams
- Users can quickly understand current execution state
- Mode switching allows same code to serve different needs
- Collapsible phases keep focus on active work

**Negative:**
- Slightly more complex than flat event display
- Requires event correlation via event_id
- Phase detection logic adds code complexity

**Neutral:**
- Requires Rich library (already a dependency)
- 5Hz refresh rate may need tuning for different terminals

## Related Decisions

- [ADR-0005](0005-event-bus-pattern-for-loose-coupling.md) - Event bus provides foundation for display
- [ADR-0009](0009-cli-framework-selection.md) - Rich framework enables tree display
- [ADR-0012](0012-middleware-integration-strategy.md) - Middleware emits events for display
