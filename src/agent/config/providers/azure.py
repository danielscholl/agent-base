"""Azure OpenAI provider configuration setup."""

import os
from typing import Any

from rich.console import Console
from rich.prompt import Prompt

from agent.config.providers.base import check_env_var


class AzureSetup:
    """Azure OpenAI provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect Azure OpenAI credentials from environment.

        Returns:
            Dictionary with endpoint, deployment, and optional api_key
        """
        credentials = {}

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if endpoint:
            credentials["endpoint"] = endpoint

        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        if deployment:
            credentials["deployment"] = deployment

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if api_key:
            credentials["api_key"] = api_key

        return credentials

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for Azure OpenAI credentials.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete Azure OpenAI configuration
        """
        # Check environment variables
        env_endpoint = check_env_var("AZURE_OPENAI_ENDPOINT", console, "Azure OpenAI config")
        env_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        env_key = os.getenv("AZURE_OPENAI_API_KEY")

        if env_endpoint and env_deployment:
            console.print(f"  [dim]Endpoint: {env_endpoint}[/dim]")
            console.print(f"  [dim]Deployment: {env_deployment}[/dim]")
            if env_key:
                console.print("  [dim]API Key: [from environment][/dim]")

            result = {
                "endpoint": env_endpoint,
                "deployment": env_deployment,
                "enabled": True,
            }
            if env_key:
                result["api_key"] = env_key
            return result

        # Prompt for values
        endpoint = Prompt.ask("Enter your Azure OpenAI endpoint")
        deployment = Prompt.ask("Enter your deployment name")
        api_key = Prompt.ask("Enter your API key (or press Enter to use Azure CLI)", password=True)

        result = {
            "endpoint": endpoint,
            "deployment": deployment,
            "enabled": True,
        }
        if api_key:
            result["api_key"] = api_key

        return result

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure Azure OpenAI provider.

        Args:
            console: Rich console for output

        Returns:
            Azure OpenAI provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
