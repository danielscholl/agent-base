"""Unit tests for agent.cli module."""

import re
import subprocess
import sys

import pytest
import typer
from typer.testing import CliRunner

from agent.cli import app


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    This helper allows tests to focus on content rather than formatting.
    ANSI codes are used for colors and styling but aren't relevant for
    testing the presence of options and descriptions.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@pytest.mark.unit
@pytest.mark.cli
class TestCLIFramework:
    """Tests for CLI framework and structure."""

    def test_app_is_typer_instance(self):
        """Test that CLI app is a Typer instance."""
        assert isinstance(app, typer.Typer)

    def test_app_has_help_text(self):
        """Test that Typer app has help text configured."""
        assert app.info.help is not None
        assert "Agent" in app.info.help or "assistant" in app.info.help.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestCLIHelpOutput:
    """Tests for CLI help output format and content."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_help_flag_succeeds(self):
        """Test --help flag executes successfully."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_contains_usage_section(self):
        """Test help output contains usage information."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Typer includes "Usage:" in help output
        assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()

    def test_help_contains_options_section(self):
        """Test help output contains options section."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Rich formatting may use "Options" or "╭─ Options"
        assert "Options" in result.stdout or "options:" in result.stdout.lower()

    def test_help_contains_expected_options(self):
        """Test help output contains expected CLI options."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Strip ANSI codes to focus on content not formatting
        clean_output = strip_ansi(result.stdout)

        # Check for documented options
        assert "--prompt" in clean_output
        assert "--check" in clean_output
        assert "config" in clean_output  # config is now a subcommand, not an option
        assert "--version" in clean_output

    def test_help_contains_examples_section(self):
        """Test help output includes examples from docstring."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Typer should extract examples from docstring
        # Looking for "Examples:" section or actual example commands
        output = result.stdout.lower()
        has_examples = (
            "examples:" in output
            or "agent --check" in output
            or "agent -p" in output
            or "agent config" in output  # config is now a subcommand
        )
        assert has_examples, "Help output should contain examples from docstring"

    def test_help_shows_option_descriptions(self):
        """Test that options have descriptive help text."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Check that help descriptions are present
        assert "prompt" in result.stdout.lower()
        assert "health check" in result.stdout.lower() or "check" in result.stdout.lower()
        assert "config" in result.stdout.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestCLIRichFormatting:
    """Tests for Rich formatting in CLI output."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_help_has_rich_formatting_or_plain_text(self):
        """Test help output has either Rich formatting or plain text fallback."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

        # Check for Rich box characters or plain text format
        # Rich uses box drawing characters like ╭, ─, ╯
        # Plain text fallback should still be readable
        has_rich_boxes = any(char in result.stdout for char in ["╭", "─", "╯", "│"])
        has_plain_format = "Options:" in result.stdout

        # Should have either Rich formatting or plain text
        assert has_rich_boxes or has_plain_format


@pytest.mark.unit
@pytest.mark.cli
class TestCLIExecution:
    """Tests for CLI command execution."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    def test_version_flag(self):
        """Test --version flag displays version from package metadata."""
        result = self.runner.invoke(app, ["--version"])
        # Should exit successfully and show version
        assert result.exit_code == 0
        assert "version" in result.stdout.lower()
        # Verify it's not the old hardcoded version
        assert "0.1.0" not in result.stdout
        # Should show actual package version from pyproject.toml
        # Don't hardcode exact version, just verify it's not empty and looks like a version
        output = result.stdout.strip()
        assert output  # Not empty
        # Should contain something that looks like a version number

        assert re.search(r"\d+\.\d+\.\d+", output), f"Expected version number in: {output}"

    def test_check_flag_runs(self):
        """Test --check flag executes."""
        result = self.runner.invoke(app, ["--check"])
        # May succeed or fail depending on configuration
        # Just verify it runs and produces output
        assert result.stdout  # Should have some output

    def test_config_command_runs(self):
        """Test config command shows help."""
        result = self.runner.invoke(app, ["config"])
        # Should show config help
        assert result.exit_code == 0
        assert "Manage agent configuration" in result.stdout or "Commands" in result.stdout


@pytest.mark.unit
@pytest.mark.cli
class TestCLIIntegration:
    """Integration tests for CLI via subprocess."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_cli_help_via_subprocess(self):
        """Test CLI help output via subprocess (real execution)."""
        result = subprocess.run(
            ["uv", "run", "agent", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        # Strip ANSI codes to focus on content not formatting
        clean_output = strip_ansi(result.stdout)
        assert "agent" in clean_output.lower() or "Agent" in clean_output
        assert "--help" in clean_output

    def test_cli_version_via_subprocess(self):
        """Test CLI version output via subprocess."""
        result = subprocess.run(
            ["uv", "run", "agent", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        # Should display version information
        assert result.stdout.strip()  # Not empty


@pytest.mark.unit
@pytest.mark.cli
class TestCLIDocumentation:
    """Tests for CLI documentation consistency."""

    def test_docstring_has_examples(self):
        """Test main command has examples in docstring."""
        from agent.cli import main

        assert main.__doc__ is not None
        assert "Examples:" in main.__doc__

    def test_docstring_examples_format(self):
        """Test docstring examples follow expected format."""
        from agent.cli import main

        docstring = main.__doc__
        assert "agent --check" in docstring or "agent -p" in docstring
        # Examples should have comments (lines starting with #)
        assert "#" in docstring

    def test_all_options_have_help_text(self):
        """Test all Typer options have help parameter."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])

        # Strip ANSI codes and convert to lowercase for matching
        clean_output = strip_ansi(result.stdout)
        help_text = clean_output.lower()

        # Check that important options are documented
        assert "--prompt" in help_text or "-p" in help_text
        assert "--check" in help_text
        assert "config" in help_text  # config is now a subcommand, not an option
        assert "--verbose" in help_text
        assert "--continue" in help_text or "continue" in help_text

        # Verify help text has descriptions (not just option names)
        # Check for common description words
        description_indicators = ["show", "display", "run", "check", "enable", "output"]
        assert any(word in help_text for word in description_indicators)
