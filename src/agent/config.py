"""Configuration management for Agent with multi-provider LLM support."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Default models for each provider
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"


@dataclass
class AgentConfig:
    """Configuration for Agent.

    Supports six LLM providers:
    - openai: OpenAI API (gpt-5-mini, gpt-4o, etc.)
    - anthropic: Anthropic API (claude-haiku-4-5, claude-sonnet-4-5, claude-opus-4, etc.)
    - azure: Azure OpenAI (requires deployment name)
    - foundry: Azure AI Foundry with managed models
    - gemini: Google Gemini API (gemini-2.0-flash-exp, gemini-2.5-pro, etc.)
    - local: Local models via Docker Desktop (qwen3, phi4, etc.)

    Model selection:
    - AGENT_MODEL: Override default model for any provider
    - Defaults: gpt-5-mini (OpenAI), claude-haiku-4-5-20251001 (Anthropic),
      gemini-2.0-flash-exp (Gemini), ai/phi4 (Local)
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
    azure_openai_api_version: str = "2024-08-01-preview"
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

    # System prompt configuration
    system_prompt_file: str | None = None

    # Observability configuration
    enable_otel: bool = False
    enable_otel_explicit: bool = False  # Track if ENABLE_OTEL was explicitly set
    enable_sensitive_data: bool = False
    applicationinsights_connection_string: str | None = None
    otlp_endpoint: str | None = None

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
        # Note: Memory is currently redundant with thread persistence
        # Default to false until semantic memory (mem0) is implemented
        config.memory_enabled = os.getenv("MEMORY_ENABLED", "true").lower() == "true"
        config.memory_type = os.getenv("MEMORY_TYPE", "in_memory")
        config.memory_history_limit = int(os.getenv("MEMORY_HISTORY_LIMIT", "20"))
        memory_dir = os.getenv("MEMORY_DIR")
        if memory_dir:
            config.memory_dir = Path(memory_dir).expanduser()
        else:
            config.memory_dir = config.agent_data_dir / "memory"

        # System prompt configuration
        config.system_prompt_file = os.getenv("AGENT_SYSTEM_PROMPT")

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
                "Supported providers: openai, anthropic, azure, foundry, gemini, local"
            )

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
        elif self.llm_provider == "local":
            return f"Local/{self.local_model}"
        return "Unknown"
