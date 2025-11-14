"""OpenAI provider configuration setup."""

import os
from typing import Any

from rich.console import Console

from agent.config.providers.base import check_env_var, prompt_if_missing


class OpenAISetup:
    """OpenAI provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect OpenAI credentials from environment.

        Returns:
            Dictionary with api_key and model if found
        """
        credentials = {}

        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            credentials["api_key"] = api_key

        model = os.getenv("OPENAI_MODEL")
        if model:
            credentials["model"] = model

        return credentials

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for OpenAI credentials.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete OpenAI configuration
        """
        # Check environment and display status
        if not detected.get("api_key"):
            api_key = check_env_var("OPENAI_API_KEY", console, "OPENAI_API_KEY")
            if api_key:
                detected["api_key"] = api_key

        # Prompt for missing values
        api_key = prompt_if_missing("api_key", detected, "Enter your OpenAI API key", password=True)

        model = prompt_if_missing("model", detected, "\nModel", default="gpt-5-mini")

        return {
            "api_key": api_key,
            "model": model,
            "enabled": True,
        }

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure OpenAI provider.

        Args:
            console: Rich console for output

        Returns:
            OpenAI provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
