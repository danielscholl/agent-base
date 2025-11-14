"""Provider setup abstractions and registry.

This module provides a protocol-based approach to provider configuration,
eliminating the 400+ lines of duplication in config_commands.py.

Pattern:
    Each provider implements ProviderSetup protocol with three methods:
    - detect_credentials() - Check environment for existing credentials
    - prompt_user() - Interactive prompts for missing credentials
    - configure() - Main entry point that orchestrates the above

Registry:
    PROVIDER_REGISTRY maps provider names to their setup implementations,
    enabling dynamic dispatch instead of if/elif chains.

Example:
    >>> setup = PROVIDER_REGISTRY["openai"]
    >>> credentials = setup.configure(console)
    >>> settings.providers.openai.update(credentials)
"""

from agent.config.providers.base import ProviderSetup
from agent.config.providers.registry import PROVIDER_REGISTRY, get_provider_setup

__all__ = ["ProviderSetup", "PROVIDER_REGISTRY", "get_provider_setup"]
