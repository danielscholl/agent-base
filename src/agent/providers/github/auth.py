"""GitHub authentication utilities."""

import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


def get_github_token() -> str:
    """Get GitHub token from environment variable or gh CLI.

    Authentication priority:
    1. GITHUB_TOKEN environment variable (checked first)
    2. gh auth token command (fallback if gh CLI is available)

    Returns:
        GitHub token string

    Raises:
        ValueError: If neither authentication method is available or token is empty

    Examples:
        >>> # With GITHUB_TOKEN set
        >>> token = get_github_token()
        >>> # With gh CLI configured
        >>> token = get_github_token()
    """
    # First, check GITHUB_TOKEN environment variable
    env_token = os.getenv("GITHUB_TOKEN")
    if env_token:
        if not env_token.strip():
            raise ValueError(
                "GITHUB_TOKEN environment variable is set but empty. "
                "Please provide a valid GitHub token."
            )
        logger.debug("Using GitHub token from GITHUB_TOKEN environment variable")
        return env_token.strip()

    # Fallback to gh CLI authentication
    if not shutil.which("gh"):
        raise ValueError(
            "GitHub authentication failed: No GITHUB_TOKEN environment variable found "
            "and gh CLI is not installed.\n\n"
            "Please either:\n"
            "1. Set GITHUB_TOKEN environment variable: export GITHUB_TOKEN=ghp_...\n"
            "2. Install and configure gh CLI: gh auth login"
        )

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        cli_token = result.stdout.strip()

        if not cli_token:
            raise ValueError("gh auth token returned empty token. " "Please run: gh auth login")

        logger.debug("Using GitHub token from gh CLI (gh auth token)")
        return cli_token

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else "Unknown error"
        raise ValueError(
            f"Failed to get GitHub token from gh CLI: {stderr}\n\n"
            "Please either:\n"
            "1. Configure gh CLI: gh auth login\n"
            "2. Set GITHUB_TOKEN environment variable: export GITHUB_TOKEN=ghp_..."
        ) from e
    except subprocess.TimeoutExpired as e:
        raise ValueError(
            "gh auth token command timed out after 5 seconds.\n\n"
            "Please either:\n"
            "1. Try running: gh auth login\n"
            "2. Set GITHUB_TOKEN environment variable: export GITHUB_TOKEN=ghp_..."
        ) from e
