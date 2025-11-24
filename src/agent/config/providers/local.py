"""Local Docker provider configuration setup."""

import os
import subprocess
from typing import Any

from rich.console import Console

from agent.config.providers.base import prompt_if_missing

# Timeout constants for Docker operations
DOCKER_ENABLE_TIMEOUT = 30  # seconds
MODEL_CHECK_TIMEOUT = 5  # seconds
MODEL_PULL_TIMEOUT = 1200  # 20 minutes

# Optional import for model checking
try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment, unused-ignore]


class LocalSetup:
    """Local Docker provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect local Docker configuration.

        Returns:
            Dictionary with model if found
        """
        credentials = {}

        model = os.getenv("LOCAL_MODEL")
        if model:
            credentials["model"] = model

        return credentials

    def _setup_docker_model_runner(self, console: Console) -> None:
        """Set up Docker Model Runner and pull phi4 model if needed.

        Args:
            console: Rich console for output
        """
        console.print("\n[bold]Setting up Docker Model Runner...[/bold]")

        # Enable model runner
        console.print("Enabling Docker Model Runner...")
        try:
            result = subprocess.run(
                ["docker", "desktop", "enable", "model-runner", "--tcp=12434"],
                capture_output=True,
                text=True,
                timeout=DOCKER_ENABLE_TIMEOUT,
            )
            if result.returncode == 0:
                console.print("[green]✓[/green] Model Runner enabled")
            else:
                console.print(f"[yellow]⚠[/yellow] Model Runner enable: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠[/yellow] Timeout enabling model runner")
        except FileNotFoundError:
            console.print("[red]✗[/red] Docker not found. Please install Docker Desktop.")
            return

        # Check for existing models
        console.print("Checking for models...")
        if requests is None:
            console.print("[yellow]⚠[/yellow] requests library not available, skipping model check")
            return

        try:
            response = requests.get(
                "http://localhost:12434/engines/llama.cpp/v1/models", timeout=MODEL_CHECK_TIMEOUT
            )
            if response.status_code == 200:
                models = response.json().get("data", [])
                if models:
                    console.print(f"[green]✓[/green] Found {len(models)} model(s)")
                else:
                    # No models - pull phi4
                    console.print(
                        "\n[bold yellow]No models found. Pulling phi4 model (9GB)...[/bold yellow]"
                    )
                    console.print(
                        "[dim]This may take 10-20 minutes depending on your connection.[/dim]\n"
                    )

                    # Run with live output so user sees progress
                    try:
                        result = subprocess.run(
                            ["docker", "model", "pull", "phi4"],
                            timeout=MODEL_PULL_TIMEOUT,
                            text=True,
                        )
                        if result.returncode == 0:
                            console.print("\n[green]✓[/green] phi4 model pulled successfully")
                        else:
                            console.print(
                                f"\n[yellow]⚠[/yellow] Model pull exited with code {result.returncode}"
                            )
                            console.print(
                                "[dim]You can manually pull with: docker model pull phi4[/dim]"
                            )
                    except subprocess.TimeoutExpired:
                        console.print("\n[red]✗[/red] Model pull timed out after 20 minutes")
                        console.print(
                            "[dim]You can manually pull with: docker model pull phi4[/dim]"
                        )
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Model pull cancelled.[/yellow]")
                        console.print(
                            "[dim]You can manually pull later with: docker model pull phi4[/dim]"
                        )
            else:
                console.print(
                    "[yellow]⚠[/yellow] Model Runner not responding. It may need a moment to start."
                )
        except requests.RequestException:
            console.print("[yellow]⚠[/yellow] Model Runner not responding yet")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not check models: {e}")

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for local Docker configuration.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete local provider configuration
        """
        # Setup Docker Model Runner
        self._setup_docker_model_runner(console)

        # Prompt for model
        model = prompt_if_missing("model", detected, "\nModel", default="ai/phi4")

        return {
            "model": model,
            "enabled": True,
        }

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure local Docker provider.

        Args:
            console: Rich console for output

        Returns:
            Local provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
