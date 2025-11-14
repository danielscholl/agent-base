"""Base protocol and utilities for provider configuration.

This module defines the ProviderSetup protocol that all provider
implementations must follow, enabling consistent configuration
across different LLM providers.
"""

import os
from typing import Any, Protocol

from rich.console import Console
from rich.prompt import Prompt


class ProviderSetup(Protocol):
    """Protocol for provider configuration setup.

    All provider implementations must provide these methods to enable
    consistent configuration through the registry pattern.
    """

    def detect_credentials(self) -> dict[str, Any]:
        """Detect credentials from environment variables.

        Returns:
            Dictionary of detected credentials (empty if none found)

        Example:
            >>> setup = OpenAISetup()
            >>> creds = setup.detect_credentials()
            >>> # {'api_key': 'sk-...', 'model': 'gpt-4o'}
        """

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for missing credentials interactively.

        Args:
            console: Rich console for formatted output
            detected: Previously detected credentials (may be empty)

        Returns:
            Complete credentials dictionary

        Example:
            >>> setup = OpenAISetup()
            >>> detected = setup.detect_credentials()
            >>> creds = setup.prompt_user(console, detected)
            >>> # Prompts for missing fields, uses detected for present ones
        """

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure provider with environment detection + user prompts.

        Main entry point that orchestrates credential detection and user input.
        This is the method called by the registry.

        Args:
            console: Rich console for formatted output

        Returns:
            Complete provider configuration dictionary

        Example:
            >>> setup = PROVIDER_REGISTRY["openai"]
            >>> config = setup.configure(console)
            >>> settings.providers.openai.update(config)
        """


def check_env_var(var_name: str, console: Console, display_name: str | None = None) -> str | None:
    """Check for environment variable and display status.

    Args:
        var_name: Environment variable name
        console: Rich console for output
        display_name: Display name (defaults to var_name)

    Returns:
        Environment variable value if found, None otherwise
    """
    value = os.getenv(var_name)
    if value:
        display = display_name or var_name
        console.print(f"[green]✓[/green] Found {display} in environment")
        console.print("  [dim]Using: [from environment][/dim]")
    return value


def prompt_if_missing(
    key: str,
    detected: dict[str, Any],
    prompt_text: str,
    password: bool = False,
    default: str | None = None,
) -> str:
    """Prompt user for value if not already detected.

    Args:
        key: Dictionary key to check
        detected: Dictionary of detected values
        prompt_text: Prompt text to display
        password: Whether to hide input
        default: Default value if any

    Returns:
        Value from detected dict or user input
    """
    if key in detected:
        return str(detected[key])

    if default:
        return Prompt.ask(prompt_text, password=password, default=default, show_default=True)

    return Prompt.ask(prompt_text, password=password)
