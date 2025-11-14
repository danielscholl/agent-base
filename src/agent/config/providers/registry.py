"""Provider registry for dynamic dispatch.

This module provides the PROVIDER_REGISTRY that maps provider names
to their setup implementations, enabling configuration without
if/elif chains.

Usage:
    >>> from agent.config.providers import PROVIDER_REGISTRY
    >>> setup = PROVIDER_REGISTRY["openai"]
    >>> config = setup.configure(console)
    >>> settings.providers.openai.api_key = config["api_key"]
    >>> settings.providers.openai.model = config["model"]
"""

from agent.config.providers.anthropic import AnthropicSetup
from agent.config.providers.azure import AzureSetup
from agent.config.providers.foundry import FoundrySetup
from agent.config.providers.gemini import GeminiSetup
from agent.config.providers.github import GitHubSetup
from agent.config.providers.local import LocalSetup
from agent.config.providers.openai import OpenAISetup

# Type alias for all provider setup types
ProviderSetupType = (
    LocalSetup
    | GitHubSetup
    | OpenAISetup
    | AnthropicSetup
    | GeminiSetup
    | AzureSetup
    | FoundrySetup
)

# Provider registry - maps provider names to setup implementations
PROVIDER_REGISTRY: dict[str, ProviderSetupType] = {
    "local": LocalSetup(),
    "github": GitHubSetup(),
    "openai": OpenAISetup(),
    "anthropic": AnthropicSetup(),
    "gemini": GeminiSetup(),
    "azure": AzureSetup(),
    "foundry": FoundrySetup(),
}


def get_provider_setup(provider: str) -> ProviderSetupType:
    """Get provider setup instance.

    Args:
        provider: Provider name

    Returns:
        Provider setup instance

    Raises:
        ValueError: If provider is not recognized
    """
    if provider not in PROVIDER_REGISTRY:
        valid_providers = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown provider: {provider}. Valid providers: {valid_providers}")

    return PROVIDER_REGISTRY[provider]
