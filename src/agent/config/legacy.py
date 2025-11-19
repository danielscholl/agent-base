"""Configuration management for Agent with multi-provider LLM support."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv

if TYPE_CHECKING:
    pass

# Default models for each provider
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"


def _auto_detect_github_org() -> str | None:
    """Auto-detect GitHub organization from gh CLI for enterprise users.

    Returns:
        Organization login name if detected, None otherwise
    """
    try:
        from agent.providers.github.auth import get_github_org

        return get_github_org()
    except Exception:
        # Silently fail - organization is optional
        return None


@dataclass
class AgentConfig:
    """Configuration for Agent.

    Supports seven LLM providers:
    - openai: OpenAI API (gpt-5-mini, gpt-4o, etc.)
    - anthropic: Anthropic API (claude-haiku-4-5, claude-sonnet-4-5, claude-opus-4, etc.)
    - azure: Azure OpenAI (requires deployment name)
    - foundry: Azure AI Foundry with managed models
    - gemini: Google Gemini API (gemini-2.0-flash-exp, gemini-2.5-pro, etc.)
    - github: GitHub Models (phi-4, llama-3.3-70b-instruct, etc.)
    - local: Local models via Docker Desktop (qwen3, phi4, etc.)

    Model selection:
    - AGENT_MODEL: Override default model for any provider
    - Defaults: gpt-5-mini (OpenAI), claude-haiku-4-5-20251001 (Anthropic),
      gemini-2.0-flash-exp (Gemini), gpt-5-nano (GitHub), ai/phi4 (Local)
    - Azure providers: Use deployment names (AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_MODEL_DEPLOYMENT)
    - Local: Recommended ai/qwen3 for best tool calling, ai/phi4 for general use
    """

    # LLM Provider (openai, anthropic, azure, or foundry)
    llm_provider: str

    # OpenAI (when llm_provider == "openai")
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"

    # Anthropic (when llm_provider == "anthropic")
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"

    # Azure OpenAI (when llm_provider == "azure")
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2025-03-01-preview"
    azure_openai_api_key: str | None = None
    # Uses AzureCliCredential for auth if API key not provided

    # Azure AI Foundry (when llm_provider == "foundry")
    azure_project_endpoint: str | None = None
    azure_model_deployment: str | None = None
    # Uses AzureCliCredential for auth, no API key needed

    # Google Gemini (when llm_provider == "gemini")
    gemini_api_key: str | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL
    gemini_project_id: str | None = None
    gemini_location: str | None = None
    gemini_use_vertexai: bool = False
    # Supports both API key (Gemini Developer API) and Vertex AI (GCP credentials)

    # GitHub Models (when llm_provider == "github")
    github_token: str | None = None
    github_model: str = "gpt-4o-mini"
    github_endpoint: str = "https://models.github.ai"
    github_org: str | None = None  # Optional: org name for enterprise rate limits
    # Uses GITHUB_TOKEN env var or gh CLI authentication

    # Local Provider (when llm_provider == "local")
    local_base_url: str | None = None
    local_model: str = "ai/phi4"
    # Docker Desktop Model Runner with OpenAI-compatible API

    # Agent-specific
    agent_data_dir: Path | None = None
    agent_session_dir: Path | None = None

    # Memory configuration (currently redundant with thread persistence)
    memory_enabled: bool = True  # Enable by default for conversation memory
    memory_type: str = "in_memory"  # Future: "mem0", "langchain", etc.
    memory_dir: Path | None = None
    memory_history_limit: int = 20  # Max memories to inject as context

    # Mem0 semantic memory configuration
    mem0_storage_path: Path | None = (
        None  # Local Chroma storage path (default: memory_dir/chroma_db)
    )
    mem0_api_key: str | None = None  # Cloud mode API key (mem0.ai)
    mem0_org_id: str | None = None  # Cloud mode organization ID
    mem0_user_id: str | None = None  # User namespace (default: username)
    mem0_project_id: str | None = None  # Project namespace for isolation

    # System prompt configuration
    system_prompt_file: str | None = None

    # Filesystem tools configuration
    workspace_root: Path | None = None
    filesystem_writes_enabled: bool = False
    filesystem_max_read_bytes: int = 10_485_760  # 10MB default
    filesystem_max_write_bytes: int = 1_048_576  # 1MB default

    # Skills configuration (from settings.skills)
    skills: Any = None  # SkillsConfig from schema.py

    # Observability configuration
    enable_otel: bool = False
    enable_otel_explicit: bool = False  # Track if ENABLE_OTEL was explicitly set
    enable_sensitive_data: bool = False
    applicationinsights_connection_string: str | None = None
    otlp_endpoint: str | None = None

    # Configuration source tracking (for new config system)
    enabled_providers: list[str] | None = None  # List of enabled providers from settings.json
    config_source: str = "env"  # Source of configuration: "env", "file", or "combined"

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables.

        Returns:
            AgentConfig instance with values from environment

        Example:
            >>> config = AgentConfig.from_env()
            >>> config.llm_provider
            'openai'
        """
        load_dotenv()

        llm_provider = os.getenv("LLM_PROVIDER", "local")

        # AGENT_MODEL can override any provider's default model
        agent_model = os.getenv("AGENT_MODEL")

        config = cls(
            llm_provider=llm_provider,
            # OpenAI
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=agent_model or "gpt-5-mini",
            # Anthropic
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=agent_model or "claude-haiku-4-5-20251001",
            # Azure OpenAI (deployment name is required Azure resource identifier)
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_VERSION", "2025-03-01-preview"),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            # Azure AI Foundry (deployment name is required Azure resource identifier)
            azure_project_endpoint=os.getenv("AZURE_PROJECT_ENDPOINT"),
            azure_model_deployment=os.getenv("AZURE_MODEL_DEPLOYMENT"),
            # Google Gemini
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=agent_model or DEFAULT_GEMINI_MODEL,
            gemini_project_id=os.getenv("GEMINI_PROJECT_ID"),
            gemini_location=os.getenv("GEMINI_LOCATION"),
            gemini_use_vertexai=os.getenv("GEMINI_USE_VERTEXAI", "false").lower() == "true",
            # GitHub Models
            github_token=os.getenv("GITHUB_TOKEN"),
            github_model=agent_model or "gpt-4o-mini",
            github_endpoint=os.getenv("GITHUB_ENDPOINT", "https://models.github.ai"),
            github_org=os.getenv("GITHUB_ORG") or _auto_detect_github_org(),
            # Local Provider
            local_base_url=os.getenv(
                "LOCAL_BASE_URL", "http://localhost:12434/engines/llama.cpp/v1"
            ),
            local_model=agent_model or "ai/phi4",
        )

        # Set default paths
        home = Path.home()
        data_dir = os.getenv("AGENT_DATA_DIR", str(home / ".agent"))
        config.agent_data_dir = Path(data_dir).expanduser()
        config.agent_session_dir = config.agent_data_dir / "sessions"

        # Memory configuration
        # Note: Memory is enabled by default for conversation context
        # Supports both in-memory (keyword search) and mem0 (semantic search)
        config.memory_enabled = os.getenv("MEMORY_ENABLED", "true").lower() == "true"
        config.memory_type = os.getenv("MEMORY_TYPE", "in_memory")
        config.memory_history_limit = int(os.getenv("MEMORY_HISTORY_LIMIT", "20"))
        memory_dir = os.getenv("MEMORY_DIR")
        if memory_dir:
            config.memory_dir = Path(memory_dir).expanduser()
        else:
            config.memory_dir = config.agent_data_dir / "memory"

        # Mem0 semantic memory configuration
        mem0_storage_env = os.getenv("MEM0_STORAGE_PATH")
        if mem0_storage_env:
            config.mem0_storage_path = Path(mem0_storage_env).expanduser()
        config.mem0_api_key = os.getenv("MEM0_API_KEY")
        config.mem0_org_id = os.getenv("MEM0_ORG_ID")
        config.mem0_user_id = os.getenv("MEM0_USER_ID") or os.getenv("USER") or "default-user"
        config.mem0_project_id = os.getenv("MEM0_PROJECT_ID")

        # System prompt configuration
        config.system_prompt_file = os.getenv("AGENT_SYSTEM_PROMPT")

        # Filesystem tools configuration
        workspace_root_env = os.getenv("AGENT_WORKSPACE_ROOT")
        if workspace_root_env:
            config.workspace_root = Path(workspace_root_env).expanduser().resolve()
        config.filesystem_writes_enabled = (
            os.getenv("FILESYSTEM_WRITES_ENABLED", "false").lower() == "true"
        )
        config.filesystem_max_read_bytes = int(os.getenv("FILESYSTEM_MAX_READ_BYTES", "10485760"))
        config.filesystem_max_write_bytes = int(os.getenv("FILESYSTEM_MAX_WRITE_BYTES", "1048576"))

        # Skills configuration - will be set from settings.skills in from_combined()
        # No environment variable configuration for skills

        # Observability configuration
        # Track whether ENABLE_OTEL was explicitly set in environment
        enable_otel_env = os.getenv("ENABLE_OTEL")
        config.enable_otel_explicit = enable_otel_env is not None
        config.enable_otel = enable_otel_env.lower() == "true" if enable_otel_env else False

        config.enable_sensitive_data = os.getenv("ENABLE_SENSITIVE_DATA", "false").lower() == "true"
        config.applicationinsights_connection_string = os.getenv(
            "APPLICATIONINSIGHTS_CONNECTION_STRING"
        )
        config.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

        # Note: from_env() doesn't set enabled_providers (old behavior)
        # This allows health check to test all configured providers
        config.enabled_providers = None
        config.config_source = "env"

        return config

    def validate(self) -> None:
        """Validate configuration based on selected provider.

        Raises:
            ValueError: If required configuration is missing for the selected provider

        Example:
            >>> config = AgentConfig(llm_provider="openai")
            >>> config.validate()  # Will raise ValueError if OPENAI_API_KEY missing
        """
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                raise ValueError(
                    "OpenAI provider requires API key. Set OPENAI_API_KEY environment variable."
                )
        elif self.llm_provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError(
                    "Anthropic provider requires API key. Set ANTHROPIC_API_KEY environment variable."
                )
        elif self.llm_provider == "azure":
            if not self.azure_openai_endpoint:
                raise ValueError(
                    "Azure OpenAI requires endpoint. Set AZURE_OPENAI_ENDPOINT environment variable."
                )
            if not self.azure_openai_deployment:
                raise ValueError(
                    "Azure OpenAI requires deployment name. Set AZURE_OPENAI_DEPLOYMENT_NAME environment variable."
                )
            # Note: Can use AzureCliCredential OR API key for auth
        elif self.llm_provider == "foundry":
            if not self.azure_project_endpoint:
                raise ValueError(
                    "Azure AI Foundry requires project endpoint. Set AZURE_PROJECT_ENDPOINT environment variable."
                )
            if not self.azure_model_deployment:
                raise ValueError(
                    "Azure AI Foundry requires model deployment name. Set AZURE_MODEL_DEPLOYMENT environment variable."
                )
            # Note: Uses AzureCliCredential for auth, user must be logged in via `az login`
        elif self.llm_provider == "gemini":
            if self.gemini_use_vertexai:
                # Vertex AI authentication
                if not self.gemini_project_id:
                    raise ValueError(
                        "Gemini Vertex AI requires project ID. Set GEMINI_PROJECT_ID environment variable."
                    )
                if not self.gemini_location:
                    raise ValueError(
                        "Gemini Vertex AI requires location. Set GEMINI_LOCATION environment variable."
                    )
                # Note: Uses Google Cloud default credentials
            else:
                # API key authentication
                if not self.gemini_api_key:
                    raise ValueError(
                        "Gemini provider requires API key. Set GEMINI_API_KEY environment variable."
                    )
        elif self.llm_provider == "github":
            # GitHub authentication is handled by get_github_token() which checks
            # GITHUB_TOKEN env var or gh CLI at runtime. No validation needed here.
            pass
        elif self.llm_provider == "local":
            if not self.local_base_url:
                raise ValueError(
                    "Local provider requires base URL. "
                    "Set LOCAL_BASE_URL environment variable "
                    "(e.g., http://localhost:12434/engines/llama.cpp/v1). "
                    "Ensure Docker Desktop is running with Model Runner enabled "
                    "and model is pulled (e.g., docker model pull phi4)."
                )
        else:
            raise ValueError(
                f"Unknown LLM provider: {self.llm_provider}. "
                "Supported providers: openai, anthropic, azure, foundry, gemini, github, local"
            )

        # Mem0 validation: No validation needed!
        # - If both MEM0_API_KEY and MEM0_ORG_ID are set → cloud mode
        # - If neither or only one is set → local Chroma mode (default)
        # - Graceful fallback handled in mem0_utils.create_memory_instance()

        # Validate system prompt file if specified
        if self.system_prompt_file:
            # Expand environment variables and user home directory (same as loader)
            expanded = os.path.expandvars(self.system_prompt_file)
            prompt_path = Path(expanded).expanduser()
            if not prompt_path.exists():
                raise ValueError(f"System prompt file not found: {self.system_prompt_file}")

    def get_model_display_name(self) -> str:
        """Get display name for current model configuration.

        Returns:
            Human-readable model display name

        Example:
            >>> config = AgentConfig(llm_provider="openai", openai_model="gpt-4o")
            >>> config.get_model_display_name()
            'OpenAI/gpt-4o'
        """
        if self.llm_provider == "openai":
            return f"OpenAI/{self.openai_model}"
        elif self.llm_provider == "anthropic":
            return f"Anthropic/{self.anthropic_model}"
        elif self.llm_provider == "azure":
            return f"Azure OpenAI/{self.azure_openai_deployment}"
        elif self.llm_provider == "foundry":
            return f"Azure AI Foundry/{self.azure_model_deployment}"
        elif self.llm_provider == "gemini":
            return f"Gemini/{self.gemini_model}"
        elif self.llm_provider == "github":
            return f"GitHub/{self.github_model}"
        elif self.llm_provider == "local":
            return f"Local/{self.local_model}"
        return "Unknown"

    @classmethod
    def from_file(cls, config_path: Path | None = None) -> "AgentConfig":
        """Load configuration from JSON settings file.

        Args:
            config_path: Optional path to settings.json file. Defaults to ~/.agent/settings.json

        Returns:
            AgentConfig instance with values from JSON file

        Example:
            >>> config = AgentConfig.from_file()
            >>> config.llm_provider
            'local'
            >>> config.config_source
            'file'
        """
        from .manager import load_config

        # Load settings from file
        settings = load_config(config_path)

        # Determine primary provider - if nothing enabled, user must configure
        if not settings.providers.enabled:
            raise ValueError(
                "No providers enabled in configuration. "
                "Run 'agent config enable <provider>' to enable a provider."
            )
        llm_provider = settings.providers.enabled[0]

        # Build AgentConfig from settings
        config = cls(
            llm_provider=llm_provider,
            # OpenAI
            openai_api_key=settings.providers.openai.api_key,
            openai_model=settings.providers.openai.model,
            # Anthropic
            anthropic_api_key=settings.providers.anthropic.api_key,
            anthropic_model=settings.providers.anthropic.model,
            # Azure OpenAI
            azure_openai_endpoint=settings.providers.azure.endpoint,
            azure_openai_deployment=settings.providers.azure.deployment,
            azure_openai_api_version=settings.providers.azure.api_version,
            azure_openai_api_key=settings.providers.azure.api_key,
            # Azure AI Foundry
            azure_project_endpoint=settings.providers.foundry.project_endpoint,
            azure_model_deployment=settings.providers.foundry.model_deployment,
            # Google Gemini
            gemini_api_key=settings.providers.gemini.api_key,
            gemini_model=settings.providers.gemini.model,
            gemini_project_id=settings.providers.gemini.project_id,
            gemini_location=settings.providers.gemini.location,
            gemini_use_vertexai=settings.providers.gemini.use_vertexai,
            # GitHub Models
            github_token=settings.providers.github.token,
            github_model=settings.providers.github.model,
            github_endpoint=settings.providers.github.endpoint,
            github_org=settings.providers.github.org,
            # Local Provider
            local_base_url=settings.providers.local.base_url,
            local_model=settings.providers.local.model,
        )

        # Set data directories
        config.agent_data_dir = Path(settings.agent.data_dir).expanduser()
        config.agent_session_dir = config.agent_data_dir / "sessions"

        # Memory configuration
        config.memory_enabled = settings.memory.enabled
        config.memory_type = settings.memory.type
        config.memory_history_limit = settings.memory.history_limit
        config.memory_dir = config.agent_data_dir / "memory"

        # Mem0 configuration
        if settings.memory.mem0.storage_path:
            config.mem0_storage_path = Path(settings.memory.mem0.storage_path).expanduser()
        config.mem0_api_key = settings.memory.mem0.api_key
        config.mem0_org_id = settings.memory.mem0.org_id
        config.mem0_user_id = settings.memory.mem0.user_id or os.getenv("USER") or "default-user"
        config.mem0_project_id = settings.memory.mem0.project_id

        # Filesystem tools configuration
        if hasattr(settings.agent, "workspace_root") and settings.agent.workspace_root:
            config.workspace_root = settings.agent.workspace_root
        if hasattr(settings.agent, "filesystem_writes_enabled"):
            config.filesystem_writes_enabled = settings.agent.filesystem_writes_enabled
        if hasattr(settings.agent, "filesystem_max_read_bytes"):
            config.filesystem_max_read_bytes = settings.agent.filesystem_max_read_bytes
        if hasattr(settings.agent, "filesystem_max_write_bytes"):
            config.filesystem_max_write_bytes = settings.agent.filesystem_max_write_bytes

        # Skills configuration
        config.skills = settings.skills

        # Observability configuration
        config.enable_otel = settings.telemetry.enabled
        config.enable_otel_explicit = settings.telemetry.enabled
        config.enable_sensitive_data = settings.telemetry.enable_sensitive_data
        config.applicationinsights_connection_string = (
            settings.telemetry.applicationinsights_connection_string
        )
        config.otlp_endpoint = settings.telemetry.otlp_endpoint

        # Set enabled providers and source
        config.enabled_providers = settings.providers.enabled
        config.config_source = "file"

        return config

    @classmethod
    def from_combined(cls, config_path: Path | None = None) -> "AgentConfig":
        """Load configuration from both file and environment variables.

        File settings override environment variables. This approach treats env vars as
        fallbacks/defaults, while explicit file configuration takes precedence. This
        avoids confusion from global env vars meant for other tools.

        Precedence (highest to lowest):
        1. Settings file (~/.agent/settings.json)
        2. Environment variables (fallback)
        3. Default values

        Args:
            config_path: Optional path to settings.json file

        Returns:
            AgentConfig instance with merged configuration

        Example:
            >>> config = AgentConfig.from_combined()
            >>> config.config_source
            'combined'
        """
        from .manager import deep_merge, load_config, merge_with_env
        from .schema import AgentSettings

        # Start with defaults
        base_settings = AgentSettings()

        # Get environment values as fallback layer
        env_overrides = merge_with_env(base_settings)

        # Load from file - this will override env values
        settings = load_config(config_path)

        # Merge: file ON TOP of env (file wins)
        if env_overrides:
            # Apply env as base layer
            env_dict = deep_merge(base_settings.model_dump(), env_overrides)
            env_settings = AgentSettings(**env_dict)

            # Then apply file settings on top (file overrides env)
            file_dict = settings.model_dump(exclude_none=True)
            merged_dict = deep_merge(env_settings.model_dump(), file_dict)
            settings = AgentSettings(**merged_dict)
        # else: just use file settings as-is

        # Determine primary provider (CLI/env takes precedence over file)
        llm_provider_env = os.getenv("LLM_PROVIDER")

        # Check if config file actually exists
        from .manager import get_config_path

        config_file_exists = config_path.exists() if config_path else get_config_path().exists()

        # CLI/env provider takes precedence over file (allows --provider flag to work)
        if llm_provider_env:
            llm_provider = llm_provider_env
        elif settings.providers.enabled:
            llm_provider = settings.providers.enabled[0]
        elif not config_file_exists:
            # No config file and no LLM_PROVIDER env var
            # Show helpful message and offer to run init
            raise ValueError("No configuration found.")
        else:
            raise ValueError(
                "No providers enabled in configuration.\n"
                "Run 'agent config init' to configure a provider"
            )

        # Build AgentConfig from merged settings
        config = cls(
            llm_provider=llm_provider,
            # OpenAI
            openai_api_key=settings.providers.openai.api_key,
            openai_model=settings.providers.openai.model,
            # Anthropic
            anthropic_api_key=settings.providers.anthropic.api_key,
            anthropic_model=settings.providers.anthropic.model,
            # Azure OpenAI
            azure_openai_endpoint=settings.providers.azure.endpoint,
            azure_openai_deployment=settings.providers.azure.deployment,
            azure_openai_api_version=settings.providers.azure.api_version,
            azure_openai_api_key=settings.providers.azure.api_key,
            # Azure AI Foundry
            azure_project_endpoint=settings.providers.foundry.project_endpoint,
            azure_model_deployment=settings.providers.foundry.model_deployment,
            # Google Gemini
            gemini_api_key=settings.providers.gemini.api_key,
            gemini_model=settings.providers.gemini.model,
            gemini_project_id=settings.providers.gemini.project_id,
            gemini_location=settings.providers.gemini.location,
            gemini_use_vertexai=settings.providers.gemini.use_vertexai,
            # GitHub Models
            github_token=settings.providers.github.token,
            github_model=settings.providers.github.model,
            github_endpoint=settings.providers.github.endpoint,
            github_org=settings.providers.github.org,
            # Local Provider
            local_base_url=settings.providers.local.base_url,
            local_model=settings.providers.local.model,
        )

        # Set data directories
        config.agent_data_dir = Path(settings.agent.data_dir).expanduser()
        config.agent_session_dir = config.agent_data_dir / "sessions"

        # Memory configuration
        config.memory_enabled = settings.memory.enabled
        config.memory_type = settings.memory.type
        config.memory_history_limit = settings.memory.history_limit
        config.memory_dir = config.agent_data_dir / "memory"

        # Mem0 configuration
        if settings.memory.mem0.storage_path:
            config.mem0_storage_path = Path(settings.memory.mem0.storage_path).expanduser()
        config.mem0_api_key = settings.memory.mem0.api_key
        config.mem0_org_id = settings.memory.mem0.org_id
        config.mem0_user_id = settings.memory.mem0.user_id or os.getenv("USER") or "default-user"
        config.mem0_project_id = settings.memory.mem0.project_id

        # Filesystem tools configuration
        if hasattr(settings.agent, "workspace_root") and settings.agent.workspace_root:
            config.workspace_root = settings.agent.workspace_root
        if hasattr(settings.agent, "filesystem_writes_enabled"):
            config.filesystem_writes_enabled = settings.agent.filesystem_writes_enabled
        if hasattr(settings.agent, "filesystem_max_read_bytes"):
            config.filesystem_max_read_bytes = settings.agent.filesystem_max_read_bytes
        if hasattr(settings.agent, "filesystem_max_write_bytes"):
            config.filesystem_max_write_bytes = settings.agent.filesystem_max_write_bytes

        # Skills configuration
        config.skills = settings.skills

        # Observability configuration
        config.enable_otel = settings.telemetry.enabled
        # If telemetry is enabled in config file, treat it as explicit
        # Otherwise check if ENABLE_OTEL env var was set
        enable_otel_env = os.getenv("ENABLE_OTEL")
        config.enable_otel_explicit = settings.telemetry.enabled or (enable_otel_env is not None)
        config.enable_sensitive_data = settings.telemetry.enable_sensitive_data
        config.applicationinsights_connection_string = (
            settings.telemetry.applicationinsights_connection_string
        )
        config.otlp_endpoint = settings.telemetry.otlp_endpoint

        # Set enabled providers and source
        config.enabled_providers = settings.providers.enabled
        config.config_source = "combined"

        return config

    def get_config_source(self) -> str:
        """Get the source of this configuration.

        Returns:
            "env" if loaded from environment variables only,
            "file" if loaded from settings.json only,
            "combined" if loaded from both (file overrides env)

        Example:
            >>> config = AgentConfig.from_combined()
            >>> config.get_config_source()
            'combined'
        """
        return self.config_source
