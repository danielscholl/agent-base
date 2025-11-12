"""Utility functions for mem0 integration.

This module provides helper functions for mem0 client management,
health checks, and connection handling.
"""

import logging
import socket
from typing import Any

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


def check_mem0_endpoint(endpoint: str | None = None, timeout: float = 0.02) -> bool:
    """Fast health check for mem0 endpoint availability.

    Uses socket connection test for quick auto-detection without
    making full HTTP requests.

    Args:
        endpoint: Endpoint URL (e.g., "http://localhost:8000")
        timeout: Connection timeout in seconds (default: 20ms)

    Returns:
        True if endpoint is reachable, False otherwise

    Example:
        >>> check_mem0_endpoint("http://localhost:8000")
        True
    """
    if not endpoint:
        endpoint = "http://localhost:8000"

    # Extract host and port from endpoint
    try:
        # Remove protocol
        host_port = endpoint.replace("http://", "").replace("https://", "")
        # Split host:port
        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            # Remove any path after port
            port_str = port_str.split("/")[0]
            port = int(port_str)
        else:
            host = host_port.split("/")[0]
            port = 80 if endpoint.startswith("http://") else 443

        # Try socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        return result == 0

    except Exception as e:
        logger.debug(f"Mem0 endpoint check failed: {e}")
        return False


def get_mem0_client(config: AgentConfig) -> Any:
    """Factory function to create mem0 client based on configuration.

    Routes to self-hosted or cloud client based on config settings.

    Args:
        config: Agent configuration with mem0 settings

    Returns:
        Configured mem0 MemoryClient instance

    Raises:
        ValueError: If configuration is invalid or incomplete
        ImportError: If mem0ai package is not installed

    Example:
        >>> config = AgentConfig.from_env()
        >>> client = get_mem0_client(config)
    """
    try:
        from mem0 import MemoryClient
    except ImportError:
        raise ImportError(
            "mem0ai package not installed. "
            "Install with: uv add mem0ai"
        )

    # Validate configuration
    if not config.mem0_host and not (config.mem0_api_key and config.mem0_org_id):
        raise ValueError(
            "Invalid mem0 configuration. Provide either:\n"
            "  - Self-hosted: MEM0_HOST\n"
            "  - Cloud: MEM0_API_KEY + MEM0_ORG_ID"
        )

    # Route to appropriate client
    if config.mem0_host:
        # Self-hosted mode
        logger.info(f"Initializing mem0 self-hosted client: {config.mem0_host}")
        try:
            client = MemoryClient(host=config.mem0_host)
            logger.debug("Mem0 self-hosted client initialized successfully")
            return client
        except Exception as e:
            raise ValueError(f"Failed to initialize mem0 self-hosted client: {e}")
    else:
        # Cloud mode
        logger.info("Initializing mem0 cloud client")
        try:
            client = MemoryClient(
                api_key=config.mem0_api_key,
                org_id=config.mem0_org_id
            )
            logger.debug("Mem0 cloud client initialized successfully")
            return client
        except Exception as e:
            raise ValueError(f"Failed to initialize mem0 cloud client: {e}")
