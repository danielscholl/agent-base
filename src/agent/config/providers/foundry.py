"""Azure AI Foundry provider configuration setup."""

import os
from typing import Any

from rich.console import Console
from rich.prompt import Prompt


class FoundrySetup:
    """Azure AI Foundry provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect Azure AI Foundry credentials from environment.

        Returns:
            Dictionary with project_endpoint and model_deployment if found
        """
        credentials = {}

        endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
        if endpoint:
            credentials["project_endpoint"] = endpoint

        deployment = os.getenv("AZURE_MODEL_DEPLOYMENT")
        if deployment:
            credentials["model_deployment"] = deployment

        return credentials

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for Azure AI Foundry credentials.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete Azure AI Foundry configuration
        """
        # Check environment variables
        env_endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
        env_deployment = os.getenv("AZURE_MODEL_DEPLOYMENT")

        if env_endpoint and env_deployment:
            console.print("\n[green]✓[/green] Found Azure AI Foundry config in environment")
            console.print(f"  [dim]Endpoint: {env_endpoint}[/dim]")
            console.print(f"  [dim]Deployment: {env_deployment}[/dim]")

            return {
                "project_endpoint": env_endpoint,
                "model_deployment": env_deployment,
                "enabled": True,
            }

        # Prompt for values
        endpoint = Prompt.ask("Enter your Azure AI Foundry project endpoint")
        deployment = Prompt.ask("Enter your model deployment name")

        return {
            "project_endpoint": endpoint,
            "model_deployment": deployment,
            "enabled": True,
        }

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure Azure AI Foundry provider.

        Args:
            console: Rich console for output

        Returns:
            Azure AI Foundry provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
