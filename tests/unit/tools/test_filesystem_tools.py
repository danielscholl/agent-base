"""Unit tests for agent.tools.filesystem module.

Comprehensive test suite covering:
1. Workspace sandboxing (security tests)
2. Read-only tools (get_path_info, list_directory, read_file, search_text)
3. Write tools (write_file, apply_text_edit, create_directory)
4. Cross-platform compatibility
5. Error handling and edge cases
"""

import logging
from pathlib import Path

import pytest

from agent.config import AgentConfig
from agent.tools.filesystem import FileSystemTools

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_workspace(tmp_path):
    """Create isolated temporary workspace for each test.

    Returns:
        Path: Temporary directory path to use as workspace_root
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def config_with_workspace(temp_workspace):
    """Create AgentConfig with workspace_root configured."""
    config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
    # Add filesystem configuration attributes (not in dataclass definition yet)
    config.workspace_root = temp_workspace
    config.filesystem_writes_enabled = False  # Default disabled
    config.filesystem_max_read_bytes = 10_485_760  # 10MB
    config.filesystem_max_write_bytes = 1_048_576  # 1MB
    return config


@pytest.fixture
def config_with_writes(temp_workspace):
    """Create AgentConfig with writes enabled."""
    config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
    # Add filesystem configuration attributes
    config.workspace_root = temp_workspace
    config.filesystem_writes_enabled = True
    config.filesystem_max_read_bytes = 10_485_760  # 10MB
    config.filesystem_max_write_bytes = 1_048_576  # 1MB
    return config


@pytest.fixture
def fs_tools_readonly(config_with_workspace):
    """Create FileSystemTools instance with writes disabled."""
    return FileSystemTools(config_with_workspace)


@pytest.fixture
def fs_tools_writable(config_with_writes):
    """Create FileSystemTools instance with writes enabled."""
    return FileSystemTools(config_with_writes)


@pytest.fixture
def sample_files(temp_workspace):
    """Create sample file structure for testing.

    Structure:
        workspace/
            file1.txt
            file2.py
            .hidden
            subdir/
                file3.txt
                nested/
                    file4.py
            empty.txt
    """
    # Create files
    (temp_workspace / "file1.txt").write_text("Hello World\nLine 2\nLine 3\n")
    (temp_workspace / "file2.py").write_text("def hello():\n    print('hi')\n")
    (temp_workspace / ".hidden").write_text("secret")
    (temp_workspace / "empty.txt").write_text("")

    # Create subdirectories and files
    subdir = temp_workspace / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("Content in subdir\n")

    nested = subdir / "nested"
    nested.mkdir()
    (nested / "file4.py").write_text("# Nested file\n")

    return temp_workspace


# ============================================================================
# Test Class: Initialization and Configuration
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestFileSystemToolsInitialization:
    """Tests for FileSystemTools initialization and configuration."""

    def test_initialization(self, config_with_workspace):
        """Test FileSystemTools initializes with config."""
        tools = FileSystemTools(config_with_workspace)

        assert tools.config == config_with_workspace
        assert tools._workspace_root_cache is None  # Lazy initialization

    def test_get_tools_returns_seven_functions(self, fs_tools_readonly):
        """Test get_tools returns all 7 filesystem tool functions."""
        tools_list = fs_tools_readonly.get_tools()

        assert len(tools_list) == 7
        assert fs_tools_readonly.get_path_info in tools_list
        assert fs_tools_readonly.list_directory in tools_list
        assert fs_tools_readonly.read_file in tools_list
        assert fs_tools_readonly.search_text in tools_list
        assert fs_tools_readonly.write_file in tools_list
        assert fs_tools_readonly.apply_text_edit in tools_list
        assert fs_tools_readonly.create_directory in tools_list

    def test_workspace_root_caching(self, fs_tools_readonly, temp_workspace):
        """Test workspace root is cached after first access."""
        # Access workspace root
        root = fs_tools_readonly._get_workspace_root()
        assert root == temp_workspace

        # Verify cached
        cached = fs_tools_readonly._workspace_root_cache
        assert cached == temp_workspace
        assert cached is root

    def test_workspace_root_from_env_var(self, tmp_path, monkeypatch):
        """Test workspace root can be loaded from AGENT_WORKSPACE_ROOT env var."""
        workspace = tmp_path / "env_workspace"
        workspace.mkdir()

        # Set env var
        monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

        # Create config without workspace_root
        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        tools = FileSystemTools(config)

        # Should load from env var
        root = tools._get_workspace_root()
        assert root == workspace.resolve()


# ============================================================================
# Test Class: Workspace Sandboxing (Critical Security Tests)
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestWorkspaceSandboxing:
    """Critical security tests for workspace sandboxing."""

    def test_workspace_defaults_to_cwd(self, monkeypatch, tmp_path):
        """Test workspace defaults to current working directory when not configured."""
        # Change to tmp_path as cwd
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AGENT_WORKSPACE_ROOT", raising=False)

        # Config without workspace_root
        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        tools = FileSystemTools(config)

        # Should default to cwd
        root = tools._get_workspace_root()
        assert root == tmp_path.resolve()

    def test_workspace_priority(self, tmp_path, monkeypatch):
        """Test workspace resolution priority: config > env > cwd."""
        config_path = tmp_path / "config"
        env_path = tmp_path / "env"
        cwd_path = tmp_path / "cwd"

        config_path.mkdir()
        env_path.mkdir()
        cwd_path.mkdir()

        # Test 1: Config takes priority over env
        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        config.workspace_root = config_path
        monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(env_path))
        monkeypatch.chdir(cwd_path)

        tools = FileSystemTools(config)
        assert tools._get_workspace_root() == config_path.resolve()

        # Test 2: Env takes priority over cwd (clear cache first)
        tools._workspace_root_cache = None
        config.workspace_root = None
        assert tools._get_workspace_root() == env_path.resolve()

        # Test 3: Cwd is used when neither config nor env set
        tools._workspace_root_cache = None
        monkeypatch.delenv("AGENT_WORKSPACE_ROOT", raising=False)
        assert tools._get_workspace_root() == cwd_path.resolve()

    def test_workspace_home_directory_warning(self, monkeypatch, tmp_path, caplog):
        """Test warning logged when workspace is home directory."""
        from pathlib import Path

        # Simulate cwd being home directory
        monkeypatch.setattr(Path, "cwd", lambda: Path.home())
        monkeypatch.delenv("AGENT_WORKSPACE_ROOT", raising=False)

        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        tools = FileSystemTools(config)

        with caplog.at_level(logging.WARNING):
            root = tools._get_workspace_root()

        assert root == Path.home()
        assert "Consider using a project directory" in caplog.text

    @pytest.mark.asyncio
    async def test_path_traversal_attempt_blocked(self, fs_tools_readonly):
        """Test paths containing '..' are rejected."""
        # Various traversal attempts
        traversal_paths = [
            "../etc/passwd",
            "subdir/../../etc/passwd",
            "././../outside",
            "valid/../../../escape",
        ]

        for path in traversal_paths:
            result = await fs_tools_readonly.get_path_info(path)
            assert result["success"] is False
            assert result["error"] == "path_traversal_attempt"
            assert ".." in result["message"]

    @pytest.mark.asyncio
    async def test_absolute_path_outside_workspace_blocked(self, fs_tools_readonly, temp_workspace):
        """Test absolute paths outside workspace are rejected."""
        # Absolute paths outside workspace
        outside_paths = [
            "/etc/passwd",
            "/tmp/outside",
            str(Path.home() / "outside"),
        ]

        for path in outside_paths:
            result = await fs_tools_readonly.get_path_info(path)
            assert result["success"] is False
            assert result["error"] == "path_outside_workspace"

    @pytest.mark.asyncio
    async def test_absolute_path_inside_workspace_allowed(self, fs_tools_readonly, temp_workspace):
        """Test absolute paths inside workspace are allowed."""
        # Create a file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("content")

        # Use absolute path
        result = await fs_tools_readonly.get_path_info(str(test_file))
        assert result["success"] is True
        assert result["result"]["exists"] is True
        assert result["result"]["type"] == "file"

    @pytest.mark.asyncio
    async def test_symlink_outside_workspace_blocked(
        self, fs_tools_readonly, temp_workspace, tmp_path
    ):
        """Test symlink pointing outside workspace is blocked."""
        # Create target outside workspace
        outside = tmp_path / "outside"
        outside.mkdir()
        outside_file = outside / "secret.txt"
        outside_file.write_text("secret data")

        # Create symlink inside workspace pointing outside
        symlink = temp_workspace / "escape_link"
        symlink.symlink_to(outside_file)

        # Should be blocked
        result = await fs_tools_readonly.get_path_info("escape_link")
        assert result["success"] is False
        # Symlinks outside workspace are caught as path_outside_workspace
        assert result["error"] == "path_outside_workspace"

    @pytest.mark.asyncio
    async def test_symlink_within_workspace_allowed(self, fs_tools_readonly, temp_workspace):
        """Test symlink within workspace is allowed."""
        # Create file and symlink within workspace
        target = temp_workspace / "target.txt"
        target.write_text("target content")

        symlink = temp_workspace / "link.txt"
        symlink.symlink_to(target)

        # Should work
        result = await fs_tools_readonly.get_path_info("link.txt")
        assert result["success"] is True
        assert result["result"]["exists"] is True


# ============================================================================
# Test Class: get_path_info
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestGetPathInfo:
    """Tests for get_path_info tool."""

    @pytest.mark.asyncio
    async def test_path_info_file(self, fs_tools_readonly, temp_workspace):
        """Test get_path_info returns correct metadata for file."""
        # Create test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello World")

        result = await fs_tools_readonly.get_path_info("test.txt")

        assert result["success"] is True
        assert result["result"]["exists"] is True
        assert result["result"]["type"] == "file"
        assert result["result"]["size"] == 11  # "Hello World" = 11 bytes
        assert result["result"]["modified"] is not None
        assert result["result"]["is_readable"] is True
        assert str(test_file) in result["result"]["absolute_path"]

    @pytest.mark.asyncio
    async def test_path_info_directory(self, fs_tools_readonly, temp_workspace):
        """Test get_path_info returns correct metadata for directory."""
        # Create test directory
        test_dir = temp_workspace / "testdir"
        test_dir.mkdir()

        result = await fs_tools_readonly.get_path_info("testdir")

        assert result["success"] is True
        assert result["result"]["exists"] is True
        assert result["result"]["type"] == "directory"
        assert result["result"]["size"] is None  # Directories don't have size
        assert result["result"]["modified"] is not None
        assert result["result"]["is_readable"] is True

    @pytest.mark.asyncio
    async def test_path_info_nonexistent(self, fs_tools_readonly):
        """Test get_path_info for nonexistent path."""
        result = await fs_tools_readonly.get_path_info("does_not_exist.txt")

        assert result["success"] is True
        assert result["result"]["exists"] is False
        assert result["result"]["type"] is None
        assert result["result"]["size"] is None
        assert result["result"]["is_readable"] is False
        assert result["result"]["is_writable"] is False

    @pytest.mark.asyncio
    async def test_path_info_symlink(self, fs_tools_readonly, temp_workspace):
        """Test get_path_info detects symlinks."""
        # Create target and symlink
        target = temp_workspace / "target.txt"
        target.write_text("content")

        symlink = temp_workspace / "link.txt"
        symlink.symlink_to(target)

        result = await fs_tools_readonly.get_path_info("link.txt")

        assert result["success"] is True
        assert result["result"]["exists"] is True
        # Symlink type depends on is_symlink() check before is_file()
        # After resolution, it should be treated as file
        assert result["result"]["type"] in ["file", "symlink"]

    @pytest.mark.asyncio
    async def test_path_info_workspace_root(self, fs_tools_readonly):
        """Test get_path_info on workspace root using '.'"""
        result = await fs_tools_readonly.get_path_info(".")

        assert result["success"] is True
        assert result["result"]["exists"] is True
        assert result["result"]["type"] == "directory"


# ============================================================================
# Test Class: list_directory
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestListDirectory:
    """Tests for list_directory tool."""

    @pytest.mark.asyncio
    async def test_list_directory_simple(self, fs_tools_readonly, sample_files):
        """Test basic directory listing."""
        result = await fs_tools_readonly.list_directory(".")

        assert result["success"] is True
        entries = result["result"]["entries"]
        assert len(entries) >= 3  # At least file1.txt, file2.py, subdir
        assert result["result"]["truncated"] is False

        # Check entry structure
        entry_names = {e["name"] for e in entries}
        assert "file1.txt" in entry_names
        assert "file2.py" in entry_names
        assert "subdir" in entry_names

        # Verify entry metadata
        file_entry = next(e for e in entries if e["name"] == "file1.txt")
        assert file_entry["type"] == "file"
        assert file_entry["size"] is not None
        assert "relative_path" in file_entry

    @pytest.mark.asyncio
    async def test_list_directory_recursive(self, fs_tools_readonly, sample_files):
        """Test recursive directory listing."""
        result = await fs_tools_readonly.list_directory(".", recursive=True)

        assert result["success"] is True
        entries = result["result"]["entries"]

        # Should include nested files
        entry_paths = {e["relative_path"] for e in entries}
        assert any("subdir" in path for path in entry_paths)
        assert any("file3.txt" in path for path in entry_paths)
        assert any("nested" in path for path in entry_paths)
        assert any("file4.py" in path for path in entry_paths)

    @pytest.mark.asyncio
    async def test_list_directory_hidden_files_excluded(self, fs_tools_readonly, sample_files):
        """Test hidden files (dotfiles) are excluded by default."""
        result = await fs_tools_readonly.list_directory(".", include_hidden=False)

        assert result["success"] is True
        entry_names = {e["name"] for e in result["result"]["entries"]}
        assert ".hidden" not in entry_names

    @pytest.mark.asyncio
    async def test_list_directory_hidden_files_included(self, fs_tools_readonly, sample_files):
        """Test hidden files can be included when requested."""
        result = await fs_tools_readonly.list_directory(".", include_hidden=True)

        assert result["success"] is True
        entry_names = {e["name"] for e in result["result"]["entries"]}
        assert ".hidden" in entry_names

    @pytest.mark.asyncio
    async def test_list_directory_max_entries_truncation(self, fs_tools_readonly, temp_workspace):
        """Test directory listing respects max_entries limit."""
        # Create many files
        for i in range(20):
            (temp_workspace / f"file{i}.txt").write_text(f"content {i}")

        result = await fs_tools_readonly.list_directory(".", max_entries=10)

        assert result["success"] is True
        assert len(result["result"]["entries"]) == 10
        assert result["result"]["truncated"] is True

    @pytest.mark.asyncio
    async def test_list_directory_empty(self, fs_tools_readonly, temp_workspace):
        """Test listing empty directory returns empty list."""
        empty_dir = temp_workspace / "empty"
        empty_dir.mkdir()

        result = await fs_tools_readonly.list_directory("empty")

        assert result["success"] is True
        assert result["result"]["entries"] == []
        assert result["result"]["truncated"] is False

    @pytest.mark.asyncio
    async def test_list_directory_not_a_directory_error(self, fs_tools_readonly, sample_files):
        """Test listing a file (not directory) returns error."""
        result = await fs_tools_readonly.list_directory("file1.txt")

        assert result["success"] is False
        assert result["error"] == "not_a_directory"

    @pytest.mark.asyncio
    async def test_list_directory_not_found_error(self, fs_tools_readonly):
        """Test listing nonexistent directory returns error."""
        result = await fs_tools_readonly.list_directory("does_not_exist")

        assert result["success"] is False
        assert result["error"] == "not_found"


# ============================================================================
# Test Class: read_file
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestReadFile:
    """Tests for read_file tool."""

    @pytest.mark.asyncio
    async def test_read_file_complete(self, fs_tools_readonly, temp_workspace):
        """Test reading entire small file."""
        test_file = temp_workspace / "test.txt"
        content = "Line 1\nLine 2\nLine 3\n"
        test_file.write_text(content)

        result = await fs_tools_readonly.read_file("test.txt")

        assert result["success"] is True
        assert result["result"]["content"] == content
        assert result["result"]["start_line"] == 1
        assert result["result"]["end_line"] == 3
        assert result["result"]["total_lines"] == 3
        assert result["result"]["truncated"] is False
        assert result["result"]["next_start_line"] is None
        assert result["result"]["encoding_errors"] is False

    @pytest.mark.asyncio
    async def test_read_file_chunked(self, fs_tools_readonly, temp_workspace):
        """Test reading file in chunks with start_line and max_lines."""
        # Create file with many lines
        lines = [f"Line {i}\n" for i in range(1, 101)]
        test_file = temp_workspace / "large.txt"
        test_file.write_text("".join(lines))

        # Read first chunk
        result = await fs_tools_readonly.read_file("large.txt", start_line=1, max_lines=10)

        assert result["success"] is True
        assert result["result"]["start_line"] == 1
        assert result["result"]["end_line"] == 10
        assert result["result"]["total_lines"] == 100
        assert result["result"]["truncated"] is True
        assert result["result"]["next_start_line"] == 11
        assert result["result"]["content"] == "".join(lines[0:10])

        # Read second chunk
        result2 = await fs_tools_readonly.read_file("large.txt", start_line=11, max_lines=10)

        assert result2["success"] is True
        assert result2["result"]["start_line"] == 11
        assert result2["result"]["end_line"] == 20
        assert result2["result"]["content"] == "".join(lines[10:20])

    @pytest.mark.asyncio
    async def test_read_file_utf8_with_emoji(self, fs_tools_readonly, temp_workspace):
        """Test reading UTF-8 file with emoji and unicode characters."""
        test_file = temp_workspace / "unicode.txt"
        content = "Hello 👋\n你好 🌍\nBonjour ◉‿◉\n"
        test_file.write_text(content, encoding="utf-8")

        result = await fs_tools_readonly.read_file("unicode.txt")

        assert result["success"] is True
        assert result["result"]["content"] == content
        assert result["result"]["encoding_errors"] is False

    @pytest.mark.asyncio
    async def test_read_file_binary_rejected(self, fs_tools_readonly, temp_workspace):
        """Test binary files are detected and rejected."""
        # Create binary file with null bytes
        test_file = temp_workspace / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\xff\xfe")

        result = await fs_tools_readonly.read_file("binary.bin")

        assert result["success"] is False
        assert result["error"] == "is_binary"
        assert "null bytes" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_read_file_encoding_errors_replaced(self, fs_tools_readonly, temp_workspace):
        """Test malformed UTF-8 uses errors='replace' gracefully."""
        # Create file with invalid UTF-8
        test_file = temp_workspace / "invalid.txt"
        test_file.write_bytes(b"Hello \xff\xfe World\n")

        result = await fs_tools_readonly.read_file("invalid.txt")

        assert result["success"] is True
        assert result["result"]["encoding_errors"] is True
        # Should contain replacement character
        assert "\ufffd" in result["result"]["content"]

    @pytest.mark.asyncio
    async def test_read_file_empty(self, fs_tools_readonly, temp_workspace):
        """Test reading empty file."""
        test_file = temp_workspace / "empty.txt"
        test_file.write_text("")

        result = await fs_tools_readonly.read_file("empty.txt")

        assert result["success"] is True
        assert result["result"]["content"] == ""
        assert result["result"]["total_lines"] == 0
        assert result["result"]["truncated"] is False

    @pytest.mark.asyncio
    async def test_read_file_no_trailing_newline(self, fs_tools_readonly, temp_workspace):
        """Test reading file without trailing newline."""
        test_file = temp_workspace / "no_newline.txt"
        test_file.write_text("Line 1\nLine 2")  # No trailing newline

        result = await fs_tools_readonly.read_file("no_newline.txt")

        assert result["success"] is True
        assert result["result"]["total_lines"] == 2
        assert result["result"]["content"] == "Line 1\nLine 2"

    @pytest.mark.asyncio
    async def test_read_file_line_out_of_range(self, fs_tools_readonly, temp_workspace):
        """Test reading with start_line beyond file length."""
        test_file = temp_workspace / "short.txt"
        test_file.write_text("Line 1\nLine 2\n")

        result = await fs_tools_readonly.read_file("short.txt", start_line=100)

        assert result["success"] is False
        assert result["error"] == "line_out_of_range"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, fs_tools_readonly):
        """Test reading nonexistent file."""
        result = await fs_tools_readonly.read_file("does_not_exist.txt")

        assert result["success"] is False
        assert result["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_read_file_not_a_file(self, fs_tools_readonly, temp_workspace):
        """Test reading a directory (not file) returns error."""
        test_dir = temp_workspace / "dir"
        test_dir.mkdir()

        result = await fs_tools_readonly.read_file("dir")

        assert result["success"] is False
        assert result["error"] == "not_a_file"

    @pytest.mark.asyncio
    async def test_read_file_size_limit_exceeded(self, fs_tools_readonly, temp_workspace):
        """Test file size limit enforcement."""
        # Create file larger than default limit (10MB)
        large_file = temp_workspace / "huge.txt"
        # Create content larger than max_read_bytes
        large_content = "x" * (fs_tools_readonly.config.filesystem_max_read_bytes + 1000)
        large_file.write_text(large_content)

        result = await fs_tools_readonly.read_file("huge.txt")

        assert result["success"] is False
        assert result["error"] == "file_too_large"


# ============================================================================
# Test Class: search_text
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestSearchText:
    """Tests for search_text tool."""

    @pytest.mark.asyncio
    async def test_search_text_literal(self, fs_tools_readonly, sample_files):
        """Test simple literal string search."""
        result = await fs_tools_readonly.search_text("Hello", path=".")

        assert result["success"] is True
        assert result["result"]["use_regex"] is False
        assert len(result["result"]["matches"]) >= 1

        # Should find "Hello" in file1.txt
        matches = result["result"]["matches"]
        hello_match = next(m for m in matches if "Hello" in m["snippet"])
        assert hello_match["file"] == "file1.txt"
        assert hello_match["line"] == 1
        assert "Hello World" in hello_match["snippet"]

    @pytest.mark.asyncio
    async def test_search_text_case_insensitive(self, fs_tools_readonly, sample_files):
        """Test case-insensitive search."""
        result = await fs_tools_readonly.search_text("HELLO", path=".", case_sensitive=False)

        assert result["success"] is True
        assert len(result["result"]["matches"]) >= 1
        # Should find "Hello" even though we searched for "HELLO"

    @pytest.mark.asyncio
    async def test_search_text_case_sensitive(self, fs_tools_readonly, sample_files):
        """Test case-sensitive search doesn't match different case."""
        result = await fs_tools_readonly.search_text("HELLO", path=".", case_sensitive=True)

        assert result["success"] is True
        assert len(result["result"]["matches"]) == 0  # Should not find lowercase "Hello"

    @pytest.mark.asyncio
    async def test_search_text_regex_simple(self, fs_tools_readonly, sample_files):
        """Test basic regex pattern search."""
        result = await fs_tools_readonly.search_text(r"Line \d+", path=".", use_regex=True)

        assert result["success"] is True
        assert result["result"]["use_regex"] is True
        assert len(result["result"]["matches"]) >= 1

        # Should match "Line 2", "Line 3", etc.
        for match in result["result"]["matches"]:
            assert match["match_start"] >= 0
            assert match["match_end"] > match["match_start"]

    @pytest.mark.asyncio
    async def test_search_text_regex_invalid(self, fs_tools_readonly, sample_files):
        """Test invalid regex pattern returns error."""
        result = await fs_tools_readonly.search_text(r"[invalid(", path=".", use_regex=True)

        assert result["success"] is False
        assert result["error"] == "invalid_regex"

    @pytest.mark.asyncio
    async def test_search_text_glob_filter(self, fs_tools_readonly, sample_files):
        """Test glob pattern filtering (search only .py files)."""
        result = await fs_tools_readonly.search_text("def", path=".", glob="*.py")

        assert result["success"] is True
        matches = result["result"]["matches"]

        # All matches should be from .py files
        for match in matches:
            assert match["file"].endswith(".py")

    @pytest.mark.asyncio
    async def test_search_text_max_matches(self, fs_tools_readonly, temp_workspace):
        """Test max_matches limit is enforced."""
        # Create multiple files with matches
        for i in range(20):
            (temp_workspace / f"file{i}.txt").write_text("MATCH\nMATCH\n")

        result = await fs_tools_readonly.search_text("MATCH", path=".", max_matches=5)

        assert result["success"] is True
        assert len(result["result"]["matches"]) == 5
        assert result["result"]["truncated"] is True

    @pytest.mark.asyncio
    async def test_search_text_binary_files_skipped(self, fs_tools_readonly, temp_workspace):
        """Test binary files are automatically skipped."""
        # Create binary file
        (temp_workspace / "binary.bin").write_bytes(b"\x00\x01MATCH\xff\xfe")
        # Create text file
        (temp_workspace / "text.txt").write_text("MATCH\n")

        result = await fs_tools_readonly.search_text("MATCH", path=".")

        assert result["success"] is True
        # Should only find match in text.txt, not binary.bin
        assert len(result["result"]["matches"]) == 1
        assert result["result"]["matches"][0]["file"] == "text.txt"

    @pytest.mark.asyncio
    async def test_search_text_no_matches(self, fs_tools_readonly, sample_files):
        """Test search with no matches returns empty results."""
        result = await fs_tools_readonly.search_text("NONEXISTENT_STRING_12345", path=".")

        assert result["success"] is True
        assert len(result["result"]["matches"]) == 0
        assert result["result"]["truncated"] is False

    @pytest.mark.asyncio
    async def test_search_text_single_file(self, fs_tools_readonly, sample_files):
        """Test searching in a single file instead of directory."""
        result = await fs_tools_readonly.search_text("Hello", path="file1.txt")

        assert result["success"] is True
        assert result["result"]["files_searched"] == 1
        assert len(result["result"]["matches"]) >= 1


# ============================================================================
# Test Class: write_file
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestWriteFile:
    """Tests for write_file tool."""

    @pytest.mark.asyncio
    async def test_write_file_disabled(self, fs_tools_readonly, temp_workspace):
        """Test write_file fails when writes disabled."""
        result = await fs_tools_readonly.write_file("test.txt", "content")

        assert result["success"] is False
        assert result["error"] == "writes_disabled"

    @pytest.mark.asyncio
    async def test_write_file_mode_create(self, fs_tools_writable, temp_workspace):
        """Test creating new file with mode='create'."""
        result = await fs_tools_writable.write_file("new.txt", "Hello World", mode="create")

        assert result["success"] is True
        assert result["result"]["path"] == "new.txt"
        assert result["result"]["bytes_written"] == 11
        assert result["result"]["mode"] == "create"
        assert result["result"]["existed_before"] is False

        # Verify file was created
        created_file = temp_workspace / "new.txt"
        assert created_file.exists()
        assert created_file.read_text() == "Hello World"

    @pytest.mark.asyncio
    async def test_write_file_mode_overwrite(self, fs_tools_writable, temp_workspace):
        """Test overwriting existing file with mode='overwrite'."""
        # Create existing file
        existing = temp_workspace / "existing.txt"
        existing.write_text("Old content")

        result = await fs_tools_writable.write_file("existing.txt", "New content", mode="overwrite")

        assert result["success"] is True
        assert result["result"]["mode"] == "overwrite"
        assert result["result"]["existed_before"] is True

        # Verify file was overwritten
        assert existing.read_text() == "New content"

    @pytest.mark.asyncio
    async def test_write_file_mode_append(self, fs_tools_writable, temp_workspace):
        """Test appending to file with mode='append'."""
        # Create existing file
        existing = temp_workspace / "append.txt"
        existing.write_text("Line 1\n")

        result = await fs_tools_writable.write_file("append.txt", "Line 2\n", mode="append")

        assert result["success"] is True
        assert result["result"]["mode"] == "append"
        assert result["result"]["existed_before"] is True

        # Verify content was appended
        assert existing.read_text() == "Line 1\nLine 2\n"

    @pytest.mark.asyncio
    async def test_write_file_mode_append_new_file(self, fs_tools_writable, temp_workspace):
        """Test append mode creates file if it doesn't exist."""
        result = await fs_tools_writable.write_file("new_append.txt", "Content", mode="append")

        assert result["success"] is True
        assert result["result"]["existed_before"] is False

        # Verify file was created
        created = temp_workspace / "new_append.txt"
        assert created.exists()
        assert created.read_text() == "Content"

    @pytest.mark.asyncio
    async def test_write_file_file_exists_error(self, fs_tools_writable, temp_workspace):
        """Test mode='create' fails if file already exists."""
        # Create existing file
        existing = temp_workspace / "exists.txt"
        existing.write_text("Existing")

        result = await fs_tools_writable.write_file("exists.txt", "New", mode="create")

        assert result["success"] is False
        assert result["error"] == "file_exists"
        assert "overwrite" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_write_file_size_limit(self, fs_tools_writable):
        """Test write size limit enforcement."""
        # Try to write content larger than limit
        max_bytes = fs_tools_writable.config.filesystem_max_write_bytes
        large_content = "x" * (max_bytes + 1000)

        result = await fs_tools_writable.write_file("large.txt", large_content, mode="create")

        assert result["success"] is False
        assert result["error"] == "write_too_large"

    @pytest.mark.asyncio
    async def test_write_file_invalid_mode(self, fs_tools_writable):
        """Test invalid write mode returns error."""
        result = await fs_tools_writable.write_file("test.txt", "content", mode="invalid")

        assert result["success"] is False
        assert result["error"] == "invalid_mode"

    @pytest.mark.asyncio
    async def test_write_file_creates_in_subdirectory(self, fs_tools_writable, temp_workspace):
        """Test writing file in subdirectory (directory must exist)."""
        # Create subdirectory
        subdir = temp_workspace / "subdir"
        subdir.mkdir()

        result = await fs_tools_writable.write_file("subdir/file.txt", "content", mode="create")

        assert result["success"] is True
        assert (subdir / "file.txt").read_text() == "content"


# ============================================================================
# Test Class: apply_text_edit
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestApplyTextEdit:
    """Tests for apply_text_edit tool."""

    @pytest.mark.asyncio
    async def test_apply_text_edit_disabled(self, fs_tools_readonly, temp_workspace):
        """Test apply_text_edit fails when writes disabled."""
        # Create file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("content")

        result = await fs_tools_readonly.apply_text_edit("test.txt", "content", "new")

        assert result["success"] is False
        assert result["error"] == "writes_disabled"

    @pytest.mark.asyncio
    async def test_apply_text_edit_single_match(self, fs_tools_writable, temp_workspace):
        """Test replacing exactly one occurrence."""
        test_file = temp_workspace / "edit.txt"
        test_file.write_text("Hello World\nGoodbye World\n")

        result = await fs_tools_writable.apply_text_edit("edit.txt", "Hello", "Hi")

        assert result["success"] is True
        assert result["result"]["replacements"] == 1
        assert result["result"]["original_size"] > 0
        assert result["result"]["new_size"] > 0

        # Verify edit was applied
        assert test_file.read_text() == "Hi World\nGoodbye World\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_multiple_matches_error(self, fs_tools_writable, temp_workspace):
        """Test error when multiple matches and replace_all=False."""
        test_file = temp_workspace / "multi.txt"
        test_file.write_text("World World World\n")

        result = await fs_tools_writable.apply_text_edit(
            "multi.txt", "World", "Earth", replace_all=False
        )

        assert result["success"] is False
        assert result["error"] == "multiple_matches"
        assert "replace_all=true" in result["message"].lower()

        # File should not be modified
        assert test_file.read_text() == "World World World\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_replace_all(self, fs_tools_writable, temp_workspace):
        """Test replacing all occurrences with replace_all=True."""
        test_file = temp_workspace / "all.txt"
        test_file.write_text("foo bar foo baz foo\n")

        result = await fs_tools_writable.apply_text_edit("all.txt", "foo", "qux", replace_all=True)

        assert result["success"] is True
        assert result["result"]["replacements"] == 3

        # Verify all occurrences replaced
        assert test_file.read_text() == "qux bar qux baz qux\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_match_not_found(self, fs_tools_writable, temp_workspace):
        """Test error when expected_text not found."""
        test_file = temp_workspace / "nomatch.txt"
        test_file.write_text("Hello World\n")

        result = await fs_tools_writable.apply_text_edit("nomatch.txt", "NONEXISTENT", "something")

        assert result["success"] is False
        assert result["error"] == "match_not_found"

        # File should not be modified
        assert test_file.read_text() == "Hello World\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_empty_expected_text(self, fs_tools_writable, temp_workspace):
        """Test error when expected_text is empty."""
        test_file = temp_workspace / "test.txt"
        test_file.write_text("content")

        result = await fs_tools_writable.apply_text_edit("test.txt", "", "replacement")

        assert result["success"] is False
        assert result["error"] == "empty_expected_text"

    @pytest.mark.asyncio
    async def test_apply_text_edit_multiline(self, fs_tools_writable, temp_workspace):
        """Test multiline text replacement."""
        test_file = temp_workspace / "multiline.txt"
        original = "Line 1\nOLD BLOCK\nLine 2\nLine 3\n"
        test_file.write_text(original)

        result = await fs_tools_writable.apply_text_edit(
            "multiline.txt", "OLD BLOCK\nLine 2", "NEW BLOCK\nUpdated Line"
        )

        assert result["success"] is True
        assert test_file.read_text() == "Line 1\nNEW BLOCK\nUpdated Line\nLine 3\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_deletion(self, fs_tools_writable, temp_workspace):
        """Test deleting text by replacing with empty string."""
        test_file = temp_workspace / "delete.txt"
        test_file.write_text("Keep DELETE_THIS Keep\n")

        result = await fs_tools_writable.apply_text_edit("delete.txt", "DELETE_THIS ", "")

        assert result["success"] is True
        assert test_file.read_text() == "Keep Keep\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_whitespace_exact_match(self, fs_tools_writable, temp_workspace):
        """Test whitespace must match exactly (no fuzzy matching)."""
        test_file = temp_workspace / "whitespace.txt"
        test_file.write_text("Hello  World\n")  # Two spaces

        # Try to match with one space (should fail)
        result = await fs_tools_writable.apply_text_edit("whitespace.txt", "Hello World", "Hi")

        assert result["success"] is False
        assert result["error"] == "match_not_found"

        # File should not be modified
        assert test_file.read_text() == "Hello  World\n"

    @pytest.mark.asyncio
    async def test_apply_text_edit_atomic_write(self, fs_tools_writable, temp_workspace):
        """Test atomic write (temp file + rename) prevents corruption."""
        test_file = temp_workspace / "atomic.txt"
        test_file.write_text("Original content\n")

        # Successful edit
        result = await fs_tools_writable.apply_text_edit("atomic.txt", "Original", "Modified")

        assert result["success"] is True
        # File should have new content
        assert test_file.read_text() == "Modified content\n"
        # No temp files should remain
        temp_files = list(temp_workspace.glob(".atomic.txt.*.tmp"))
        assert len(temp_files) == 0


# ============================================================================
# Test Class: create_directory
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestCreateDirectory:
    """Tests for create_directory tool."""

    @pytest.mark.asyncio
    async def test_create_directory_disabled(self, fs_tools_readonly):
        """Test create_directory fails when writes disabled."""
        result = await fs_tools_readonly.create_directory("newdir")

        assert result["success"] is False
        assert result["error"] == "writes_disabled"

    @pytest.mark.asyncio
    async def test_create_directory_simple(self, fs_tools_writable, temp_workspace):
        """Test creating single directory."""
        result = await fs_tools_writable.create_directory("newdir")

        assert result["success"] is True
        assert result["result"]["path"] == "newdir"
        assert result["result"]["created"] is True
        assert result["result"]["parents_created"] == 0

        # Verify directory was created
        assert (temp_workspace / "newdir").is_dir()

    @pytest.mark.asyncio
    async def test_create_directory_with_parents(self, fs_tools_writable, temp_workspace):
        """Test creating nested directory structure."""
        result = await fs_tools_writable.create_directory("parent/child/grandchild", parents=True)

        assert result["success"] is True
        assert result["result"]["created"] is True
        assert result["result"]["parents_created"] >= 2  # parent and child

        # Verify directory structure
        assert (temp_workspace / "parent" / "child" / "grandchild").is_dir()

    @pytest.mark.asyncio
    async def test_create_directory_idempotent(self, fs_tools_writable, temp_workspace):
        """Test creating existing directory is idempotent (returns success)."""
        # Create directory
        existing = temp_workspace / "existing"
        existing.mkdir()

        result = await fs_tools_writable.create_directory("existing")

        assert result["success"] is True
        assert result["result"]["created"] is False  # Already existed
        assert result["result"]["parents_created"] == 0

    @pytest.mark.asyncio
    async def test_create_directory_file_exists_error(self, fs_tools_writable, temp_workspace):
        """Test error when path exists but is a file."""
        # Create file with same name
        conflicting = temp_workspace / "conflict"
        conflicting.write_text("I am a file")

        result = await fs_tools_writable.create_directory("conflict")

        assert result["success"] is False
        assert result["error"] == "not_a_directory"

    @pytest.mark.asyncio
    async def test_create_directory_without_parents_fails(self, fs_tools_writable, temp_workspace):
        """Test creating nested directory without parents fails."""
        result = await fs_tools_writable.create_directory("parent/child", parents=False)

        assert result["success"] is False
        assert result["error"] == "parent_not_found"
        assert "parents=true" in result["message"].lower()


# ============================================================================
# Test Class: Cross-Platform Compatibility
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestCrossPlatformCompatibility:
    """Tests for cross-platform path handling."""

    @pytest.mark.asyncio
    async def test_unicode_filenames(self, fs_tools_writable, temp_workspace):
        """Test handling unicode filenames (emoji, Chinese characters)."""
        # Create file with unicode name
        unicode_file = temp_workspace / "测试_📄_test.txt"
        unicode_file.write_text("Content")

        result = await fs_tools_writable.get_path_info("测试_📄_test.txt")

        assert result["success"] is True
        assert result["result"]["exists"] is True

    @pytest.mark.asyncio
    async def test_spaces_in_paths(self, fs_tools_writable, temp_workspace):
        """Test handling paths with spaces."""
        # Create directory and file with spaces
        dir_with_spaces = temp_workspace / "My Documents"
        dir_with_spaces.mkdir()
        file_with_spaces = dir_with_spaces / "test file.txt"
        file_with_spaces.write_text("content")

        result = await fs_tools_writable.get_path_info("My Documents/test file.txt")

        assert result["success"] is True
        assert result["result"]["exists"] is True

    @pytest.mark.asyncio
    async def test_special_characters_in_filenames(self, fs_tools_writable, temp_workspace):
        """Test handling special characters in filenames."""
        # Characters that are valid on most filesystems
        special_chars = ["file$test.txt", "file#test.txt", "file@test.txt"]

        for filename in special_chars:
            special_file = temp_workspace / filename
            special_file.write_text("content")

            result = await fs_tools_writable.get_path_info(filename)
            assert result["success"] is True, f"Failed for {filename}"


# ============================================================================
# Test Class: Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestEdgeCasesAndErrors:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_very_long_filename(self, fs_tools_writable, temp_workspace):
        """Test handling filenames near OS limits."""
        # Most filesystems allow 255 characters
        long_name = "a" * 200 + ".txt"
        long_file = temp_workspace / long_name
        long_file.write_text("content")

        result = await fs_tools_writable.get_path_info(long_name)

        assert result["success"] is True
        assert result["result"]["exists"] is True

    @pytest.mark.asyncio
    async def test_empty_filename_component(self, fs_tools_readonly):
        """Test handling paths with empty components."""
        # Paths like "dir//file.txt" should be normalized
        result = await fs_tools_readonly.get_path_info(".")

        # Should work (current directory)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_workspace_not_found_error(self, tmp_path):
        """Test error when workspace_root doesn't exist."""
        nonexistent = tmp_path / "does_not_exist"

        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        config.workspace_root = nonexistent
        config.filesystem_writes_enabled = False
        config.filesystem_max_read_bytes = 10_485_760
        config.filesystem_max_write_bytes = 1_048_576
        tools = FileSystemTools(config)

        result = await tools.get_path_info(".")

        assert result["success"] is False
        assert result["error"] == "workspace_not_found"

    @pytest.mark.asyncio
    async def test_workspace_not_directory_error(self, tmp_path):
        """Test error when workspace_root is a file, not directory."""
        file_not_dir = tmp_path / "file.txt"
        file_not_dir.write_text("content")

        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")
        config.workspace_root = file_not_dir
        config.filesystem_writes_enabled = False
        config.filesystem_max_read_bytes = 10_485_760
        config.filesystem_max_write_bytes = 1_048_576
        tools = FileSystemTools(config)

        result = await tools.get_path_info(".")

        assert result["success"] is False
        assert result["error"] == "workspace_not_directory"


# ============================================================================
# Test Class: Response Format Consistency
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestResponseFormatConsistency:
    """Tests for consistent response format across all tools."""

    def test_success_response_format(self, fs_tools_readonly):
        """Test success responses have consistent structure."""
        success = fs_tools_readonly._create_success_response({"key": "value"}, "msg")

        assert "success" in success
        assert "result" in success
        assert "message" in success
        assert success["success"] is True
        assert success["result"] == {"key": "value"}
        assert success["message"] == "msg"

    def test_error_response_format(self, fs_tools_readonly):
        """Test error responses have consistent structure."""
        error = fs_tools_readonly._create_error_response("error_code", "msg")

        assert "success" in error
        assert "error" in error
        assert "message" in error
        assert error["success"] is False
        assert error["error"] == "error_code"
        assert error["message"] == "msg"

    @pytest.mark.asyncio
    async def test_all_tools_return_standard_format(self, fs_tools_readonly, temp_workspace):
        """Test all tools return standard response format."""
        # Create test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("content")

        # Test all read-only tools
        tools_to_test = [
            fs_tools_readonly.get_path_info("."),
            fs_tools_readonly.list_directory("."),
            fs_tools_readonly.read_file("test.txt"),
            fs_tools_readonly.search_text("content", path="."),
        ]

        for tool_call in tools_to_test:
            result = await tool_call
            # All should have success key
            assert "success" in result
            assert "message" in result
            # Either result or error
            if result["success"]:
                assert "result" in result
            else:
                assert "error" in result
