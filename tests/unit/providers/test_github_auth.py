"""Unit tests for GitHub authentication utilities."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from agent.providers.github.auth import get_github_token


class TestGetGitHubToken:
    """Test get_github_token function."""

    def test_token_from_environment_variable(self, monkeypatch):
        """Test token retrieval from GITHUB_TOKEN environment variable."""
        test_token = "ghp_test_token_from_env"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)

        token = get_github_token()

        assert token == test_token

    def test_token_from_environment_variable_with_whitespace(self, monkeypatch):
        """Test token from env var is stripped of whitespace."""
        test_token = "  ghp_test_token_with_spaces  "
        monkeypatch.setenv("GITHUB_TOKEN", test_token)

        token = get_github_token()

        assert token == test_token.strip()
        assert token == "ghp_test_token_with_spaces"

    def test_empty_environment_variable_raises_error(self, monkeypatch):
        """Test that empty GITHUB_TOKEN raises ValueError."""
        monkeypatch.setenv("GITHUB_TOKEN", "   ")

        with pytest.raises(ValueError) as exc_info:
            get_github_token()

        assert "empty" in str(exc_info.value).lower()
        assert "GITHUB_TOKEN" in str(exc_info.value)

    @patch("agent.providers.github.auth.shutil.which")
    @patch("agent.providers.github.auth.subprocess.run")
    def test_token_from_gh_cli(self, mock_run, mock_which, monkeypatch):
        """Test token retrieval from gh auth token command."""
        # Ensure GITHUB_TOKEN is not set
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Mock gh CLI availability
        mock_which.return_value = "/usr/local/bin/gh"

        # Mock successful gh auth token command
        test_token = "ghp_test_token_from_cli"
        mock_run.return_value = MagicMock(
            stdout=test_token,
            stderr="",
            returncode=0,
        )

        token = get_github_token()

        assert token == test_token
        mock_which.assert_called_once_with("gh")
        mock_run.assert_called_once_with(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )

    @patch("agent.providers.github.auth.shutil.which")
    @patch("agent.providers.github.auth.subprocess.run")
    def test_token_from_gh_cli_with_whitespace(self, mock_run, mock_which, monkeypatch):
        """Test token from gh CLI is stripped of whitespace."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_which.return_value = "/usr/local/bin/gh"

        test_token = "  ghp_test_token_with_spaces\n"
        mock_run.return_value = MagicMock(
            stdout=test_token,
            stderr="",
            returncode=0,
        )

        token = get_github_token()

        assert token == test_token.strip()
        assert token == "ghp_test_token_with_spaces"

    @patch("agent.providers.github.auth.shutil.which")
    def test_no_gh_cli_installed_raises_error(self, mock_which, monkeypatch):
        """Test that missing gh CLI raises ValueError when GITHUB_TOKEN not set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_which.return_value = None

        with pytest.raises(ValueError) as exc_info:
            get_github_token()

        error_msg = str(exc_info.value)
        assert "gh CLI is not installed" in error_msg
        assert "GITHUB_TOKEN" in error_msg
        assert "gh auth login" in error_msg

    @patch("agent.providers.github.auth.shutil.which")
    @patch("agent.providers.github.auth.subprocess.run")
    def test_gh_cli_returns_empty_token(self, mock_run, mock_which, monkeypatch):
        """Test that empty token from gh CLI raises ValueError."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_which.return_value = "/usr/local/bin/gh"

        mock_run.return_value = MagicMock(
            stdout="",
            stderr="",
            returncode=0,
        )

        with pytest.raises(ValueError) as exc_info:
            get_github_token()

        error_msg = str(exc_info.value)
        assert "empty token" in error_msg.lower()
        assert "gh auth login" in error_msg

    @patch("agent.providers.github.auth.shutil.which")
    @patch("agent.providers.github.auth.subprocess.run")
    def test_gh_cli_command_fails(self, mock_run, mock_which, monkeypatch):
        """Test that gh CLI command failure raises ValueError."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_which.return_value = "/usr/local/bin/gh"

        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["gh", "auth", "token"],
            stderr="error: not logged in",
        )

        with pytest.raises(ValueError) as exc_info:
            get_github_token()

        error_msg = str(exc_info.value)
        assert "Failed to get GitHub token" in error_msg
        assert "gh auth login" in error_msg

    @patch("agent.providers.github.auth.shutil.which")
    @patch("agent.providers.github.auth.subprocess.run")
    def test_gh_cli_command_timeout(self, mock_run, mock_which, monkeypatch):
        """Test that gh CLI command timeout raises ValueError."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        mock_which.return_value = "/usr/local/bin/gh"

        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["gh", "auth", "token"],
            timeout=5,
        )

        with pytest.raises(ValueError) as exc_info:
            get_github_token()

        error_msg = str(exc_info.value)
        assert "timed out" in error_msg.lower()
        assert "5 seconds" in error_msg

    def test_environment_variable_takes_precedence(self, monkeypatch):
        """Test that GITHUB_TOKEN env var takes precedence over gh CLI."""
        test_token = "ghp_env_token"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)

        # Even if gh CLI is available, env var should be used
        with patch("agent.providers.github.auth.shutil.which") as mock_which:
            mock_which.return_value = "/usr/local/bin/gh"

            token = get_github_token()

            # Should not call gh CLI since env var is set
            assert token == test_token
            # which() should not even be called since we found env var
            mock_which.assert_not_called()
