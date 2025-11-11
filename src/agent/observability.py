"""Observability helpers for Agent Base.

This module provides helper utilities for OpenTelemetry integration.
The main observability setup is handled by agent_framework.observability.setup_observability().

For full observability setup, see:
- agent_framework.observability.setup_observability()
- Examples: examples/observability_example.py
- Documentation: docs/decisions/0014-observability-integration.md
"""

import contextvars
import logging
import socket
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Context var to hold the current agent span for cross-task propagation
_current_agent_span: contextvars.ContextVar[Any] = contextvars.ContextVar(
    "_current_agent_span", default=None
)


def set_current_agent_span(span: Any) -> None:
    """Record the current agent span in a context variable.

    This helps preserve parent-child relationships for tool spans when
    asynchronous task boundaries might lose the active span context.

    Args:
        span: The agent-level span to set as current
    """
    try:
        _current_agent_span.set(span)
    except Exception:
        # Best-effort: ignore issues with context vars in constrained envs
        pass


def get_current_agent_span() -> Any:
    """Retrieve the current agent span from the context variable.

    Returns:
        The agent span if set, otherwise None.
    """
    try:
        return _current_agent_span.get()
    except Exception:
        return None


def check_telemetry_endpoint(endpoint: str | None = None, timeout: float = 0.02) -> bool:
    """Check if telemetry endpoint is reachable.

    Uses a fast socket connection test with minimal timeout to avoid startup delays.
    This enables auto-detection of telemetry availability without user configuration.

    Args:
        endpoint: OTLP endpoint URL (default: http://localhost:4317)
        timeout: Connection timeout in seconds (default: 0.02 = 20ms)

    Returns:
        True if endpoint is reachable, False otherwise

    Example:
        >>> if check_telemetry_endpoint():
        ...     setup_observability()

    Performance:
        - When available: ~1-2ms
        - When unavailable: ~20-30ms (timeout period)
    """
    if not endpoint:
        endpoint = "http://localhost:4317"

    try:
        # Parse endpoint URL to extract host and port
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4317

        # Fast socket connection check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        return result == 0
    except Exception as e:
        logger.debug(f"Telemetry endpoint check failed: {e}")
        return False
