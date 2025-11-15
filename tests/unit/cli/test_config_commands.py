"""Tests for CLI configuration commands."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_console():
    """Mock console for testing."""
    with patch("agent.cli.config_commands.console") as mock:
        yield mock


@pytest.mark.unit
@pytest.mark.cli
def test_install_mem0_dependencies_uv_tool(mock_console):
    """Test mem0 dependency installation when running as uv tool."""
    from agent.cli.config_commands import _install_mem0_dependencies

    # Mock sys.executable to look like a uv tool
    with patch("sys.executable", "/Users/test/.local/share/uv/tools/agent-base/bin/python"):
        # Mock subprocess.run to simulate successful tool reinstall
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            result = _install_mem0_dependencies()

            # Should detect uv tool and use tool install
            assert result is True
            mock_run.assert_called_once()

            # Verify correct command was called
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "uv"
            assert call_args[1] == "tool"
            assert call_args[2] == "install"
            assert "--force" in call_args
            assert "--with" in call_args
            assert "mem0ai" in call_args
            assert "chromadb" in call_args
            assert "agent-base" in call_args


@pytest.mark.unit
@pytest.mark.cli
def test_install_mem0_dependencies_regular_install(mock_console):
    """Test mem0 dependency installation for regular (non-tool) installation."""
    from agent.cli.config_commands import _install_mem0_dependencies

    # Mock sys.executable to NOT look like a uv tool
    with patch("sys.executable", "/usr/bin/python3"):
        # Mock subprocess.run to simulate successful pip install
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

            result = _install_mem0_dependencies()

            # Should use uv pip install for regular installation
            assert result is True
            mock_run.assert_called_once()

            # Verify correct command was called
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "uv"
            assert call_args[1] == "pip"
            assert call_args[2] == "install"
            assert "mem0ai" in call_args
            assert "chromadb" in call_args


@pytest.mark.unit
@pytest.mark.cli
def test_install_mem0_dependencies_uv_tool_failure(mock_console):
    """Test mem0 dependency installation failure when running as uv tool."""
    from agent.cli.config_commands import _install_mem0_dependencies

    # Mock sys.executable to look like a uv tool
    with patch("sys.executable", "/Users/test/.local/share/uv/tools/agent-base/bin/python"):
        # Mock subprocess.run to simulate failed tool reinstall
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Installation failed", stdout="")

            result = _install_mem0_dependencies()

            # Should return False on failure
            assert result is False


@pytest.mark.unit
@pytest.mark.cli
def test_install_mem0_dependencies_regular_install_fallback_to_pip(mock_console):
    """Test fallback to pip when uv pip install fails."""
    from agent.cli.config_commands import _install_mem0_dependencies

    # Mock sys.executable to NOT look like a uv tool
    with patch("sys.executable", "/usr/bin/python3"):
        # Mock subprocess.run to first fail with uv, then succeed with pip
        with patch("subprocess.run") as mock_run:
            # First call (uv pip install) fails
            # Second call (pip install) succeeds
            mock_run.side_effect = [
                MagicMock(returncode=1, stderr="uv failed", stdout=""),
                MagicMock(returncode=0, stderr="", stdout=""),
            ]

            result = _install_mem0_dependencies()

            # Should succeed after falling back to pip
            assert result is True
            assert mock_run.call_count == 2

            # Second call should be to pip
            second_call_args = mock_run.call_args_list[1][0][0]
            assert second_call_args[0] == "pip"
            assert second_call_args[1] == "install"


@pytest.mark.unit
@pytest.mark.cli
def test_install_mem0_dependencies_timeout(mock_console):
    """Test timeout handling during installation."""
    from agent.cli.config_commands import _install_mem0_dependencies

    # Mock sys.executable to look like a uv tool
    with patch("sys.executable", "/Users/test/.local/share/uv/tools/agent-base/bin/python"):
        # Mock subprocess.run to raise TimeoutExpired
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="uv", timeout=300)

            result = _install_mem0_dependencies()

            # Should return False on timeout
            assert result is False
