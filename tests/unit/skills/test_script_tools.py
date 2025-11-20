"""Unit tests for script wrapper tools."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agent.skills.script_tools import ScriptToolset


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.script_timeout = 60
    config.max_script_output = 1048576
    return config


@pytest.fixture
def sample_scripts():
    """Create sample script metadata."""
    return {
        "kalshi-markets": [
            {"name": "status", "path": Path("/fake/kalshi-markets/scripts/status.py")},
            {"name": "markets", "path": Path("/fake/kalshi-markets/scripts/markets.py")},
        ],
        "hello-extended": [
            {"name": "greeting", "path": Path("/fake/hello-extended/scripts/greeting.py")},
        ],
    }


class TestScriptToolset:
    """Test ScriptToolset class."""

    def test_init(self, mock_config, sample_scripts):
        """Should initialize with config and scripts."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        assert toolset.config == mock_config
        assert toolset.scripts == sample_scripts
        assert toolset.timeout == 60
        assert toolset.max_output == 1048576

    def test_get_tools(self, mock_config, sample_scripts):
        """Should return list of three tools."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        tools = toolset.get_tools()
        assert len(tools) == 3
        assert toolset.script_list in tools
        assert toolset.script_help in tools
        assert toolset.script_run in tools

    def test_script_count(self, mock_config, sample_scripts):
        """Should count total scripts across all skills."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        assert toolset.script_count == 3  # 2 from kalshi + 1 from hello


class TestScriptList:
    """Test script_list tool."""

    @pytest.mark.asyncio
    async def test_list_all_scripts(self, mock_config, sample_scripts):
        """Should list all scripts across all skills."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        result = await toolset.script_list()

        assert result["success"] is True
        assert "kalshi-markets" in result["result"]
        assert "hello-extended" in result["result"]
        assert len(result["result"]["kalshi-markets"]) == 2
        assert "3 scripts" in result["message"]

    @pytest.mark.asyncio
    async def test_list_specific_skill(self, mock_config, sample_scripts):
        """Should list scripts for a specific skill."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        result = await toolset.script_list(skill_name="kalshi-markets")

        assert result["success"] is True
        assert "kalshi-markets" in result["result"]
        assert len(result["result"]["kalshi-markets"]) == 2
        assert "2 scripts" in result["message"]

    @pytest.mark.asyncio
    async def test_list_nonexistent_skill(self, mock_config, sample_scripts):
        """Should return error for nonexistent skill."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        result = await toolset.script_list(skill_name="nonexistent")

        assert result["success"] is False
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_list_case_insensitive(self, mock_config, sample_scripts):
        """Should handle case-insensitive skill names."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        result = await toolset.script_list(skill_name="Kalshi-Markets")

        assert result["success"] is True
        assert "kalshi-markets" in result["result"]


class TestScriptHelp:
    """Test script_help tool."""

    @pytest.mark.asyncio
    async def test_get_help_success(self, mock_config, sample_scripts):
        """Should execute script with --help and return output."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"Usage: status.py [OPTIONS]", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await toolset.script_help("kalshi-markets", "status")

        assert result["success"] is True
        assert "Usage: status.py" in result["result"]["help_text"]

    @pytest.mark.asyncio
    async def test_get_help_script_not_found(self, mock_config, sample_scripts):
        """Should return error if script not found."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        result = await toolset.script_help("kalshi-markets", "nonexistent")

        assert result["success"] is False
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_help_timeout(self, mock_config, sample_scripts):
        """Should handle timeout."""
        toolset = ScriptToolset(mock_config, sample_scripts)
        toolset.timeout = 0.1  # Very short timeout

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=TimeoutError())
        mock_process.kill = MagicMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("asyncio.wait_for", side_effect=TimeoutError()):
                result = await toolset.script_help("kalshi-markets", "status")

        assert result["success"] is False
        assert result["error"] == "timeout"


class TestScriptRun:
    """Test script_run tool."""

    @pytest.mark.asyncio
    async def test_run_script_json_success(self, mock_config, sample_scripts):
        """Should execute script and parse JSON output."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        output_data = {"status": "operational", "timestamp": "2025-01-01T00:00:00Z"}
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(json.dumps(output_data).encode(), b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await toolset.script_run("kalshi-markets", "status")

        assert result["success"] is True
        assert result["result"] == output_data

    @pytest.mark.asyncio
    async def test_run_script_plain_text(self, mock_config, sample_scripts):
        """Should return plain text if json=False."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"Plain text output", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await toolset.script_run("kalshi-markets", "status", json_output=False)

        assert result["success"] is True
        assert result["result"] == "Plain text output"

    @pytest.mark.asyncio
    async def test_run_script_with_args(self, mock_config, sample_scripts):
        """Should pass arguments to script."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b'{"result": "ok"}', b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            await toolset.script_run("kalshi-markets", "status", args=["--verbose", "--debug"])

        # Verify args were passed
        call_args = mock_exec.call_args[0]
        assert "--verbose" in call_args
        assert "--debug" in call_args

    @pytest.mark.asyncio
    async def test_run_script_args_too_many(self, mock_config, sample_scripts):
        """Should reject too many arguments."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        too_many_args = ["arg"] * 101  # Max is 100
        result = await toolset.script_run("kalshi-markets", "status", args=too_many_args)

        assert result["success"] is False
        assert result["error"] == "args_too_large"

    @pytest.mark.asyncio
    async def test_run_script_invalid_json(self, mock_config, sample_scripts):
        """Should return parse error for invalid JSON."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"Not JSON", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await toolset.script_run("kalshi-markets", "status", json_output=True)

        assert result["success"] is False
        assert result["error"] == "parse_error"

    @pytest.mark.asyncio
    async def test_run_script_nonzero_exit(self, mock_config, sample_scripts):
        """Should handle non-zero exit code."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error message"))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await toolset.script_run("kalshi-markets", "status")

        assert result["success"] is False
        assert result["error"] == "execution_failed"


class TestNameNormalization:
    """Test name normalization in script tools."""

    @pytest.mark.asyncio
    async def test_skill_name_normalization(self, mock_config, sample_scripts):
        """Should handle various skill name formats."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        # All these should work (case-insensitive, hyphen/underscore equivalent)
        result1 = await toolset.script_list(skill_name="kalshi-markets")
        result2 = await toolset.script_list(skill_name="Kalshi-Markets")
        result3 = await toolset.script_list(skill_name="KALSHI-MARKETS")

        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True

    @pytest.mark.asyncio
    async def test_script_name_normalization(self, mock_config, sample_scripts):
        """Should handle script names with/without .py extension."""
        toolset = ScriptToolset(mock_config, sample_scripts)

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"Help text", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            # Both formats should work
            result1 = await toolset.script_help("kalshi-markets", "status")
            result2 = await toolset.script_help("kalshi-markets", "status.py")

        assert result1["success"] is True
        assert result2["success"] is True
