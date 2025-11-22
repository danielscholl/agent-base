---
status: accepted
contact: danielscholl
date: 2025-11-21
deciders: danielscholl
---

# Legacy Configuration System Deprecation Plan

## Context and Problem Statement

Agent-base currently maintains two configuration systems in parallel:

1. **Legacy System** (`config/legacy.py`, 645 lines):
   - Dataclass-based `AgentConfig`
   - Environment variable parsing with `.env` support
   - Direct instantiation from environment
   - Used by 16 files across the codebase

2. **New System** (`config/schema.py`, 424 lines):
   - Pydantic-based `AgentSettings` models
   - JSON file-based persistence (`~/.agent/settings.json`)
   - Progressive disclosure with minimal JSON export
   - Better validation and type safety

Both systems contain similar validation logic and provider configurations, creating maintenance burden and risk of inconsistency. How should we deprecate the legacy system for 2.0.0 while maintaining backward compatibility during 1.x releases?

## Decision Drivers

- **Maintenance Burden**: Duplicate validation logic across two systems
- **Type Safety**: Pydantic provides better runtime validation
- **User Experience**: JSON config file is more user-friendly than environment variables
- **Backward Compatibility**: Many existing deployments use legacy system
- **Migration Path**: Users need clear guidance for transition
- **Testing**: Dual systems complicate test coverage

## Considered Options

1. **Gradual Deprecation with Warnings (v1.x → v2.0)** - Add warnings in 1.x, remove in 2.0
2. **Hard Cutover in 2.0** - Remove immediately with migration script
3. **Maintain Both Indefinitely** - Keep supporting both systems
4. **Bridge Layer** - Auto-convert legacy config to new format at runtime

## Decision Outcome

Chosen option: **"Gradual Deprecation with Warnings (v1.x → v2.0)"**, because it:

- Provides clear migration path for users
- Allows testing and feedback during transition period
- Maintains backward compatibility during 1.x lifecycle
- Reduces risk of breaking existing deployments
- Enables phased removal of legacy code

### Migration Timeline

**Phase 1: 1.0.0 - Status Quo**
- Both systems coexist
- No warnings or deprecation notices
- Current state maintained for stable 1.0 release

**Phase 2: 1.1.0 - Deprecation Warnings**
- Add deprecation warnings to `AgentConfig.from_env()`
- Log warning when legacy config is detected:
  ```python
  logger.warning(
      "Legacy configuration (AgentConfig) is deprecated and will be removed in 2.0.0. "
      "Please migrate to settings.json using: agent config init"
  )
  ```
- Update documentation to recommend new system
- Add migration guide to docs/design/usage.md

**Phase 3: 1.2.0 - Migration Tooling**
- Add `agent config migrate` command
- Reads legacy environment variables
- Generates `settings.json` with equivalent configuration
- Validates new config matches legacy behavior
- Provides diff/preview before committing

**Phase 4: 2.0.0 - Legacy Removal**
- Remove `config/legacy.py` entirely
- Update all imports to use new system
- Remove legacy tests
- Update all documentation

### Migration Command Design

```python
# agent config migrate
# Reads .env and current environment
# Generates settings.json

$ agent config migrate
Reading legacy configuration...
  ✓ LLM_PROVIDER=openai
  ✓ OPENAI_API_KEY=sk-***
  ✓ AGENT_MODEL=gpt-5-mini

Generating settings.json...
  ✓ providers.enabled: ["openai"]
  ✓ providers.openai.api_key: ******
  ✓ providers.openai.model: gpt-5-mini

Preview (settings.json):
{
  "version": "1.0",
  "providers": {
    "enabled": ["openai"],
    "openai": {
      "api_key": "sk-***",
      "model": "gpt-5-mini"
    }
  }
}

Write to ~/.agent/settings.json? [Y/n]:
```

### Implementation Steps

**1.1.0 Release:**
- Add deprecation warning to `AgentConfig.__init__`
- Add deprecation notice to legacy docstrings
- Create migration guide in docs/
- Update CHANGELOG.md with deprecation timeline

**1.2.0 Release:**
- Implement `agent config migrate` command
- Add tests for migration logic
- Update CLI help with migration instructions
- Add examples to migration guide

**2.0.0 Release:**
- Remove `config/legacy.py`
- Remove legacy imports from all files
- Remove legacy-specific tests
- Update architecture documentation
- Add breaking changes section to CHANGELOG.md

### Backward Compatibility Strategy

During 1.x releases:
- Both systems fully functional
- No forced migration
- Clear opt-in path to new system
- Legacy system still documented (with deprecation notice)

### Communication Plan

**Documentation Updates:**
- Add prominent deprecation notice to README.md (starting 1.1.0)
- Create detailed migration guide
- Update CONTRIBUTING.md with new config patterns
- Add ADR explaining rationale (this document)

**User Communication:**
- Release notes for each phase
- Blog post explaining migration (if applicable)
- Example migration scenarios in docs
- FAQ section addressing common concerns

## Consequences

### Positive

- **Reduced Maintenance**: Single configuration system to maintain
- **Better UX**: JSON config file is more intuitive than environment variables
- **Type Safety**: Pydantic validation catches errors early
- **Progressive Disclosure**: Minimal JSON export improves readability
- **Clear Migration Path**: Users have 3+ releases to migrate

### Negative

- **Temporary Complexity**: Maintaining both systems during transition
- **Migration Effort**: Users must update their deployments
- **Documentation Burden**: Need to maintain migration guides
- **Breaking Change**: 2.0.0 removes legacy system entirely

### Neutral

- **Test Coverage**: Can gradually remove legacy tests as users migrate
- **Code Churn**: Multiple PRs across several releases

## Implementation Notes

### Files to Update (1.1.0)

1. `src/agent/config/legacy.py`:
   - Add deprecation warning to `__init__` and `from_env()`
   - Add docstring notice about deprecation

2. `docs/MIGRATION_GUIDE.md`:
   - Create comprehensive migration guide
   - Include examples for common scenarios
   - Document command line migration tool

3. `CHANGELOG.md`:
   - Add deprecation notice
   - Link to migration guide
   - Include timeline

### Files to Update (1.2.0)

1. `src/agent/cli/config_commands.py`:
   - Add `migrate` subcommand
   - Implement legacy-to-new conversion
   - Add validation and preview

2. `tests/unit/cli/test_config_migrate.py`:
   - Test migration command
   - Test edge cases (missing values, invalid config)
   - Test preview functionality

### Files to Remove (2.0.0)

1. `src/agent/config/legacy.py` (entire file)
2. All legacy-specific tests
3. Migration command (no longer needed after cutover)
4. Migration guide (replace with "Upgrading from 1.x" guide)

## References

- [ADR-0001](0001-module-and-package-naming-conventions.md) - Naming conventions
- [Progressive Disclosure Pattern](https://en.wikipedia.org/wiki/Progressive_disclosure)
- Current configuration files:
  - `src/agent/config/legacy.py` (645 lines)
  - `src/agent/config/schema.py` (424 lines)
  - `src/agent/config/defaults.py` (118 lines)
  - `src/agent/config/manager.py` (config file I/O)

## Status

**Proposed for 1.1.0+**

This ADR documents the plan for future releases. Implementation will begin with 1.1.0 deprecation warnings and complete with 2.0.0 removal.

## Related Changes (1.0.0)

As part of 1.0.0 preparation, `.env.example` was removed from the repository in favor of comprehensive configuration documentation in `docs/design/config.md`. This aligns with the vision of settings.json as the primary configuration method, with environment variables documented for CI/CD use cases rather than promoted via an example file.

---

## Implementation Status

**Status:** ✅ **IMPLEMENTED in v0.3.0**

**Implementation Date:** November 21, 2025

**Decision:** The originally proposed gradual deprecation timeline was revised. Instead of waiting for 1.1.0 and 2.0.0, the legacy system was removed in v0.3.0 during the alpha phase, avoiding the need for deprecation warnings in production releases.

### Phase 4 Execution Summary

**What Was Removed:**
- `src/agent/config/legacy.py` (645 lines) - Entire legacy configuration module
- `AgentConfig` class and all factory methods (`from_env()`, `from_file()`, `from_combined()`)
- 32 test files updated to use new `AgentSettings` API
- Legacy configuration imports across 48 files

**What Was Migrated:**
- All production code now uses `AgentSettings` from `config/schema.py`
- Configuration loading consolidated to `load_config()` function
- Test fixtures rewritten to use `AgentSettings` patterns
- All 966 tests passing with 86% coverage maintained

**What Was Preserved:**
- Environment variable support fully maintained via `merge_with_env()` function
- All documented environment variables continue to work
- Backward compatibility for environment-only deployments (CI/CD)
- Hybrid mode (settings.json + env overrides) fully functional

### Migration Path

Users upgrading from v0.2.x to v0.3.0+:

**For Environment-Only Users (CI/CD):**
- ✅ **No changes needed** - Environment variables still work
- All `LLM_PROVIDER`, `OPENAI_API_KEY`, etc. continue to function
- `load_config()` automatically merges environment overrides

**For settings.json Users:**
- ✅ **No changes needed** - JSON configuration works as before
- Environment variables can still override settings.json values

**For Direct `AgentConfig` Importers:**
- ⚠️ **Code changes required**
- Change: `from agent.config import AgentConfig` → `from agent.config import AgentSettings, load_config`
- Change: `AgentConfig.from_combined()` → `load_config()`
- Change: `config.openai_api_key` → `settings.providers.openai.api_key`

### Breaking Changes (v0.3.0)

**Removed:**
- `AgentConfig` class
- `AgentConfig.from_env()` method
- `AgentConfig.from_file()` method
- `AgentConfig.from_combined()` method
- `config/legacy.py` module

**Added:**
- `load_config()` function as single entry point
- `AgentSettings` as unified configuration model
- `migrate_from_env()` helper for environment-only setups

See CHANGELOG v0.3.0 for complete breaking change documentation.

### Implementation Evidence

**Pull Request:** Configuration migration completed in PR #72
**Commits:** 15 systematic commits showing incremental migration
**Tests:** All 966 tests passing (838 free, 30 LLM opt-in)
**Coverage:** 86% maintained (exceeds 85% requirement)
**Files Changed:** 48 production files, 32 test files
**Documentation:** README, CONTRIBUTING, config.md all updated

### Lessons Learned

**What Worked Well:**
1. **Alpha Phase Execution** - Removing legacy system during alpha (v0.3.0) avoided deprecation complexity in production releases
2. **Comprehensive Testing** - 966 tests caught all regressions during migration
3. **Environment Variable Preservation** - Maintaining env var support prevented deployment disruptions
4. **Systematic Commits** - 15 focused commits enabled easy rollback if needed
5. **Specification-Driven** - Detailed spec (`docs/specs/legacy-config-removal.md`) provided clear roadmap

**What Could Be Improved:**
1. **ADR Timing** - This ADR was created after implementation decision was made (should precede implementation)
2. **Migration Communication** - Could have provided example migration scripts for direct importers

**Recommendation for Future Breaking Changes:**
- Execute major breaking changes during alpha phase when possible
- Maintain comprehensive test coverage throughout migration
- Document every step in CHANGELOG with migration paths
- Preserve backward compatibility at deployment boundaries (env vars, CLI)
