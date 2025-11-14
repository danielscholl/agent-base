"""Anthropic provider configuration setup."""

import os
from typing import Any

from rich.console import Console

from agent.config.providers.base import check_env_var, prompt_if_missing


class AnthropicSetup:
    """Anthropic provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect Anthropic credentials from environment.

        Returns:
            Dictionary with api_key and model if found
        """
        credentials = {}

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            credentials["api_key"] = api_key

        model = os.getenv("ANTHROPIC_MODEL")
        if model:
            credentials["model"] = model

        return credentials

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for Anthropic credentials.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete Anthropic configuration
        """
        # Check environment and display status
        if not detected.get("api_key"):
            api_key = check_env_var("ANTHROPIC_API_KEY", console, "ANTHROPIC_API_KEY")
            if api_key:
                detected["api_key"] = api_key

        # Prompt for missing values
        api_key = prompt_if_missing(
            "api_key", detected, "Enter your Anthropic API key", password=True
        )

        model = prompt_if_missing("model", detected, "\nModel", default="claude-haiku-4-5-20251001")

        return {
            "api_key": api_key,
            "model": model,
            "enabled": True,
        }

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure Anthropic provider.

        Args:
            console: Rich console for output

        Returns:
            Anthropic provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
