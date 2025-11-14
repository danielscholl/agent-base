"""Utility functions for CLI module."""

import logging
import os
import platform
import sys
from typing import Any

from rich.console import Console

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


def get_console() -> Console:
    """Create Rich console with proper encoding for Windows.

    On Windows in non-interactive mode (subprocess, pipe, etc.), the default
    encoding is often CP1252 which cannot handle Unicode characters. This
    function detects such cases and forces UTF-8 encoding when possible.

    Returns:
        Console: Configured Rich console instance
    """
    if platform.system() == "Windows" and not sys.stdout.isatty():
        # Running in non-interactive mode (subprocess, pipe, etc)
        # Try to use UTF-8 if available
        try:
            import locale

            encoding = locale.getpreferredencoding() or ""
            if "utf" not in encoding.lower():
                # Force UTF-8 for better Unicode support
                os.environ["PYTHONIOENCODING"] = "utf-8"
                # Create console with legacy Windows mode disabled
                return Console(force_terminal=True, legacy_windows=False)
            else:
                return Console()
        except Exception:
            # Fallback to safe ASCII mode if encoding detection fails
            return Console(legacy_windows=True, safe_box=True)
    else:
        # Normal interactive mode or non-Windows
        return Console()


def hide_connection_string_if_otel_disabled(config: AgentConfig) -> str | None:
    """Conditionally hide Azure Application Insights connection string.

    The agent_framework auto-enables OpenTelemetry when it sees
    APPLICATIONINSIGHTS_CONNECTION_STRING in the environment, which causes
    1-3s exit lag from daemon threads flushing metrics.

    This helper hides the connection string ONLY when telemetry is disabled,
    allowing users who explicitly enable OTEL to still use it.

    Args:
        config: Loaded AgentConfig (must be loaded first to check enable_otel)

    Returns:
        The connection string if it was hidden, None otherwise

    Example:
        >>> config = AgentConfig.from_combined()
        >>> saved = hide_connection_string_if_otel_disabled(config)
        >>> # ... create agent ...
        >>> if saved:
        ...     os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = saved
    """
    should_enable_otel = config.enable_otel and config.enable_otel_explicit

    if not should_enable_otel and config.applicationinsights_connection_string:
        saved = os.environ.pop("APPLICATIONINSIGHTS_CONNECTION_STRING", None)
        if saved:
            logger.debug(
                "[PERF] Hiding Azure connection string to prevent OpenTelemetry "
                "auto-init (set ENABLE_OTEL=true to enable telemetry)"
            )
        return saved

    return None


def set_model_span_attributes(span: Any, config: AgentConfig) -> None:
    """Set OpenTelemetry span attributes based on provider and model configuration.

    Args:
        span: OpenTelemetry span to set attributes on
        config: Agent configuration containing provider and model information
    """
    span.set_attribute("gen_ai.system", config.llm_provider or "unknown")

    if config.llm_provider == "openai" and config.openai_model:
        span.set_attribute("gen_ai.request.model", config.openai_model)
    elif config.llm_provider == "anthropic" and config.anthropic_model:
        span.set_attribute("gen_ai.request.model", config.anthropic_model)
    elif config.llm_provider == "azure" and config.azure_openai_deployment:
        span.set_attribute("gen_ai.request.model", config.azure_openai_deployment)
    elif config.llm_provider == "foundry" and config.azure_model_deployment:
        span.set_attribute("gen_ai.request.model", config.azure_model_deployment)
