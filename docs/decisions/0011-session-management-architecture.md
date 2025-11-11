---
status: accepted
contact: danielscholl
date: 2025-11-07
deciders: danielscholl
---

# Session Management Architecture

## Context and Problem Statement

Users working on complex tasks need to maintain conversation context across multiple terminal sessions. The agent framework's thread serialization may fail or change across versions. How should we persist conversation state reliably while ensuring sessions remain human-readable and debuggable?

## Decision Drivers

- Thread serialization is framework-dependent and may fail
- Sessions should survive framework version upgrades
- Users need to resume conversations after closing terminal
- Session files should be human-readable for debugging
- Context must be restorable even when full thread deserialization fails
- Security: Prevent path traversal and injection attacks

## Considered Options

1. **Framework-only serialization** - Rely solely on framework's thread.serialize()
2. **JSON-based storage with fallback** - Try framework first, fallback to manual extraction
3. **Database storage** - Use SQLite or similar for session management
4. **Pickle serialization** - Use Python pickle for thread objects

## Decision Outcome

Chosen option: **"JSON-based storage with fallback serialization"**, because:

- **Robust**: Fallback ensures sessions never lost even if framework changes
- **Human-readable**: JSON files can be inspected and debugged
- **Framework-agnostic**: Manual message extraction works across providers
- **Context summaries**: When full deserialization fails, AI gets context via summary
- **Portable**: JSON is standard, no database dependency

### Implementation Details

**Storage Structure:**
```
~/.agent/sessions/
├── index.json              # Metadata index
├── session-1.json          # Individual session
└── session-2.json
```

**Session File Format:**
```json
{
  "name": "session-1",
  "description": "User-provided description",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:45:00",
  "message_count": 12,
  "first_message": "Hello, I need help with...",
  "thread": {
    "messages": [...],
    "metadata": {"fallback": true, "version": "1.0"}
  }
}
```

**Fallback Serialization:**
When `thread.serialize()` fails:
1. Extract messages from `thread.message_store.list_messages()`
2. Convert to JSON-serializable dict format
3. Mark with `"fallback": true` metadata
4. Generate context summary for AI restoration

**Context Summary Generation:**
Provides AI with concise history:
- User requests (up to 5, truncated to 200 chars)
- Tools used (deduplicated list)
- Total message count
- Instruction to continue conversation

**Security:**
- Name sanitization prevents path traversal (`../`, `..`)
- Character whitelist: `[A-Za-z0-9._-]`
- Length limits: 1-64 characters
- Reserved name blocking: `index`, `metadata`, OS reserved names

### Consequences

**Positive:**
- Sessions never lost due to framework changes
- Human-readable for debugging and inspection
- Works across all LLM providers
- Context restoration via summaries when needed
- Secure against path traversal attacks

**Negative:**
- Fallback mode loses full thread state (tools, intermediate results)
- Context summaries are approximate, not exact restoration
- Disk space usage (JSON is verbose)

**Neutral:**
- Requires manual message extraction logic
- Session files stored in user home directory

## Related Decisions

- [ADR-0010](0010-display-output-format.md) - Display system complements session management
- [ADR-0012](0012-middleware-integration-strategy.md) - Middleware tracks execution that gets persisted
