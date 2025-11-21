"""Configuration constants for agent-base.

This module provides a single source of truth for all default configuration values.
Separated from defaults.py and schema.py to avoid circular imports.
"""

from pathlib import Path

# Default paths
DEFAULT_CONFIG_PATH = Path.home() / ".agent" / "settings.json"
DEFAULT_DATA_DIR = Path.home() / ".agent"
DEFAULT_MEMORY_DIR = DEFAULT_DATA_DIR / "memory"
DEFAULT_SESSION_DIR = DEFAULT_DATA_DIR / "sessions"

# Default provider settings
DEFAULT_LOCAL_BASE_URL = "http://localhost:12434/engines/llama.cpp/v1"
DEFAULT_LOCAL_MODEL = "ai/phi4"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_AZURE_API_VERSION = "2025-03-01-preview"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash-exp"
DEFAULT_GITHUB_MODEL = "gpt-4o-mini"
DEFAULT_GITHUB_ENDPOINT = "https://models.github.ai"

# Default telemetry settings
DEFAULT_OTLP_ENDPOINT = "http://localhost:4317"

# Default memory settings
DEFAULT_MEMORY_TYPE = "in_memory"
DEFAULT_MEMORY_HISTORY_LIMIT = 20
