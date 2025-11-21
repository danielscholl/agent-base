"""Pydantic models for agent configuration schema."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from agent.config.constants import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_AZURE_API_VERSION,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GITHUB_ENDPOINT,
    DEFAULT_GITHUB_MODEL,
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_LOCAL_MODEL,
    DEFAULT_OPENAI_MODEL,
)

# Module-level constants for validation
VALID_PROVIDERS = {"local", "openai", "anthropic", "azure", "foundry", "gemini", "github"}
VALID_MEMORY_TYPES = {"in_memory", "mem0"}


class LocalProviderConfig(BaseModel):
    """Local provider configuration (Docker Desktop Model Runner)."""

    enabled: bool = False  # NOTE: Overwritten by sync_enabled_flags() validator.
    # Actual enabled state is determined by ProviderConfig.enabled list.
    base_url: str = DEFAULT_LOCAL_BASE_URL
    model: str = DEFAULT_LOCAL_MODEL


class OpenAIProviderConfig(BaseModel):
    """OpenAI provider configuration."""

    enabled: bool = False
    api_key: str | None = None
    model: str = DEFAULT_OPENAI_MODEL


class AnthropicProviderConfig(BaseModel):
    """Anthropic provider configuration."""

    enabled: bool = False
    api_key: str | None = None
    model: str = DEFAULT_ANTHROPIC_MODEL


class AzureOpenAIProviderConfig(BaseModel):
    """Azure OpenAI provider configuration."""

    enabled: bool = False
    endpoint: str | None = None
    deployment: str | None = None
    api_version: str = DEFAULT_AZURE_API_VERSION
    api_key: str | None = None


class FoundryProviderConfig(BaseModel):
    """Azure AI Foundry provider configuration."""

    enabled: bool = False
    project_endpoint: str | None = None
    model_deployment: str | None = None


class GeminiProviderConfig(BaseModel):
    """Google Gemini provider configuration."""

    enabled: bool = False
    api_key: str | None = None
    model: str = DEFAULT_GEMINI_MODEL
    use_vertexai: bool = False
    project_id: str | None = None
    location: str | None = None


class GitHubProviderConfig(BaseModel):
    """GitHub Models provider configuration."""

    enabled: bool = False
    token: str | None = None
    model: str = DEFAULT_GITHUB_MODEL
    endpoint: str = DEFAULT_GITHUB_ENDPOINT
    org: str | None = None  # Optional: org name for enterprise rate limits


class ProviderConfig(BaseModel):
    """Provider configurations."""

    enabled: list[str] = Field(default_factory=list)  # Empty by default - requires explicit config
    local: LocalProviderConfig = Field(default_factory=LocalProviderConfig)
    openai: OpenAIProviderConfig = Field(default_factory=OpenAIProviderConfig)
    anthropic: AnthropicProviderConfig = Field(default_factory=AnthropicProviderConfig)
    azure: AzureOpenAIProviderConfig = Field(default_factory=AzureOpenAIProviderConfig)
    foundry: FoundryProviderConfig = Field(default_factory=FoundryProviderConfig)
    gemini: GeminiProviderConfig = Field(default_factory=GeminiProviderConfig)
    github: GitHubProviderConfig = Field(default_factory=GitHubProviderConfig)

    @field_validator("enabled")
    @classmethod
    def validate_enabled_providers(cls, v: list[str]) -> list[str]:
        """Validate that enabled providers list contains valid provider names."""
        invalid = set(v) - VALID_PROVIDERS
        if invalid:
            raise ValueError(
                f"Invalid provider names in enabled list: {invalid}. "
                f"Valid providers: {VALID_PROVIDERS}"
            )
        return v

    @model_validator(mode="after")
    def sync_enabled_flags(self) -> "ProviderConfig":
        """Sync enabled list with individual provider enabled flags."""
        # Update individual provider enabled flags based on enabled list
        self.local.enabled = "local" in self.enabled
        self.openai.enabled = "openai" in self.enabled
        self.anthropic.enabled = "anthropic" in self.enabled
        self.azure.enabled = "azure" in self.enabled
        self.foundry.enabled = "foundry" in self.enabled
        self.gemini.enabled = "gemini" in self.enabled
        self.github.enabled = "github" in self.enabled
        return self


class PluginSkillSource(BaseModel):
    """Git-based plugin skill source configuration."""

    name: str = Field(description="Canonical skill name")
    git_url: str = Field(description="Git repository URL")
    branch: str = Field(default="main", description="Git branch to use")
    enabled: bool = Field(default=True, description="Enable/disable this plugin skill")
    installed_path: str | None = Field(
        default=None, description="Installation path (auto-populated by skill manager)"
    )

    @field_validator("installed_path")
    @classmethod
    def expand_installed_path(cls, v: str | None) -> str | None:
        """Expand user home directory in installed_path."""
        if v is None:
            return None
        return str(Path(v).expanduser().resolve())


class SkillsConfig(BaseModel):
    """Skills system configuration (matches memory pattern)."""

    # Plugin skills (git-based, user-installed)
    plugins: list[PluginSkillSource] = Field(
        default_factory=list,
        description="Git-based plugin skills with source configuration",
    )

    # Bundled skills control (three-state: user enabled, user disabled, manifest default)
    disabled_bundled: list[str] = Field(
        default_factory=list,
        description="Bundled skills explicitly disabled by user (overrides default_enabled: true).",
    )
    enabled_bundled: list[str] = Field(
        default_factory=list,
        description="Bundled skills explicitly enabled by user (overrides default_enabled: false).",
    )

    # Directory configuration
    user_dir: str = Field(
        default="~/.agent/skills",
        description="Directory for user-installed plugin skills",
    )
    bundled_dir: str | None = Field(
        default=None,
        description="Directory for bundled core skills. Auto-detected from repo if None.",
    )

    # Script execution configuration
    script_timeout: int = Field(
        default=60,
        description="Timeout in seconds for script execution",
    )
    max_script_output: int = Field(
        default=1_048_576,  # 1MB
        description="Maximum output size in bytes for script execution",
    )

    @model_validator(mode="after")
    def expand_paths(self) -> "SkillsConfig":
        """Expand user home directory in paths after validation."""
        # Expand user_dir if it contains ~
        if "~" in self.user_dir:
            self.user_dir = str(Path(self.user_dir).expanduser().resolve())

        # Expand bundled_dir if set and contains ~
        if self.bundled_dir and "~" in self.bundled_dir:
            self.bundled_dir = str(Path(self.bundled_dir).expanduser().resolve())

        return self


class AgentConfig(BaseModel):
    """Agent-specific configuration."""

    data_dir: str = "~/.agent"
    log_level: str = "info"
    system_prompt_file: str | None = None

    # Filesystem tools configuration
    workspace_root: Path | None = Field(
        default=None,
        description="Root directory for filesystem tools. Defaults to current working directory if not set.",
    )
    filesystem_writes_enabled: bool = Field(
        default=False,
        description="Enable filesystem write operations (write_file, apply_text_edit, create_directory)",
    )
    filesystem_max_read_bytes: int = Field(
        default=10_485_760, description="Maximum file size in bytes for read operations"  # 10MB
    )
    filesystem_max_write_bytes: int = Field(
        default=1_048_576, description="Maximum content size in bytes for write operations"  # 1MB
    )

    @field_validator("data_dir")
    @classmethod
    def expand_data_dir(cls, v: str) -> str:
        """Expand user home directory in data_dir."""
        return str(Path(v).expanduser())

    @field_validator("workspace_root")
    @classmethod
    def expand_workspace_root(cls, v: Path | None) -> Path | None:
        """Expand user home directory in workspace_root and resolve to absolute path."""
        if v is None:
            return None
        # Convert to Path if string, expand user, and resolve to absolute
        path = Path(v).expanduser().resolve()
        return path


class TelemetryConfig(BaseModel):
    """Telemetry and observability configuration."""

    enabled: bool = False
    enable_sensitive_data: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    applicationinsights_connection_string: str | None = None


class Mem0Config(BaseModel):
    """Mem0-specific configuration."""

    storage_path: str | None = None
    api_key: str | None = None
    org_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None

    @field_validator("storage_path")
    @classmethod
    def expand_storage_path(cls, v: str | None) -> str | None:
        """Expand user home directory in storage_path."""
        if v:
            return str(Path(v).expanduser())
        return v


class MemoryConfig(BaseModel):
    """Memory configuration."""

    enabled: bool = True
    type: str = "in_memory"
    history_limit: int = 20
    mem0: Mem0Config = Field(default_factory=Mem0Config)

    @field_validator("type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        """Validate memory type."""
        if v not in VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory type: {v}. Valid types: {VALID_MEMORY_TYPES}")
        return v


class AgentSettings(BaseModel):
    """Root configuration model for agent settings."""

    version: str = "1.0"
    providers: ProviderConfig = Field(default_factory=ProviderConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)

    def model_dump_json_pretty(self, **kwargs: Any) -> str:
        """Dump model to pretty-printed JSON string."""
        return self.model_dump_json(indent=2, exclude_none=False, **kwargs)

    def model_dump_json_minimal(self) -> str:
        """Dump model to minimal JSON string (progressive disclosure).

        Only includes:
        - Enabled providers (not disabled ones)
        - Non-null values

        This creates a cleaner, more user-friendly config file that shows
        only what the user has explicitly configured.

        Benefits:
        - Reduced clutter (100+ lines → ~20 lines)
        - Clear intent (only see what's configured)
        - Git-friendly (smaller diffs)
        - Industry standard (like package.json, docker-compose)

        Returns:
            JSON string with minimal configuration

        Example:
            >>> settings = AgentSettings()
            >>> settings.providers.enabled = ["openai"]
            >>> settings.providers.openai.api_key = "sk-..."
            >>> json_str = settings.model_dump_json_minimal()
            # Only shows openai config, not disabled providers
        """
        # Get full data excluding None values
        data = self.model_dump(exclude_none=True)

        # Filter providers: only include enabled ones
        if "providers" in data:
            enabled = data["providers"].get("enabled", [])
            filtered_providers = {"enabled": enabled}

            # Only include enabled provider configs
            for provider in enabled:
                if provider in data["providers"]:
                    provider_data = data["providers"][provider]
                    # Remove the redundant 'enabled' flag from individual providers
                    # (it's already in the enabled list)
                    if isinstance(provider_data, dict):
                        provider_data.pop("enabled", None)
                    filtered_providers[provider] = provider_data

            data["providers"] = filtered_providers

        # Clean up empty nested objects (like mem0 if all values are None)
        if "memory" in data and "mem0" in data["memory"]:
            if not data["memory"]["mem0"]:
                # Remove empty mem0 config
                del data["memory"]["mem0"]

        return json.dumps(data, indent=2)

    @classmethod
    def get_json_schema(cls) -> dict[str, Any]:
        """Get JSON schema for the settings model."""
        return cls.model_json_schema()

    def validate_enabled_providers(self) -> list[str]:
        """Validate all enabled providers have required configuration.

        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []

        for provider_name in self.providers.enabled:
            provider = getattr(self.providers, provider_name)

            if provider_name == "openai":
                if not provider.api_key:
                    errors.append(
                        "OpenAI provider enabled but missing api_key. "
                        "Run: agent config enable openai"
                    )

            elif provider_name == "anthropic":
                if not provider.api_key:
                    errors.append(
                        "Anthropic provider enabled but missing api_key. "
                        "Run: agent config enable anthropic"
                    )

            elif provider_name == "azure":
                if not provider.endpoint:
                    errors.append(
                        "Azure provider enabled but missing endpoint. "
                        "Run: agent config enable azure"
                    )
                if not provider.deployment:
                    errors.append(
                        "Azure provider enabled but missing deployment. "
                        "Run: agent config enable azure"
                    )

            elif provider_name == "foundry":
                if not provider.project_endpoint:
                    errors.append(
                        "Foundry provider enabled but missing project_endpoint. "
                        "Run: agent config enable foundry"
                    )
                if not provider.model_deployment:
                    errors.append(
                        "Foundry provider enabled but missing model_deployment. "
                        "Run: agent config enable foundry"
                    )

            elif provider_name == "gemini":
                if provider.use_vertexai:
                    if not provider.project_id:
                        errors.append(
                            "Gemini Vertex AI enabled but missing project_id. "
                            "Run: agent config enable gemini"
                        )
                    if not provider.location:
                        errors.append(
                            "Gemini Vertex AI enabled but missing location. "
                            "Run: agent config enable gemini"
                        )
                else:
                    if not provider.api_key:
                        errors.append(
                            "Gemini provider enabled but missing api_key. "
                            "Run: agent config enable gemini"
                        )

            elif provider_name == "local":
                # Local provider requires base_url
                if not provider.base_url:
                    errors.append(
                        "Local provider enabled but missing base_url. "
                        "Set LOCAL_BASE_URL environment variable or configure via: agent config enable local"
                    )

            elif provider_name == "github":
                # GitHub authentication is handled at runtime via get_github_token()
                # which checks GITHUB_TOKEN env var or gh CLI
                # Token is optional in config - validation happens at runtime
                pass

        return errors

    @property
    def llm_provider(self) -> str:
        """Get the primary LLM provider (first enabled provider).

        Returns:
            Primary provider name from enabled list

        Raises:
            ValueError: If no providers are enabled

        Example:
            >>> settings = AgentSettings()
            >>> settings.providers.enabled = ["openai"]
            >>> settings.llm_provider
            'openai'
        """
        if not self.providers.enabled:
            raise ValueError("No providers enabled in configuration")
        return self.providers.enabled[0]

    @property
    def agent_data_dir(self) -> Path:
        """Get agent data directory as Path object.

        Returns:
            Path to agent data directory (~/.agent by default)
        """
        return Path(self.agent.data_dir).expanduser()

    @property
    def agent_session_dir(self) -> Path:
        """Get agent session directory as Path object.

        Returns:
            Path to agent session directory (data_dir/sessions)
        """
        return self.agent_data_dir / "sessions"

    @property
    def memory_enabled(self) -> bool:
        """Get memory enabled status.

        Returns:
            True if memory is enabled
        """
        return self.memory.enabled

    @property
    def memory_type(self) -> str:
        """Get memory type.

        Returns:
            Memory type ('in_memory' or 'mem0')
        """
        return self.memory.type

    @property
    def memory_history_limit(self) -> int:
        """Get memory history limit.

        Returns:
            Maximum number of messages to keep in memory
        """
        return self.memory.history_limit

    @property
    def system_prompt_file(self) -> str | None:
        """Get system prompt file path.

        Returns:
            Path to custom system prompt file or None.
            Checks agent.system_prompt_file field first, then falls back to AGENT_SYSTEM_PROMPT env var.
        """
        # Check if field is explicitly set
        if self.agent.system_prompt_file is not None:
            return self.agent.system_prompt_file

        # Fall back to environment variable
        import os

        return os.getenv("AGENT_SYSTEM_PROMPT")

    def get_model_display_name(self) -> str:
        """Get display name for the current model with provider.

        Returns:
            Model name with provider prefix (e.g., "OpenAI/gpt-5-mini")

        Example:
            >>> settings = AgentSettings()
            >>> settings.providers.enabled = ["openai"]
            >>> settings.providers.openai.model = "gpt-5-mini"
            >>> settings.get_model_display_name()
            'OpenAI/gpt-5-mini'
        """
        provider = self.llm_provider

        # Format: Provider/model
        if provider == "openai":
            return f"OpenAI/{self.providers.openai.model}"
        elif provider == "anthropic":
            return f"Anthropic/{self.providers.anthropic.model}"
        elif provider == "azure":
            deployment = self.providers.azure.deployment or "unknown"
            return f"Azure OpenAI/{deployment}"
        elif provider == "foundry":
            deployment = self.providers.foundry.model_deployment or "unknown"
            return f"Azure AI Foundry/{deployment}"
        elif provider == "gemini":
            return f"Gemini/{self.providers.gemini.model}"
        elif provider == "github":
            return f"GitHub/{self.providers.github.model}"
        elif provider == "local":
            return f"Local/{self.providers.local.model}"
        else:
            return "unknown"

    # Legacy compatibility aliases for smooth migration
    @property
    def openai_api_key(self) -> str | None:
        """Legacy: Get OpenAI API key."""
        return self.providers.openai.api_key

    @property
    def openai_model(self) -> str:
        """Legacy: Get OpenAI model."""
        return self.providers.openai.model

    @property
    def anthropic_api_key(self) -> str | None:
        """Legacy: Get Anthropic API key."""
        return self.providers.anthropic.api_key

    @property
    def anthropic_model(self) -> str:
        """Legacy: Get Anthropic model."""
        return self.providers.anthropic.model

    @property
    def azure_openai_endpoint(self) -> str | None:
        """Legacy: Get Azure OpenAI endpoint."""
        return self.providers.azure.endpoint

    @property
    def azure_openai_deployment(self) -> str | None:
        """Legacy: Get Azure OpenAI deployment."""
        return self.providers.azure.deployment

    @property
    def azure_openai_api_version(self) -> str:
        """Legacy: Get Azure OpenAI API version."""
        return self.providers.azure.api_version

    @property
    def azure_openai_api_key(self) -> str | None:
        """Legacy: Get Azure OpenAI API key."""
        return self.providers.azure.api_key

    @property
    def azure_project_endpoint(self) -> str | None:
        """Legacy: Get Azure AI Foundry project endpoint."""
        return self.providers.foundry.project_endpoint

    @property
    def azure_model_deployment(self) -> str | None:
        """Legacy: Get Azure model deployment (OpenAI or Foundry)."""
        # Check which Azure provider is enabled
        if "azure" in self.providers.enabled:
            return self.providers.azure.deployment
        elif "foundry" in self.providers.enabled:
            return self.providers.foundry.model_deployment
        return None

    @property
    def gemini_api_key(self) -> str | None:
        """Legacy: Get Gemini API key."""
        return self.providers.gemini.api_key

    @property
    def gemini_model(self) -> str:
        """Legacy: Get Gemini model."""
        return self.providers.gemini.model

    @property
    def gemini_project_id(self) -> str | None:
        """Legacy: Get Gemini project ID."""
        return self.providers.gemini.project_id

    @property
    def gemini_location(self) -> str | None:
        """Legacy: Get Gemini location."""
        return self.providers.gemini.location

    @property
    def gemini_use_vertexai(self) -> bool:
        """Legacy: Get Gemini Vertex AI usage flag."""
        return self.providers.gemini.use_vertexai

    @property
    def github_token(self) -> str | None:
        """Legacy: Get GitHub token."""
        return self.providers.github.token

    @property
    def github_model(self) -> str:
        """Legacy: Get GitHub model."""
        return self.providers.github.model

    @property
    def github_endpoint(self) -> str:
        """Legacy: Get GitHub endpoint."""
        return self.providers.github.endpoint

    @property
    def github_org(self) -> str | None:
        """Legacy: Get GitHub organization."""
        return self.providers.github.org

    @property
    def local_base_url(self) -> str:
        """Legacy: Get local base URL."""
        return self.providers.local.base_url

    @property
    def local_model(self) -> str:
        """Legacy: Get local model."""
        return self.providers.local.model

    @property
    def workspace_root(self) -> Path | None:
        """Legacy: Get workspace root for filesystem tools."""
        return self.agent.workspace_root

    @workspace_root.setter
    def workspace_root(self, value: Path | None) -> None:
        """Legacy: Set workspace root for filesystem tools."""
        self.agent.workspace_root = value

    @property
    def filesystem_writes_enabled(self) -> bool:
        """Legacy: Get filesystem writes enabled flag."""
        return self.agent.filesystem_writes_enabled

    @filesystem_writes_enabled.setter
    def filesystem_writes_enabled(self, value: bool) -> None:
        """Legacy: Set filesystem writes enabled flag."""
        self.agent.filesystem_writes_enabled = value

    @property
    def filesystem_max_read_bytes(self) -> int:
        """Legacy: Get filesystem max read bytes."""
        return self.agent.filesystem_max_read_bytes

    @filesystem_max_read_bytes.setter
    def filesystem_max_read_bytes(self, value: int) -> None:
        """Legacy: Set filesystem max read bytes."""
        self.agent.filesystem_max_read_bytes = value

    @property
    def filesystem_max_write_bytes(self) -> int:
        """Legacy: Get filesystem max write bytes."""
        return self.agent.filesystem_max_write_bytes

    @filesystem_max_write_bytes.setter
    def filesystem_max_write_bytes(self, value: int) -> None:
        """Legacy: Set filesystem max write bytes."""
        self.agent.filesystem_max_write_bytes = value

    @property
    def mem0_user_id(self) -> str | None:
        """Legacy: Get Mem0 user ID."""
        return self.memory.mem0.user_id

    @property
    def mem0_project_id(self) -> str | None:
        """Legacy: Get Mem0 project ID."""
        return self.memory.mem0.project_id

    @property
    def mem0_storage_path(self) -> str | None:
        """Legacy: Get Mem0 storage path."""
        return self.memory.mem0.storage_path

    @property
    def mem0_api_key(self) -> str | None:
        """Legacy: Get Mem0 API key."""
        return self.memory.mem0.api_key

    @property
    def mem0_org_id(self) -> str | None:
        """Legacy: Get Mem0 organization ID."""
        return self.memory.mem0.org_id

    @property
    def memory_dir(self) -> Path:
        """Legacy: Get memory directory path."""
        return self.agent_data_dir / "memory"

    @property
    def enabled_providers(self) -> list[str]:
        """Legacy: Get list of enabled providers."""
        return self.providers.enabled

    @property
    def enable_otel(self) -> bool:
        """Legacy: Get telemetry enabled flag."""
        return self.telemetry.enabled

    @property
    def enable_otel_explicit(self) -> bool:
        """Legacy: Check if telemetry was explicitly enabled (not auto-detected)."""
        return self.telemetry.enabled

    @property
    def otlp_endpoint(self) -> str:
        """Legacy: Get OTLP endpoint."""
        return self.telemetry.otlp_endpoint

    @property
    def applicationinsights_connection_string(self) -> str | None:
        """Legacy: Get Application Insights connection string."""
        return self.telemetry.applicationinsights_connection_string

    @property
    def enable_sensitive_data(self) -> bool:
        """Legacy: Get enable sensitive data flag."""
        return self.telemetry.enable_sensitive_data
