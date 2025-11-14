"""GitHub Models provider configuration setup."""

import os
import shutil
import subprocess
from typing import Any

from rich.console import Console
from rich.prompt import Confirm, Prompt

from agent.config.providers.base import prompt_if_missing


class GitHubSetup:
    """GitHub Models provider configuration handler."""

    def detect_credentials(self) -> dict[str, Any]:
        """Detect GitHub credentials from environment.

        Returns:
            Dictionary with token and model if found
        """
        credentials = {}

        token = os.getenv("GITHUB_TOKEN")
        if token:
            credentials["token"] = token

        model = os.getenv("GITHUB_MODEL")
        if model:
            credentials["model"] = model

        return credentials

    def _check_gh_cli(self, console: Console) -> bool:
        """Check if gh CLI is authenticated.

        Args:
            console: Rich console for output

        Returns:
            True if gh CLI is authenticated
        """
        gh_available = shutil.which("gh") is not None

        if not gh_available:
            console.print("\n[yellow]⚠[/yellow] gh CLI not found")
            console.print("[dim]Install: brew install gh && gh auth login[/dim]")
            console.print("[dim]Or set GITHUB_TOKEN: export GITHUB_TOKEN=ghp_...[/dim]")
            return False

        # Check authentication
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            if result.stdout.strip():
                console.print("\n[green]✓[/green] GitHub authentication ready (gh CLI)")
                return True
            else:
                console.print("\n[yellow]⚠[/yellow] gh CLI not authenticated")
                console.print("  [dim]Run 'gh auth login' to authenticate[/dim]")
                return False
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            console.print("\n[yellow]⚠[/yellow] Could not verify gh authentication")
            console.print("  [dim]Run 'gh auth login' to authenticate[/dim]")
            return False

    def _setup_github_org(self, console: Console, config: dict[str, Any]) -> None:
        """Configure GitHub organization for enterprise rate limits.

        Args:
            console: Rich console for output
            config: GitHub configuration to update
        """
        # Ask about organization
        if Confirm.ask("\nAre you using a GitHub organization account?", default=False):
            # Try to detect organization from gh CLI
            org_name = None
            try:
                from agent.providers.github.auth import get_github_org

                org_name = get_github_org()
            except Exception:
                # Organization detection failed; fallback to manual prompt below
                pass

            if org_name:
                console.print(f"[green]✓[/green] Detected organization: {org_name}")
                if Confirm.ask(f"Use {org_name}?", default=True):
                    config["org"] = org_name
                else:
                    org = Prompt.ask("Enter organization name")
                    config["org"] = org
            else:
                org = Prompt.ask("Enter organization name")
                config["org"] = org

    def prompt_user(self, console: Console, detected: dict[str, Any]) -> dict[str, Any]:
        """Prompt user for GitHub credentials.

        Args:
            console: Rich console for output
            detected: Previously detected credentials

        Returns:
            Complete GitHub configuration
        """
        # Check for environment token
        env_token = os.getenv("GITHUB_TOKEN")
        if env_token:
            console.print("\n[green]✓[/green] Found GITHUB_TOKEN in environment")
            console.print("  [dim]Using: [from environment][/dim]")
            detected["token"] = env_token
        else:
            # Check gh CLI authentication
            self._check_gh_cli(console)

        # Model selection
        model = prompt_if_missing("model", detected, "\nModel", default="gpt-4o-mini")

        result = {
            "model": model,
            "endpoint": "https://models.github.ai",
            "enabled": True,
        }

        if detected.get("token"):
            result["token"] = detected["token"]

        # Ask about organization
        self._setup_github_org(console, result)

        return result

    def configure(self, console: Console) -> dict[str, Any]:
        """Configure GitHub Models provider.

        Args:
            console: Rich console for output

        Returns:
            GitHub provider configuration
        """
        detected = self.detect_credentials()
        return self.prompt_user(console, detected)
