"""Unit tests for configuration schema."""

import pytest
from pydantic import ValidationError

from agent.config.schema import (
    AgentSettings,
    AnthropicProviderConfig,
    AzureOpenAIProviderConfig,
    FoundryProviderConfig,
    GeminiProviderConfig,
    GitHubProviderConfig,
    LocalProviderConfig,
    MemoryConfig,
    OpenAIProviderConfig,
    ProviderConfig,
    TelemetryConfig,
)


class TestProviderConfigs:
    """Test individual provider configurations."""

    def test_local_provider_defaults(self):
        """Test local provider has correct defaults."""
        config = LocalProviderConfig()
        # Note: Field default is False; actual enabled state is controlled by
        # ProviderConfig.enabled list through sync_enabled_flags() validator
        assert config.enabled is False
        assert config.base_url == "http://localhost:12434/engines/llama.cpp/v1"
        assert config.model == "ai/phi4"

    def test_openai_provider_defaults(self):
        """Test OpenAI provider has correct defaults."""
        config = OpenAIProviderConfig()
        assert config.enabled is False
        assert config.api_key is None
        assert config.model == "gpt-5-mini"

    def test_anthropic_provider_defaults(self):
        """Test Anthropic provider has correct defaults."""
        config = AnthropicProviderConfig()
        assert config.enabled is False
        assert config.api_key is None
        assert config.model == "claude-haiku-4-5-20251001"

    def test_azure_provider_defaults(self):
        """Test Azure OpenAI provider has correct defaults."""
        config = AzureOpenAIProviderConfig()
        assert config.enabled is False
        assert config.endpoint is None
        assert config.deployment is None
        assert config.api_version == "2025-03-01-preview"
        assert config.api_key is None

    def test_foundry_provider_defaults(self):
        """Test Azure AI Foundry provider has correct defaults."""
        config = FoundryProviderConfig()
        assert config.enabled is False
        assert config.project_endpoint is None
        assert config.model_deployment is None

    def test_gemini_provider_defaults(self):
        """Test Gemini provider has correct defaults."""
        config = GeminiProviderConfig()
        assert config.enabled is False
        assert config.api_key is None
        assert config.model == "gemini-2.0-flash-exp"
        assert config.use_vertexai is False
        assert config.project_id is None
        assert config.location is None

    def test_github_provider_defaults(self):
        """Test GitHub provider has correct defaults."""
        config = GitHubProviderConfig()
        assert config.enabled is False
        assert config.token is None
        assert config.model == "gpt-5-nano"
        assert config.endpoint == "https://models.inference.ai.azure.com"


class TestProviderConfig:
    """Test ProviderConfig model."""

    def test_default_enabled_providers(self):
        """Test default enabled providers is empty (explicit config required)."""
        config = ProviderConfig()
        assert config.enabled == []
        assert config.local.enabled is False
        assert config.openai.enabled is False

    def test_enable_multiple_providers(self):
        """Test enabling multiple providers."""
        config = ProviderConfig(enabled=["local", "openai", "anthropic"])
        assert "local" in config.enabled
        assert "openai" in config.enabled
        assert "anthropic" in config.enabled
        assert config.local.enabled is True
        assert config.openai.enabled is True
        assert config.anthropic.enabled is True
        assert config.azure.enabled is False

    def test_invalid_provider_name_raises_error(self):
        """Test that invalid provider name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ProviderConfig(enabled=["invalid_provider"])
        assert "Invalid provider names" in str(exc_info.value)

    def test_sync_enabled_flags(self):
        """Test that enabled flags sync with enabled list."""
        config = ProviderConfig(enabled=["openai", "gemini"])
        assert config.openai.enabled is True
        assert config.gemini.enabled is True
        assert config.local.enabled is False
        assert config.anthropic.enabled is False


class TestTelemetryConfig:
    """Test TelemetryConfig model."""

    def test_defaults(self):
        """Test telemetry config defaults."""
        config = TelemetryConfig()
        assert config.enabled is False
        assert config.enable_sensitive_data is False
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.applicationinsights_connection_string is None

    def test_custom_values(self):
        """Test setting custom telemetry values."""
        config = TelemetryConfig(
            enabled=True,
            enable_sensitive_data=True,
            otlp_endpoint="http://custom:4318",
            applicationinsights_connection_string="InstrumentationKey=test",
        )
        assert config.enabled is True
        assert config.enable_sensitive_data is True
        assert config.otlp_endpoint == "http://custom:4318"
        assert config.applicationinsights_connection_string == "InstrumentationKey=test"


class TestMemoryConfig:
    """Test MemoryConfig model."""

    def test_defaults(self):
        """Test memory config defaults."""
        config = MemoryConfig()
        assert config.enabled is True
        assert config.type == "in_memory"
        assert config.history_limit == 20
        assert config.mem0.storage_path is None
        assert config.mem0.api_key is None

    def test_invalid_memory_type_raises_error(self):
        """Test that invalid memory type raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryConfig(type="invalid_type")
        assert "Invalid memory type" in str(exc_info.value)

    def test_valid_memory_types(self):
        """Test valid memory types."""
        config1 = MemoryConfig(type="in_memory")
        assert config1.type == "in_memory"

        config2 = MemoryConfig(type="mem0")
        assert config2.type == "mem0"


class TestAgentSettings:
    """Test AgentSettings root model."""

    def test_default_settings(self):
        """Test default agent settings."""
        settings = AgentSettings()
        assert settings.version == "1.0"
        assert (
            settings.providers.enabled == []
        )  # No providers by default (explicit config required)
        assert settings.agent.data_dir.endswith(".agent")
        assert settings.agent.log_level == "info"
        assert settings.telemetry.enabled is False
        assert settings.memory.enabled is True
        assert settings.memory.type == "in_memory"

    def test_custom_settings(self):
        """Test creating custom settings."""
        settings = AgentSettings(
            providers=ProviderConfig(enabled=["openai"]),
            agent={"data_dir": "/custom/path", "log_level": "debug"},
            telemetry={"enabled": True},
            memory={"type": "mem0", "history_limit": 50},
        )
        assert settings.providers.enabled == ["openai"]
        assert "/custom/path" in settings.agent.data_dir
        assert settings.agent.log_level == "debug"
        assert settings.telemetry.enabled is True
        assert settings.memory.type == "mem0"
        assert settings.memory.history_limit == 50

    def test_json_schema_export(self):
        """Test JSON schema export."""
        schema = AgentSettings.get_json_schema()
        assert "properties" in schema
        assert "providers" in schema["properties"]
        assert "agent" in schema["properties"]
        assert "telemetry" in schema["properties"]
        assert "memory" in schema["properties"]

    def test_pretty_json_dump(self):
        """Test pretty JSON dump."""
        settings = AgentSettings()
        json_str = settings.model_dump_json_pretty()
        assert '"version": "1.0"' in json_str
        assert '"local"' in json_str
        # Check it's formatted with newlines and indentation
        assert "\n" in json_str
        assert "  " in json_str

    def test_validate_enabled_providers_all_valid(self):
        """Test validation passes when all enabled providers are configured."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["openai"],
            )
        )
        settings.providers.openai.api_key = "sk-test123"
        errors = settings.validate_enabled_providers()
        assert len(errors) == 0

    def test_validate_enabled_providers_missing_config(self):
        """Test validation fails when enabled provider is missing config."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["openai", "anthropic"],
            )
        )
        # Neither provider has API key
        errors = settings.validate_enabled_providers()
        assert len(errors) == 2
        assert any("OpenAI" in error for error in errors)
        assert any("Anthropic" in error for error in errors)

    def test_validate_azure_provider_requirements(self):
        """Test Azure provider validation requires endpoint and deployment."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["azure"],
            )
        )
        errors = settings.validate_enabled_providers()
        assert len(errors) == 2
        assert any("endpoint" in error for error in errors)
        assert any("deployment" in error for error in errors)

    def test_validate_foundry_provider_requirements(self):
        """Test Foundry provider validation requires project_endpoint and model_deployment."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["foundry"],
            )
        )
        errors = settings.validate_enabled_providers()
        assert len(errors) == 2
        assert any("project_endpoint" in error for error in errors)
        assert any("model_deployment" in error for error in errors)

    def test_validate_gemini_api_key_mode(self):
        """Test Gemini API key mode validation."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["gemini"],
            )
        )
        # API key mode (use_vertexai=False, default)
        errors = settings.validate_enabled_providers()
        assert len(errors) == 1
        assert "api_key" in errors[0]

    def test_validate_gemini_vertexai_mode(self):
        """Test Gemini Vertex AI mode validation."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["gemini"],
            )
        )
        settings.providers.gemini.use_vertexai = True
        # Vertex AI mode requires project_id and location
        errors = settings.validate_enabled_providers()
        assert len(errors) == 2
        assert any("project_id" in error for error in errors)
        assert any("location" in error for error in errors)

    def test_validate_local_provider_always_passes(self):
        """Test local provider validation always passes (no API keys needed)."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["local"],
            )
        )
        errors = settings.validate_enabled_providers()
        assert len(errors) == 0

    def test_validate_github_provider_missing_token(self):
        """Test GitHub provider validation passes even without token.

        GitHub authentication is handled at runtime via get_github_token()
        which checks GITHUB_TOKEN env var or gh CLI, so token is optional in config.
        """
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["github"],
            )
        )
        errors = settings.validate_enabled_providers()
        # No validation errors expected - token fetched at runtime
        assert len(errors) == 0

    def test_validate_github_provider_with_token(self):
        """Test GitHub provider validation passes with token."""
        settings = AgentSettings(
            providers=ProviderConfig(
                enabled=["github"],
            )
        )
        settings.providers.github.token = "ghp_test123"
        errors = settings.validate_enabled_providers()
        assert len(errors) == 0

    def test_github_provider_in_sync_enabled_flags(self):
        """Test GitHub provider enabled flag syncs with enabled list."""
        config = ProviderConfig(enabled=["github", "openai"])
        assert config.github.enabled is True
        assert config.openai.enabled is True
        assert config.local.enabled is False


class TestDataDirExpansion:
    """Test data directory path expansion."""

    def test_data_dir_expands_tilde(self):
        """Test that ~ in data_dir is expanded."""
        settings = AgentSettings(agent={"data_dir": "~/.agent"})
        assert "~" not in settings.agent.data_dir
        assert settings.agent.data_dir.endswith(".agent")

    def test_storage_path_expands_tilde(self):
        """Test that ~ in mem0 storage_path is expanded."""
        settings = AgentSettings(memory={"mem0": {"storage_path": "~/.agent/mem0"}})
        assert "~" not in settings.memory.mem0.storage_path
        assert settings.memory.mem0.storage_path.endswith(".agent/mem0")
