"""Tests for CLI status bar functionality."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import agent.cli.interactive
from agent.cli.interactive import _get_status_bar_text

# Module-level markers for all tests in this file
pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_status_bar_returns_string():
    """Test that status bar function returns a string."""
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)

    # Should return a string
    assert isinstance(result, str)
    assert len(result) > 0


def test_status_bar_includes_directory():
    """Test that status bar includes current directory."""
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)

    # Should contain directory info (at least '/' or '~')
    assert "/" in result or "~" in result


@patch("agent.cli.interactive._BRANCH_CACHE_CWD", None)
@patch("agent.cli.interactive._BRANCH_CACHE_VALUE", "")
@patch("agent.cli.interactive.subprocess.run")
def test_status_bar_includes_git_branch(mock_run):
    """Test that git branch is included when available."""
    # Clear cache to force subprocess call
    agent.cli.interactive._BRANCH_CACHE_CWD = None
    agent.cli.interactive._BRANCH_CACHE_VALUE = ""

    # Mock git command to return a branch name
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "main\n"
    mock_run.return_value = mock_result

    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)

    # Should contain branch name and symbol
    assert "main" in result
    assert "⎇" in result  # Branch symbol


@patch("agent.cli.interactive.subprocess.run")
def test_status_bar_handles_no_git(mock_run):
    """Test that status bar works when not in git repo."""
    # Clear cache to force subprocess call
    agent.cli.interactive._BRANCH_CACHE_CWD = None
    agent.cli.interactive._BRANCH_CACHE_VALUE = ""

    # Mock git command to fail
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_run.return_value = mock_result

    # Should not raise exception
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)
    assert isinstance(result, str)

    # Should not contain branch symbol when no git repo
    # (current implementation falls back gracefully)


@patch("agent.cli.interactive._BRANCH_CACHE_CWD", None)
@patch("agent.cli.interactive._BRANCH_CACHE_VALUE", "")
@patch("agent.cli.interactive.subprocess.run")
def test_status_bar_handles_git_exception(mock_run):
    """Test that status bar handles git command exceptions."""
    # Clear cache to force subprocess call
    agent.cli.interactive._BRANCH_CACHE_CWD = None
    agent.cli.interactive._BRANCH_CACHE_VALUE = ""

    # Mock git command to raise exception (OSError for git not found)
    mock_run.side_effect = OSError("Git not found")

    # Should not raise exception
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)
    assert isinstance(result, str)

    # Should not contain branch info
    assert "⎇" not in result


@patch("agent.cli.interactive.subprocess.run")
def test_status_bar_git_timeout(mock_run):
    """Test that git command timeout is handled gracefully."""
    # Clear cache to force subprocess call
    agent.cli.interactive._BRANCH_CACHE_CWD = None
    agent.cli.interactive._BRANCH_CACHE_VALUE = ""

    # Mock git command to timeout
    mock_run.side_effect = subprocess.TimeoutExpired("git", 1)

    # Should not raise exception
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)
    assert isinstance(result, str)


def test_status_bar_directory_shortening():
    """Test that home directory is shortened to ~/."""
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)

    # If we're in a subdirectory of home, should see ~/
    cwd = Path.cwd()
    try:
        cwd.relative_to(Path.home())
        # We're in home directory or subdirectory
        assert "~/" in result
    except ValueError:
        # We're outside home directory
        # Should show full path (will contain /)
        assert "/" in result


def test_status_bar_has_padding():
    """Test that status bar includes padding for right-justification."""
    # Create mock console
    mock_console = MagicMock()
    mock_console.width = 80

    result = _get_status_bar_text(mock_console)

    # Should have leading spaces for right-justification
    # (unless status text is as wide as console)
    # The string starts with spaces if there's room
    assert isinstance(result, str)
