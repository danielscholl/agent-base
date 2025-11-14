"""Unit tests for agent.cli.utils module."""

import os
from unittest.mock import patch

import pytest
from rich.console import Console

from agent.cli.utils import get_console


@pytest.mark.unit
@pytest.mark.cli
class TestGetConsole:
    """Tests for get_console function."""

    def test_get_console_returns_console_instance(self):
        """Test that get_console returns a Console instance."""
        console = get_console()
        assert isinstance(console, Console)

    @patch("sys.stdout")
    @patch("agent.cli.utils.platform.system")
    def test_get_console_non_windows(self, mock_system, mock_stdout):
        """Test console creation on non-Windows systems."""
        mock_system.return_value = "Linux"
        mock_stdout.isatty.return_value = True

        console = get_console()

        assert isinstance(console, Console)
        # Verify platform.system() was called (function was executed)
        mock_system.assert_called()
        # On non-Windows path, Console() is called with no special arguments
        # Note: Rich's Console may still set legacy_windows based on actual OS
        # so we just verify the function returns a Console instance

    @patch("platform.system")
    @patch("sys.stdout")
    def test_get_console_windows_interactive(self, mock_stdout, mock_system):
        """Test console creation on Windows in interactive mode."""
        mock_system.return_value = "Windows"
        mock_stdout.isatty.return_value = True

        console = get_console()

        assert isinstance(console, Console)

    @patch("platform.system")
    @patch("sys.stdout")
    @patch("locale.getpreferredencoding")
    def test_get_console_windows_non_interactive_cp1252(
        self, mock_encoding, mock_stdout, mock_system
    ):
        """Test console creation on Windows in non-interactive mode with CP1252."""
        mock_system.return_value = "Windows"
        mock_stdout.isatty.return_value = False
        mock_encoding.return_value = "cp1252"

        # Clear the env var before test
        original_env = os.environ.get("PYTHONIOENCODING")
        if original_env:
            del os.environ["PYTHONIOENCODING"]

        try:
            console = get_console()

            assert isinstance(console, Console)
            # Should have set UTF-8 encoding
            assert os.environ.get("PYTHONIOENCODING") == "utf-8"
        finally:
            # Cleanup
            if "PYTHONIOENCODING" in os.environ:
                del os.environ["PYTHONIOENCODING"]
            if original_env:
                os.environ["PYTHONIOENCODING"] = original_env

    @patch("platform.system")
    @patch("sys.stdout")
    @patch("locale.getpreferredencoding")
    def test_get_console_windows_non_interactive_utf8(
        self, mock_encoding, mock_stdout, mock_system
    ):
        """Test console creation on Windows in non-interactive mode with UTF-8."""
        mock_system.return_value = "Windows"
        mock_stdout.isatty.return_value = False
        mock_encoding.return_value = "utf-8"

        console = get_console()

        assert isinstance(console, Console)

    @patch("platform.system")
    @patch("sys.stdout")
    @patch("locale.getpreferredencoding")
    def test_get_console_windows_encoding_exception(self, mock_encoding, mock_stdout, mock_system):
        """Test console creation when encoding detection fails."""
        mock_system.return_value = "Windows"
        mock_stdout.isatty.return_value = False
        mock_encoding.side_effect = Exception("Encoding error")

        console = get_console()

        assert isinstance(console, Console)
        # Should fallback to safe mode

    @patch("platform.system")
    @patch("sys.stdout")
    @patch("locale.getpreferredencoding")
    def test_get_console_windows_none_encoding(self, mock_encoding, mock_stdout, mock_system):
        """Test console creation when getpreferredencoding returns None."""
        mock_system.return_value = "Windows"
        mock_stdout.isatty.return_value = False
        mock_encoding.return_value = None

        # Clear the env var before test
        original_env = os.environ.get("PYTHONIOENCODING")
        if original_env:
            del os.environ["PYTHONIOENCODING"]

        try:
            console = get_console()

            assert isinstance(console, Console)
            # Should have set UTF-8 encoding since encoding is None (empty string after "or")
            assert os.environ.get("PYTHONIOENCODING") == "utf-8"
        finally:
            # Cleanup
            if "PYTHONIOENCODING" in os.environ:
                del os.environ["PYTHONIOENCODING"]
            if original_env:
                os.environ["PYTHONIOENCODING"] = original_env
