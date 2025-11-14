"""Google Gemini provider configuration setup."""

import os
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt


class GeminiSetup:
    """Google Gemini provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect Gemini credentials from environment.

        Returns:
            Dictionary with api_key/vertex config and model if found
        """
        credentials: dict[str, Any] = {}

        # Check for Vertex AI configuration
        use_vertex = os.getenv("GEMINI_USE_VERTEXAI", "false").lower() == "true"
        if use_vertex:
            credentials["use_vertexai"] = True
            project_id = os.getenv("GEMINI_PROJECT_ID")
            if project_id:
                credentials["project_id"] = project_id
            location = os.getenv("GEMINI_LOCATION")
            if location:
                credentials["location"] = location

        # Check for API key
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            credentials["api_key"] = api_key

        # Check for model
        model = os.getenv("GEMINI_MODEL")
        if model:
            credentials["model"] = model

        return credentials

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for Gemini credentials.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete Gemini configuration
        """
        # Check environment
        env_use_vertex = os.getenv("GEMINI_USE_VERTEXAI", "false").lower() == "true"
        env_key = os.getenv("GEMINI_API_KEY")
        env_project = os.getenv("GEMINI_PROJECT_ID")
        env_location = os.getenv("GEMINI_LOCATION")

        if env_use_vertex and env_project:
            console.print("\n[green]✓[/green] Found Gemini Vertex AI config in environment")
            console.print(f"  [dim]Project: {env_project}[/dim]")
            console.print(f"  [dim]Location: {env_location or 'us-central1'}[/dim]")

            model = Prompt.ask("\nModel", default="gemini-2.0-flash-exp", show_default=True)

            return {
                "use_vertexai": True,
                "project_id": env_project,
                "location": env_location or "us-central1",
                "model": model,
                "enabled": True,
            }
        elif env_key:
            console.print("\n[green]✓[/green] Found GEMINI_API_KEY in environment")
            console.print("  [dim]Using: [from environment][/dim]")

            model = Prompt.ask("\nModel", default="gemini-2.0-flash-exp", show_default=True)

            return {
                "api_key": env_key,
                "model": model,
                "enabled": True,
            }
        else:
            # No environment config - prompt user
            use_vertex = Confirm.ask("\nUse Vertex AI instead of Gemini API?", default=False)

            if use_vertex:
                project_id = Prompt.ask("Enter your GCP project ID")
                location = Prompt.ask("Enter your GCP location", default="us-central1")
                model = Prompt.ask("\nModel", default="gemini-2.0-flash-exp", show_default=True)

                return {
                    "use_vertexai": True,
                    "project_id": project_id,
                    "location": location,
                    "model": model,
                    "enabled": True,
                }
            else:
                api_key = Prompt.ask("Enter your Gemini API key", password=True)
                model = Prompt.ask("\nModel", default="gemini-2.0-flash-exp", show_default=True)

                return {
                    "api_key": api_key,
                    "model": model,
                    "enabled": True,
                }

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure Google Gemini provider.

        Args:
            console: Rich console for output

        Returns:
            Gemini provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
