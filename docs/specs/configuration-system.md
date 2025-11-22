# Feature: File-Based Configuration System

> **Historical Note:** This specification was written for v0.2.x development. As of v0.3.0, the legacy `AgentConfig` system referenced in this spec has been removed. All examples showing `AgentConfig.from_env()` or similar methods should now use `AgentSettings` and `load_config()` from the modern configuration system. This spec is preserved for historical reference and to document the design decisions that led to the current implementation.

## Feature Description

Replace the current environment variable-based configuration with a modern file-based configuration system using JSON files stored in `~/.agent/settings.json`. This new system will provide:

- **Explicit Provider Management**: Enable/disable LLM providers explicitly rather than relying on environment variable detection
- **Interactive Configuration**: CLI commands to guide users through setup with validation and helpful prompts
- **Better User Experience**: Reduce complexity of `.env` files and improve discoverability of features
- **Default Settings**: Docker provider enabled by default as it's free and requires no API keys
- **Editor Integration**: Open configuration files directly in VSCode or default editor
- **Backward Compatibility**: Continue supporting environment variables as overrides

## User Story

As a **developer using the agent-base framework**
I want to **manage configuration through an intuitive file-based system with CLI helpers**
So that **I can easily discover capabilities, enable/disable features, and avoid complex .env file management**

## Problem Statement

The current environment variable-based configuration system has several pain points:

1. **Discoverability**: Users must read documentation or `.env.example` to understand available features
2. **Complexity**: Managing many environment variables is error-prone and tedious
3. **Provider Confusion**: All providers show up in `--check` even if not intended for use
4. **No Guidance**: Users get validation errors but no help on what values are needed
5. **Poor Ergonomics**: Editing `.env` files manually is not industry standard for modern CLI tools
6. **No State Management**: Can't easily track which features are intentionally enabled vs accidentally configured

## Solution Statement

Implement a JSON-based configuration system with interactive CLI commands that:

1. **Stores configuration** in `~/.agent/settings.json` with clear structure
2. **Provides CLI helpers** like `agent config init`, `agent config edit`, `agent config enable provider azure`
3. **Offers interactive prompts** that guide users through setting required values
4. **Validates configuration** and provides actionable error messages
5. **Opens in editor** for advanced users who prefer direct editing
6. **Maintains env var support** for CI/CD and backward compatibility (env vars override config file)
7. **Filters `--check` output** to only show enabled providers

## Relevant Files

### Existing Files

- **src/agent/config.py** - Current configuration class using environment variables; needs major refactor to support JSON file loading
- **src/agent/cli/app.py** - CLI entry point; needs new config-related commands and flags
- **src/agent/cli/commands.py** - Command handlers; needs new config command handlers
- **src/agent/agent.py** - Agent initialization; needs to use new config system
- **README.md** - Documentation; needs updates to reflect new config approach
- **.env.example** - Environment variable reference; can be simplified or deprecated

### New Files

- **src/agent/config/manager.py** - Configuration file manager (load, save, validate JSON)
- **src/agent/config/schema.py** - Pydantic models for configuration schema validation
- **src/agent/config/defaults.py** - Default configuration values
- **src/agent/cli/config_commands.py** - Interactive config CLI commands (init, edit, enable, disable, show)
- **src/agent/config/editor.py** - Editor integration utilities (open VSCode/default editor)
- **tests/unit/config/test_manager.py** - Unit tests for config manager
- **tests/unit/config/test_schema.py** - Unit tests for config schema
- **tests/integration/test_config_migration.py** - Integration tests for env var migration

## Implementation Plan

### Phase 1: Foundation

**Goal**: Create the configuration infrastructure without breaking existing functionality

1. **Define Configuration Schema**
   - Create Pydantic models for settings structure
   - Define provider configuration schema
   - Define telemetry and memory configuration
   - Support nested configuration (providers, telemetry, memory)

2. **Implement Configuration Manager**
   - Load JSON from `~/.agent/settings.json`
   - Save JSON with pretty formatting
   - Merge with environment variable overrides
   - Migration utility from env vars to JSON
   - Validation with helpful error messages

3. **Extend AgentConfig Class**
   - Add `from_file()` class method
   - Add `from_combined()` to merge file + env vars
   - Keep `from_env()` for backward compatibility
   - Add provider enable/disable flags

### Phase 2: Core Implementation

**Goal**: Implement CLI commands for managing configuration

1. **CLI Command Structure**
   - `agent config init` - Interactive first-time setup
   - `agent config show` - Display current configuration
   - `agent config edit` - Open in editor
   - `agent config enable <feature>` - Enable provider/feature
   - `agent config disable <feature>` - Disable provider/feature
   - `agent config set <key> <value>` - Set specific value
   - `agent config validate` - Validate configuration

2. **Interactive Setup Flow**
   - Detect if settings.json exists
   - Guide through provider selection
   - Prompt for required credentials
   - Validate inputs in real-time
   - Save with sensible defaults

3. **Provider Management**
   - Enable/disable individual providers
   - Show required configuration for each
   - Validate provider-specific settings
   - Update `--check` to filter by enabled providers

### Phase 3: Integration

**Goal**: Integrate configuration system throughout the application

1. **Update Agent Initialization**
   - Use `AgentConfig.from_combined()` as default
   - Environment variables override file settings
   - Clear precedence documentation

2. **Update `--check` Command**
   - Only test enabled providers
   - Show configuration source (file vs env)
   - Display warnings for partially configured providers

3. **Editor Integration**
   - Detect VSCode, vim, nano, default editor
   - Open settings.json with `agent config edit`
   - Validate after editor closes
   - Handle editor errors gracefully

4. **Documentation Updates**
   - Update README.md with new workflow
   - Add configuration guide
   - Document migration path from env vars
   - Update all examples

## Step by Step Tasks

### Step 1: Create Configuration Schema

- Define Pydantic models in `src/agent/config/schema.py`
- Create `ProviderConfig` model for each provider type
- Create `TelemetryConfig` model for OTEL settings
- Create `MemoryConfig` model for memory backends
- Create root `AgentSettings` model
- Add JSON schema export for documentation
- Write unit tests for schema validation

### Step 2: Implement Configuration Manager

- Create `src/agent/config/manager.py`
- Implement `load_config()` - load from JSON file
- Implement `save_config()` - save to JSON with formatting
- Implement `merge_with_env()` - merge file with env vars
- Implement `validate_config()` - comprehensive validation
- Implement `migrate_from_env()` - create settings.json from .env
- Write unit tests for manager functions

### Step 3: Create Default Configuration

- Create `src/agent/config/defaults.py`
- Define default settings (Docker provider enabled)
- Define default paths and directories
- Define default telemetry settings (disabled by default)
- Define default memory settings (in_memory)
- Export `get_default_config()` function

### Step 4: Refactor AgentConfig Class

- Update `src/agent/config.py`
- Add `from_file()` class method
- Add `from_combined()` class method (file + env vars)
- Add `enabled_providers: list[str]` field
- Update `validate()` to check enabled providers only
- Maintain backward compatibility with `from_env()`
- Add `get_config_source()` method (returns "file", "env", or "combined")

### Step 5: Create CLI Config Commands

- Create `src/agent/cli/config_commands.py`
- Implement `config_init()` - interactive setup wizard
- Implement `config_show()` - display current config
- Implement `config_enable()` - enable provider/feature
- Implement `config_disable()` - disable provider/feature
- Implement `config_set()` - set specific value
- Implement `config_validate()` - validate and show errors
- Use rich prompts for interactive input

### Step 6: Add Editor Integration

- Create `src/agent/config/editor.py`
- Implement `detect_editor()` - find VSCode, vim, nano, etc.
- Implement `open_in_editor()` - open file in detected editor
- Implement `wait_for_editor()` - wait for editor to close
- Implement validation after editor closes
- Handle missing editor gracefully

### Step 7: Wire CLI Commands

- Update `src/agent/cli/app.py`
- Add `--config` flag (show config)
- Add `config` command group
- Wire all config subcommands
- Add autocomplete for config commands
- Update help text

### Step 8: Update Agent Initialization

- Update `src/agent/agent.py`
- Change default to use `AgentConfig.from_combined()`
- Document precedence (CLI args > env vars > config file > defaults)
- Ensure backward compatibility

### Step 9: Update Health Check Command

- Update `run_health_check()` in `src/agent/cli/app.py`
- Filter providers by `enabled_providers` list
- Show config source indicator (📄 file, 🔧 env, 🔗 combined)
- Show disabled providers with dim styling
- Add "Run `agent config enable <provider>` to enable" hints

### Step 10: Create Migration Utility

- Add `agent config migrate` command
- Read existing .env file
- Convert to settings.json format
- Backup .env as .env.backup
- Prompt user to verify migration
- Test migration thoroughly

### Step 11: Write Comprehensive Tests

- Unit tests for schema validation
- Unit tests for config manager
- Unit tests for CLI config commands
- Integration test for config migration
- Integration test for env var override
- Integration test for provider enable/disable
- Test editor integration (mock editor)

### Step 12: Update Documentation

- Update README.md Quick Setup section
- Add "Configuration Guide" section
- Document all `agent config` commands
- Add migration guide from env vars
- Update examples throughout docs
- Add troubleshooting section

### Step 13: Run Validation Commands

- Execute all validation commands to ensure feature works with zero regressions
- Verify backward compatibility with env vars

## Testing Strategy

### Unit Tests

1. **Schema Validation Tests** (`tests/unit/config/test_schema.py`)
   - Valid configuration passes validation
   - Invalid configurations fail with clear errors
   - Default values are populated correctly
   - Nested configuration validates properly

2. **Config Manager Tests** (`tests/unit/config/test_manager.py`)
   - Load non-existent file returns defaults
   - Load valid JSON succeeds
   - Load invalid JSON fails gracefully
   - Save creates formatted JSON
   - Merge with env vars applies overrides correctly
   - Migration from env creates correct JSON

3. **CLI Command Tests** (`tests/unit/cli/test_config_commands.py`)
   - Config init creates valid settings.json
   - Config show displays correct values
   - Config enable adds provider to enabled list
   - Config disable removes provider
   - Config set updates specific value
   - Config validate catches errors

### Integration Tests

1. **End-to-End Configuration Flow** (`tests/integration/test_config_e2e.py`)
   - Fresh install → config init → agent runs successfully
   - Enable Azure provider → set required values → provider works
   - Disable provider → --check doesn't test it
   - Env var override works correctly

2. **Migration Tests** (`tests/integration/test_config_migration.py`)
   - Migrate from .env with all providers configured
   - Migrate from minimal .env (only one provider)
   - Migrated config works identically to env config
   - After migration, env vars still override

3. **Backward Compatibility Tests** (`tests/integration/test_backward_compat.py`)
   - Agent works with only .env (no settings.json)
   - Agent works with only settings.json (no .env)
   - Agent works with both (env overrides file)
   - CLI args override both

### Edge Cases

1. **Corrupted settings.json** - Falls back to env vars or defaults with warning
2. **Partial configuration** - Validation clearly indicates missing required values
3. **Permission errors** - Graceful handling if can't write to ~/.agent
4. **Concurrent edits** - Handle if settings.json modified while agent running
5. **Missing editor** - Provide helpful message if editor not found
6. **Provider compatibility** - mem0 doesn't work with local/foundry providers
7. **Empty enabled_providers list** - Default to "local" provider

## Acceptance Criteria

### Core Functionality
- [ ] `agent config init` creates valid settings.json with guided prompts
- [ ] `agent config show` displays current configuration clearly
- [ ] `agent config edit` opens settings.json in appropriate editor
- [ ] `agent config enable provider <name>` enables provider and prompts for required values
- [ ] `agent config disable provider <name>` disables provider
- [ ] Disabled providers don't appear in `agent --check` output
- [ ] Docker/local provider is enabled by default

### Configuration Management
- [ ] Settings stored in `~/.agent/settings.json` with clear structure
- [ ] Environment variables override file settings (documented precedence)
- [ ] CLI arguments override both env vars and file settings
- [ ] Invalid configuration provides actionable error messages
- [ ] `agent config validate` checks configuration without running agent

### User Experience
- [ ] Interactive prompts guide user through setup
- [ ] Required values are clearly indicated
- [ ] Helpful hints when enabling features (e.g., "Get Azure credentials from...")
- [ ] Configuration changes take effect immediately (no restart needed)
- [ ] Clear documentation of all config commands

### Backward Compatibility
- [ ] Existing .env-based configurations continue to work
- [ ] Migration command successfully converts .env to settings.json
- [ ] No breaking changes to public API
- [ ] Tests pass for both config methods

### Quality
- [ ] All unit tests pass (>90% coverage for new code)
- [ ] All integration tests pass
- [ ] Documentation is complete and accurate
- [ ] Code follows project conventions

## Validation Commands

Execute every command to validate the feature works correctly with zero regressions.

```bash
# Test schema and config manager
cd agent-base && uv run pytest tests/unit/config/ -v

# Test CLI config commands
cd agent-base && uv run pytest tests/unit/cli/test_config_commands.py -v

# Test integration scenarios
cd agent-base && uv run pytest tests/integration/test_config_e2e.py -v
cd agent-base && uv run pytest tests/integration/test_config_migration.py -v
cd agent-base && uv run pytest tests/integration/test_backward_compat.py -v

# Run all tests to ensure no regressions
cd agent-base && uv run pytest -v

# Manual validation: Interactive config setup
agent config init
# Follow prompts to set up OpenAI provider
# Verify settings.json created correctly

# Manual validation: Config commands
agent config show
agent config enable provider azure
# Follow prompts to enter Azure credentials
agent config show
# Verify Azure provider is now enabled

agent --check
# Verify only enabled providers appear

agent config disable provider azure
agent --check
# Verify Azure provider no longer appears

# Manual validation: Editor integration
agent config edit
# Verify settings.json opens in correct editor
# Make a change and save
agent config validate
# Verify validation runs correctly

# Manual validation: Environment variable override
export OPENAI_API_KEY="test-override-key"
agent config show
# Verify shows override indicator

# Manual validation: Migration
# Create a test .env file
cat > test.env << EOF
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-test123
ENABLE_OTEL=true
MEMORY_TYPE=mem0
EOF

# Run migration
agent config migrate --env-file test.env
# Verify settings.json created correctly

# Manual validation: Backward compatibility
rm ~/.agent/settings.json
agent --check
# Verify works with only .env file

# Manual validation: Single prompt mode
agent -p "Hello" --provider local
agent -p "Hello" --provider openai

# Manual validation: Interactive mode
agent
# Test various commands
# Verify configuration is respected
```

## Notes

### Configuration File Structure

Example `~/.agent/settings.json`:

```json
{
  "version": "1.0",
  "providers": {
    "enabled": ["local"],
    "local": {
      "base_url": "http://localhost:12434/engines/llama.cpp/v1",
      "model": "ai/phi4"
    },
    "openai": {
      "enabled": false,
      "api_key": null,
      "model": "gpt-5-mini"
    },
    "anthropic": {
      "enabled": false,
      "api_key": null,
      "model": "claude-haiku-4-5-20251001"
    },
    "azure": {
      "enabled": false,
      "endpoint": null,
      "deployment": null,
      "api_version": "2025-03-01-preview",
      "api_key": null
    },
    "foundry": {
      "enabled": false,
      "project_endpoint": null,
      "model_deployment": null
    },
    "gemini": {
      "enabled": false,
      "api_key": null,
      "model": "gemini-2.0-flash-exp",
      "use_vertexai": false,
      "project_id": null,
      "location": null
    }
  },
  "agent": {
    "data_dir": "~/.agent",
    "log_level": "info"
  },
  "telemetry": {
    "enabled": false,
    "enable_sensitive_data": false,
    "otlp_endpoint": "http://localhost:4317",
    "applicationinsights_connection_string": null
  },
  "memory": {
    "enabled": true,
    "type": "in_memory",
    "history_limit": 20,
    "mem0": {
      "storage_path": null,
      "api_key": null,
      "org_id": null,
      "user_id": null,
      "project_id": null
    }
  }
}
```

### Configuration Precedence

1. **CLI Arguments** (highest priority) - `--provider openai --model gpt-4o`
2. **Environment Variables** - `export OPENAI_API_KEY=...`
3. **Configuration File** - `~/.agent/settings.json`
4. **Defaults** (lowest priority) - Hardcoded defaults

### Migration Strategy

- Keep environment variable support indefinitely for CI/CD and Docker deployments
- Recommend file-based config for local development
- Provide clear migration path with `agent config migrate` command
- Update documentation to show file-based config as primary method
- .env.example can remain as reference but point users to `agent config init`

### Future Enhancements

- **Profiles**: Support multiple configuration profiles (`--profile production`)
- **Import/Export**: Export config for sharing, import from others
- **Validation Hooks**: Custom validation for provider-specific requirements
- **Config Templates**: Pre-built templates for common scenarios
- **Cloud Sync**: Sync settings across machines (optional)
- **Secrets Management**: Integration with system keychain for API keys

### Dependencies

New dependencies needed:
- `pydantic>=2.0` (already in project for validation)
- No additional dependencies required (use stdlib for JSON and editor detection)

### Breaking Changes

None - this feature is fully backward compatible. Environment variables continue to work exactly as before.
