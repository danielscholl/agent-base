"""Filesystem tools for safe, sandboxed file operations.

This module provides structured filesystem tools that enable agents to inspect
and modify files in a controlled workspace without exposing arbitrary OS shell
execution to the LLM.

Key Features:
- Workspace sandboxing with path traversal protection
- Structured directory listing and file reading
- Text search with literal and regex support
- Guarded write operations (disabled by default)
- Surgical text editing with safety checks
- Cross-platform path handling

All operations are sandboxed to workspace_root (defaults to current directory).
"""

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from agent.config import AgentConfig
from agent.tools.toolset import AgentToolset

logger = logging.getLogger(__name__)


class FileSystemTools(AgentToolset):
    """Filesystem tools for safe, sandboxed file operations.

    This toolset provides structured file operations with security guarantees:
    - All paths must be under configured workspace_root
    - Path traversal attempts are blocked
    - Symlinks that escape workspace are rejected
    - Write operations are disabled by default
    - Size limits prevent resource exhaustion

    Example:
        >>> config = AgentConfig.from_env()
        >>> config.workspace_root = Path("/home/user/project")
        >>> tools = FileSystemTools(config)
        >>> result = await tools.list_directory(".")
        >>> print(result)
        {'success': True, 'result': {'entries': [...], 'truncated': False}}
    """

    def __init__(self, config: AgentConfig):
        """Initialize FileSystemTools with configuration.

        Args:
            config: Agent configuration instance with workspace_root
        """
        super().__init__(config)
        self._workspace_root_cache: Path | None = None

    def get_tools(self) -> list:
        """Get list of filesystem tools.

        Returns:
            List of filesystem tool functions
        """
        return [
            self.get_path_info,
            self.list_directory,
            self.read_file,
            self.search_text,
            self.write_file,
            self.apply_text_edit,
            self.create_directory,
        ]

    def _get_workspace_root(self) -> Path:
        """Get and cache workspace root from config, environment, or current directory.

        Priority order:
            1. Cached value (for performance)
            2. config.workspace_root (from settings.json)
            3. AGENT_WORKSPACE_ROOT env var
            4. Path.cwd() (default fallback)

        Returns:
            Resolved workspace root Path (always returns a valid Path)

        Note:
            Logs warning if workspace is home directory or filesystem root,
            as these are risky locations that may expose more than intended.
        """
        if self._workspace_root_cache is not None:
            return self._workspace_root_cache

        workspace_root: Path | None = None

        # Check config first (handle legacy configs without workspace_root attribute)
        if hasattr(self.config, "workspace_root") and self.config.workspace_root is not None:
            workspace_root = self.config.workspace_root
        # Check environment variable
        elif env_root := os.getenv("AGENT_WORKSPACE_ROOT"):
            workspace_root = Path(env_root).expanduser().resolve()
        # Default to current working directory
        else:
            workspace_root = Path.cwd().resolve()
            # Log warning for risky workspace locations
            if workspace_root == Path.home() or workspace_root == Path("/"):
                logger.warning(
                    f"Workspace is set to {workspace_root}. Consider using a project directory "
                    "or configuring workspace_root in ~/.agent/settings.json for better security."
                )

        self._workspace_root_cache = workspace_root
        return self._workspace_root_cache

    def _resolve_path(self, relative_path: str) -> dict | Path:
        """Resolve and validate path within workspace boundaries.

        This is the core security function that enforces workspace sandboxing.
        All filesystem tools MUST call this before any filesystem access.

        Security checks:
        1. Workspace root is configured
        2. No path traversal attempts (../)
        3. No absolute paths outside workspace
        4. Symlinks don't escape workspace

        Args:
            relative_path: Path relative to workspace root

        Returns:
            Resolved Path object if valid, or error dict if validation fails

        Example:
            >>> path = self._resolve_path("src/main.py")
            >>> if isinstance(path, dict):
            ...     return path  # Error response
            >>> # Use path for filesystem operation
        """
        workspace_root = self._get_workspace_root()

        # Validate workspace root exists and is a directory
        if not workspace_root.exists():
            return self._create_error_response(
                error="workspace_not_found",
                message=f"Workspace root does not exist: {workspace_root}",
            )

        if not workspace_root.is_dir():
            return self._create_error_response(
                error="workspace_not_directory",
                message=f"Workspace root is not a directory: {workspace_root}",
            )

        # Detect path traversal attempts before resolution
        if ".." in Path(relative_path).parts:
            logger.warning(f"Path traversal attempt detected: {relative_path}")
            return self._create_error_response(
                error="path_traversal_attempt",
                message=f"Path contains '..' component: {relative_path}. Path traversal is not allowed.",
            )

        # Convert to Path and combine with workspace root
        try:
            # Handle both relative and absolute paths
            requested_path = Path(relative_path)

            if requested_path.is_absolute():
                # For absolute paths, verify they start with workspace_root
                unresolved = requested_path
                resolved = requested_path.resolve()
            else:
                # For relative paths, combine with workspace_root
                unresolved = workspace_root / requested_path
                resolved = unresolved.resolve()

            # Check if resolved path is within workspace
            try:
                # Use is_relative_to (Python 3.9+) to check boundaries
                if not resolved.is_relative_to(workspace_root):
                    logger.warning(
                        f"Path outside workspace: {relative_path} -> {resolved} "
                        f"(workspace: {workspace_root})"
                    )
                    return self._create_error_response(
                        error="path_outside_workspace",
                        message=f"Path resolves outside workspace: {relative_path}",
                    )
            except (ValueError, TypeError):
                # Fallback for edge cases
                return self._create_error_response(
                    error="path_outside_workspace",
                    message=f"Path resolves outside workspace: {relative_path}",
                )

            # Additional check: if symlink, verify target is in workspace
            if unresolved.is_symlink():
                try:
                    if not resolved.is_relative_to(workspace_root):
                        logger.warning(
                            f"Symlink target outside workspace: {relative_path} -> {resolved}"
                        )
                        return self._create_error_response(
                            error="symlink_outside_workspace",
                            message=f"Symlink target is outside workspace: {relative_path}",
                        )
                except (ValueError, TypeError):
                    return self._create_error_response(
                        error="symlink_outside_workspace",
                        message=f"Symlink target is outside workspace: {relative_path}",
                    )

            logger.debug(f"Path resolved: {relative_path} -> {resolved}")
            return resolved

        except (OSError, RuntimeError) as e:
            logger.error(f"Error resolving path {relative_path}: {e}")
            return self._create_error_response(
                error="path_resolution_failed",
                message=f"Failed to resolve path: {relative_path}. Error: {str(e)}",
            )

    """
    {
      "name": "get_path_info",
      "description": "Get file/directory metadata within workspace. Returns exists, type, size, permissions, timestamps.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Path relative to workspace root",
            "default": "."
          }
        },
        "required": []
      }
    }
    """

    async def get_path_info(
        self, path: Annotated[str, Field(description="Path relative to workspace root")] = "."
    ) -> dict:
        """Get file/directory metadata within workspace. Returns exists, type, size, permissions, timestamps."""
        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Get unresolved path for symlink detection
        workspace_root = self._get_workspace_root()
        requested_path = Path(path)
        if requested_path.is_absolute():
            unresolved = requested_path
        else:
            unresolved = workspace_root / requested_path

        # Gather metadata
        try:
            exists = resolved.exists()

            if not exists:
                info: dict[str, Any] = {
                    "exists": False,
                    "type": None,
                    "size": None,
                    "modified": None,
                    "is_readable": False,
                    "is_writable": False,
                    "absolute_path": str(resolved),
                }
                return self._create_success_response(
                    result=info, message=f"Path does not exist: {path}"
                )

            # Determine type - check symlink before resolved types
            if unresolved.is_symlink():
                path_type = "symlink"
                size = None
            elif resolved.is_file():
                path_type = "file"
                size = resolved.stat().st_size
            elif resolved.is_dir():
                path_type = "directory"
                size = None
            else:
                path_type = "other"
                size = None

            # Get modification time
            modified = resolved.stat().st_mtime

            # Check permissions
            is_readable = os.access(resolved, os.R_OK)
            is_writable = os.access(resolved, os.W_OK)

            exists_info: dict[str, Any] = {
                "exists": True,
                "type": path_type,
                "size": size,
                "modified": modified,
                "is_readable": is_readable,
                "is_writable": is_writable,
                "absolute_path": str(resolved),
            }

            return self._create_success_response(
                result=exists_info, message=f"Retrieved metadata for: {path}"
            )

        except PermissionError:
            return self._create_error_response(
                error="permission_denied",
                message=f"Permission denied accessing: {path}",
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"OS error accessing {path}: {str(e)}"
            )

    """
    {
      "name": "list_directory",
      "description": "List directory contents within workspace with metadata. Supports recursive traversal. Default: 200 entries max, excludes hidden files. Returns entries with type and size.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Directory path relative to workspace",
            "default": "."
          },
          "recursive": {
            "type": "boolean",
            "description": "Recursively list subdirectories",
            "default": false
          },
          "max_entries": {
            "type": "integer",
            "description": "Maximum entries to return",
            "default": 200
          },
          "include_hidden": {
            "type": "boolean",
            "description": "Include hidden files (dotfiles)",
            "default": false
          }
        },
        "required": []
      }
    }
    """

    async def list_directory(
        self,
        path: Annotated[str, Field(description="Directory path relative to workspace")] = ".",
        recursive: Annotated[bool, Field(description="Recursively list subdirectories")] = False,
        max_entries: Annotated[int, Field(description="Maximum entries to return")] = 200,
        include_hidden: Annotated[
            bool, Field(description="Include hidden files (dotfiles)")
        ] = False,
    ) -> dict:
        """List directory contents within workspace with metadata. Supports recursive traversal. Default: 200 entries max, excludes hidden files. Returns entries with type and size."""
        # Cap max_entries at 500
        max_entries = min(max_entries, 500)

        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Check if path exists and is a directory
        if not resolved.exists():
            return self._create_error_response(error="not_found", message=f"Path not found: {path}")

        if not resolved.is_dir():
            return self._create_error_response(
                error="not_a_directory", message=f"Path is not a directory: {path}"
            )

        # Get workspace root for relative path calculation
        workspace_root = self._get_workspace_root()
        entries: list[dict[str, Any]] = []
        truncated = False

        try:
            if recursive:
                # Recursive walk
                for root, dirs, files in os.walk(resolved):
                    root_path = Path(root)

                    # Filter hidden directories if needed
                    if not include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]

                    # Add directories
                    for dir_name in dirs:
                        if len(entries) >= max_entries:
                            truncated = True
                            break

                        dir_path = root_path / dir_name
                        relative = dir_path.relative_to(workspace_root)

                        entries.append(
                            {
                                "name": dir_name,
                                "relative_path": str(relative),
                                "type": "directory",
                                "size": None,
                            }
                        )

                    if truncated:
                        break

                    # Filter and add files
                    if not include_hidden:
                        files = [f for f in files if not f.startswith(".")]

                    for file_name in files:
                        if len(entries) >= max_entries:
                            truncated = True
                            break

                        file_path = root_path / file_name
                        relative = file_path.relative_to(workspace_root)

                        try:
                            size = file_path.stat().st_size
                        except OSError:
                            size = None

                        entries.append(
                            {
                                "name": file_name,
                                "relative_path": str(relative),
                                "type": "file",
                                "size": size,
                            }
                        )

                    if truncated:
                        break

            else:
                # Non-recursive listing
                for entry in resolved.iterdir():
                    if len(entries) >= max_entries:
                        truncated = True
                        break

                    # Skip hidden files if requested
                    if not include_hidden and entry.name.startswith("."):
                        continue

                    relative = entry.relative_to(workspace_root)

                    if entry.is_dir():
                        entries.append(
                            {
                                "name": entry.name,
                                "relative_path": str(relative),
                                "type": "directory",
                                "size": None,
                            }
                        )
                    elif entry.is_file():
                        try:
                            size = entry.stat().st_size
                        except OSError:
                            size = None

                        entries.append(
                            {
                                "name": entry.name,
                                "relative_path": str(relative),
                                "type": "file",
                                "size": size,
                            }
                        )

            result = {"entries": entries, "truncated": truncated}

            return self._create_success_response(
                result=result, message=f"Listed {len(entries)} entries from: {path}"
            )

        except PermissionError:
            return self._create_error_response(
                error="permission_denied", message=f"Permission denied reading directory: {path}"
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"OS error listing directory {path}: {str(e)}"
            )

    """
    {
      "name": "read_file",
      "description": "Read text file within workspace by line range. Paths relative to workspace root. Default: first 200 lines. Returns content with truncation flag for large files.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "File path relative to workspace"
          },
          "start_line": {
            "type": "integer",
            "description": "Starting line number (1-based)",
            "default": 1
          },
          "max_lines": {
            "type": "integer",
            "description": "Maximum lines to read",
            "default": 200
          }
        },
        "required": ["path"]
      }
    }
    """

    async def read_file(
        self,
        path: Annotated[str, Field(description="File path relative to workspace")],
        start_line: Annotated[int, Field(description="Starting line number (1-based)")] = 1,
        max_lines: Annotated[int, Field(description="Maximum lines to read")] = 200,
    ) -> dict:
        """Read text file within workspace by line range. Paths relative to workspace root. Default: first 200 lines. Returns content with truncation flag for large files."""
        # Cap max_lines at 1000
        max_lines = min(max_lines, 1000)

        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Check if path exists and is a file
        if not resolved.exists():
            return self._create_error_response(error="not_found", message=f"File not found: {path}")

        if not resolved.is_file():
            return self._create_error_response(
                error="not_a_file", message=f"Path is not a file: {path}"
            )

        # Check file size limit
        try:
            file_size = resolved.stat().st_size
            if file_size > self.config.filesystem_max_read_bytes:
                return self._create_error_response(
                    error="file_too_large",
                    message=f"File size ({file_size} bytes) exceeds max read limit "
                    f"({self.config.filesystem_max_read_bytes} bytes): {path}",
                )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"Error getting file size for {path}: {str(e)}"
            )

        # Detect binary files (check first 8KB for null bytes)
        try:
            with open(resolved, "rb") as f:
                sample = f.read(8192)
                if b"\x00" in sample:
                    return self._create_error_response(
                        error="is_binary",
                        message=f"File appears to be binary (contains null bytes): {path}",
                    )
        except OSError as e:
            return self._create_error_response(
                error="permission_denied", message=f"Cannot read file {path}: {str(e)}"
            )

        # Read file contents
        try:
            with open(resolved, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Check if start_line is valid
            if start_line < 1:
                start_line = 1

            # Allow start_line beyond file length for empty files
            if total_lines > 0 and start_line > total_lines:
                return self._create_error_response(
                    error="line_out_of_range",
                    message=f"start_line ({start_line}) exceeds file length ({total_lines} lines): {path}",
                )

            # Calculate slice (convert to 0-based indexing)
            start_idx = start_line - 1
            end_idx = min(start_idx + max_lines, total_lines)

            # Extract lines
            selected_lines = lines[start_idx:end_idx]
            content = "".join(selected_lines)

            # Check if truncated
            truncated = end_idx < total_lines
            next_start_line = end_idx + 1 if truncated else None
            actual_end_line = end_idx  # 1-based

            # Check if encoding errors occurred (look for replacement character)
            encoding_errors = "\ufffd" in content

            result = {
                "path": path,
                "start_line": start_line,
                "end_line": actual_end_line,
                "total_lines": total_lines,
                "truncated": truncated,
                "next_start_line": next_start_line,
                "content": content,
                "encoding_errors": encoding_errors,
            }

            return self._create_success_response(
                result=result,
                message=f"Read {len(selected_lines)} lines from {path} (lines {start_line}-{actual_end_line})",
            )

        except PermissionError:
            return self._create_error_response(
                error="permission_denied", message=f"Permission denied reading file: {path}"
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"Error reading file {path}: {str(e)}"
            )

    """
    {
      "name": "search_text",
      "description": "Search text patterns across files in workspace. Supports literal (default) and regex modes. Case-sensitive by default. Max 50 matches. Returns matches with file, line, snippet.",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search pattern (literal or regex)"
          },
          "path": {
            "type": "string",
            "description": "Directory or file to search",
            "default": "."
          },
          "glob": {
            "type": "string",
            "description": "File pattern (e.g., '*.py', 'src/**/*.ts')",
            "default": "**/*"
          },
          "max_matches": {
            "type": "integer",
            "description": "Maximum matches to return",
            "default": 50
          },
          "use_regex": {
            "type": "boolean",
            "description": "Enable regex mode",
            "default": false
          },
          "case_sensitive": {
            "type": "boolean",
            "description": "Case-sensitive search",
            "default": true
          }
        },
        "required": ["query"]
      }
    }
    """

    async def search_text(
        self,
        query: Annotated[str, Field(description="Search pattern (literal or regex)")],
        path: Annotated[str, Field(description="Directory or file to search")] = ".",
        glob: Annotated[
            str, Field(description="File pattern (e.g., '*.py', 'src/**/*.ts')")
        ] = "**/*",
        max_matches: Annotated[int, Field(description="Maximum matches to return")] = 50,
        use_regex: Annotated[bool, Field(description="Enable regex mode")] = False,
        case_sensitive: Annotated[bool, Field(description="Case-sensitive search")] = True,
    ) -> dict:
        """Search text patterns across files in workspace. Supports literal (default) and regex modes. Case-sensitive by default. Max 50 matches. Returns matches with file, line, snippet."""

        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Check if path exists
        if not resolved.exists():
            return self._create_error_response(error="not_found", message=f"Path not found: {path}")

        # Compile regex if needed
        regex_pattern = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex_pattern = re.compile(query, flags)
            except re.error as e:
                return self._create_error_response(
                    error="invalid_regex", message=f"Invalid regex pattern '{query}': {str(e)}"
                )

        # Collect files to search
        files_to_search = []
        workspace_root = self._get_workspace_root()

        try:
            if resolved.is_file():
                # Single file search
                files_to_search = [resolved]
            elif resolved.is_dir():
                # Directory search with glob filtering
                # Use pathlib's glob matching instead of fnmatch for ** support
                if glob == "**/*" or glob == "*":
                    # Match all files (optimization)
                    for file_path in resolved.rglob("*"):
                        if file_path.is_file():
                            files_to_search.append(file_path)
                else:
                    # Use glob pattern matching
                    for file_path in resolved.glob(glob):
                        if file_path.is_file():
                            files_to_search.append(file_path)
                    # Also try rglob if glob contains **
                    if "**" in glob:
                        for file_path in resolved.glob(glob):
                            if file_path.is_file() and file_path not in files_to_search:
                                files_to_search.append(file_path)
            else:
                return self._create_error_response(
                    error="invalid_path_type", message=f"Path is neither file nor directory: {path}"
                )
        except (OSError, PermissionError) as e:
            return self._create_error_response(
                error="os_error", message=f"Error accessing path {path}: {str(e)}"
            )

        # Search files
        matches: list[dict[str, Any]] = []
        files_searched = 0
        truncated = False

        for file_path in files_to_search:
            if len(matches) >= max_matches:
                truncated = True
                break

            files_searched += 1

            try:
                # Skip binary files (check for null bytes in first 8KB)
                with open(file_path, "rb") as f:
                    sample = f.read(8192)
                    if b"\x00" in sample:
                        continue  # Skip binary file

                # Search file contents
                with open(file_path, encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, start=1):
                        if len(matches) >= max_matches:
                            truncated = True
                            break

                        # Perform search
                        if use_regex:
                            # Regex search
                            if regex_pattern is not None:
                                match_obj = regex_pattern.search(line)
                            else:
                                match_obj = None
                            if match_obj:
                                match_start = match_obj.start()
                                match_end = match_obj.end()
                            else:
                                continue
                        else:
                            # Literal search
                            search_line = line if case_sensitive else line.lower()
                            search_query = query if case_sensitive else query.lower()

                            match_start = search_line.find(search_query)
                            if match_start == -1:
                                continue
                            match_end = match_start + len(search_query)

                        # Truncate snippet to 200 chars
                        snippet = line.strip()
                        if len(snippet) > 200:
                            snippet = snippet[:200] + "..."

                        # Get relative path for result
                        relative_path = file_path.relative_to(workspace_root)

                        matches.append(
                            {
                                "file": str(relative_path),
                                "line": line_num,
                                "snippet": snippet,
                                "match_start": match_start,
                                "match_end": match_end,
                            }
                        )

            except (OSError, PermissionError):
                # Skip files we can't read
                continue
            except Exception as e:
                # Log unexpected errors but continue searching
                logger.warning(f"Unexpected error searching {file_path}: {e}")
                continue

        result = {
            "query": query,
            "use_regex": use_regex,
            "files_searched": files_searched,
            "matches": matches,
            "truncated": truncated,
        }

        return self._create_success_response(
            result=result,
            message=f"Found {len(matches)} matches in {files_searched} files",
        )

    """
    {
      "name": "write_file",
      "description": "Write file within workspace with safety checks. Requires filesystem_writes_enabled. Supports create/overwrite/append modes. Returns bytes written and mode used.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "File path relative to workspace"
          },
          "content": {
            "type": "string",
            "description": "Content to write"
          },
          "mode": {
            "type": "string",
            "description": "Write mode: create, overwrite, append",
            "default": "create"
          }
        },
        "required": ["path", "content"]
      }
    }
    """

    async def write_file(
        self,
        path: Annotated[str, Field(description="File path relative to workspace")],
        content: Annotated[str, Field(description="Content to write")],
        mode: Annotated[str, Field(description="Write mode: create, overwrite, append")] = "create",
    ) -> dict:
        """Write file within workspace with safety checks. Requires filesystem_writes_enabled. Supports create/overwrite/append modes. Returns bytes written and mode used."""
        # Check if writes are enabled
        if not self.config.filesystem_writes_enabled:
            return self._create_error_response(
                error="writes_disabled",
                message="Filesystem writes are disabled. Set filesystem_writes_enabled=true in configuration.",
            )

        # Validate mode
        valid_modes = ["create", "overwrite", "append"]
        if mode not in valid_modes:
            return self._create_error_response(
                error="invalid_mode",
                message=f"Invalid mode '{mode}'. Valid modes: {', '.join(valid_modes)}",
            )

        # Check content size limit
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > self.config.filesystem_max_write_bytes:
            return self._create_error_response(
                error="write_too_large",
                message=f"Content size ({content_bytes} bytes) exceeds max write limit "
                f"({self.config.filesystem_max_write_bytes} bytes)",
            )

        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Check mode-specific preconditions
        existed_before = resolved.exists()

        if mode == "create" and existed_before:
            return self._create_error_response(
                error="file_exists",
                message=f"File already exists (mode=create): {path}. Use mode='overwrite' to replace or mode='append' to add content.",
            )

        if mode == "overwrite" and not existed_before:
            # Allow overwrite to create new file (like mode='create')
            pass

        # Perform write operation
        try:
            if mode == "append":
                # Append mode
                with open(resolved, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                # Create or overwrite mode
                with open(resolved, "w", encoding="utf-8") as f:
                    f.write(content)

            result = {
                "path": path,
                "bytes_written": content_bytes,
                "mode": mode,
                "existed_before": existed_before,
            }

            return self._create_success_response(
                result=result, message=f"Wrote {content_bytes} bytes to {path} (mode={mode})"
            )

        except PermissionError:
            return self._create_error_response(
                error="permission_denied", message=f"Permission denied writing to: {path}"
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"Error writing to {path}: {str(e)}"
            )

    """
    {
      "name": "apply_text_edit",
      "description": "Apply exact text replacement in file within workspace. Requires filesystem_writes_enabled and exact match. Use replace_all for multiple occurrences. Returns replacement count and size delta.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "File path relative to workspace"
          },
          "expected_text": {
            "type": "string",
            "description": "Exact text to find and replace"
          },
          "replacement_text": {
            "type": "string",
            "description": "Replacement text"
          },
          "replace_all": {
            "type": "boolean",
            "description": "Replace all occurrences",
            "default": false
          }
        },
        "required": ["path", "expected_text", "replacement_text"]
      }
    }
    """

    async def apply_text_edit(
        self,
        path: Annotated[str, Field(description="File path relative to workspace")],
        expected_text: Annotated[str, Field(description="Exact text to find and replace")],
        replacement_text: Annotated[str, Field(description="Replacement text")],
        replace_all: Annotated[bool, Field(description="Replace all occurrences")] = False,
    ) -> dict:
        """Apply exact text replacement in file within workspace. Requires filesystem_writes_enabled and exact match. Use replace_all for multiple occurrences. Returns replacement count and size delta."""
        # Check if writes are enabled
        if not self.config.filesystem_writes_enabled:
            return self._create_error_response(
                error="writes_disabled",
                message="Filesystem writes are disabled. Set filesystem_writes_enabled=true in configuration.",
            )

        # Validate expected_text
        if not expected_text:
            return self._create_error_response(
                error="empty_expected_text",
                message="expected_text cannot be empty. Provide exact text to match.",
            )

        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Check if file exists and is a regular file
        if not resolved.exists():
            return self._create_error_response(error="not_found", message=f"File not found: {path}")

        if not resolved.is_file():
            return self._create_error_response(
                error="not_a_file", message=f"Path is not a file: {path}"
            )

        # Read file contents
        try:
            with open(resolved, encoding="utf-8", errors="replace") as f:
                original_content = f.read()

            original_size = len(original_content.encode("utf-8"))

        except PermissionError:
            return self._create_error_response(
                error="permission_denied", message=f"Permission denied reading file: {path}"
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"Error reading file {path}: {str(e)}"
            )

        # Count occurrences
        occurrences = original_content.count(expected_text)

        if occurrences == 0:
            return self._create_error_response(
                error="match_not_found",
                message=f"expected_text not found in file: {path}. No changes made.",
            )

        if occurrences > 1 and not replace_all:
            return self._create_error_response(
                error="multiple_matches",
                message=f"expected_text found {occurrences} times in {path}. "
                f"Use replace_all=true to replace all occurrences.",
            )

        # Perform replacement
        if replace_all:
            new_content = original_content.replace(expected_text, replacement_text)
            replacements = occurrences
        else:
            # Replace only first occurrence (occurrences == 1 at this point)
            new_content = original_content.replace(expected_text, replacement_text, 1)
            replacements = 1

        # Check new size limit
        new_size = len(new_content.encode("utf-8"))
        if new_size > self.config.filesystem_max_write_bytes:
            return self._create_error_response(
                error="write_too_large",
                message=f"Resulting file size ({new_size} bytes) exceeds max write limit "
                f"({self.config.filesystem_max_write_bytes} bytes)",
            )

        # Calculate lines changed (approximate)
        original_lines = original_content.splitlines()
        new_lines = new_content.splitlines()
        lines_changed = abs(len(new_lines) - len(original_lines)) + replacements

        # Write atomically (temp file + rename)
        try:
            # Create temp file in same directory for atomic rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=resolved.parent, prefix=f".{resolved.name}.", suffix=".tmp"
            )

            try:
                # Write to temp file
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    f.write(new_content)

                # Atomic rename
                os.replace(temp_path, resolved)

            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    # Ignore errors during temp file cleanup; not critical if deletion fails
                    pass
                raise

            result = {
                "path": path,
                "bytes_written": new_size,
                "replacements": replacements,
                "original_size": original_size,
                "new_size": new_size,
                "lines_changed": lines_changed,
            }

            return self._create_success_response(
                result=result,
                message=f"Applied {replacements} replacement(s) to {path}",
            )

        except PermissionError:
            return self._create_error_response(
                error="permission_denied", message=f"Permission denied writing to: {path}"
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"Error writing to {path}: {str(e)}"
            )

    """
    {
      "name": "create_directory",
      "description": "Create directory within workspace with optional parent creation. Requires filesystem_writes_enabled. Idempotent (success if exists). Returns created flag.",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Directory path relative to workspace"
          },
          "parents": {
            "type": "boolean",
            "description": "Create parent directories if needed",
            "default": true
          }
        },
        "required": ["path"]
      }
    }
    """

    async def create_directory(
        self,
        path: Annotated[str, Field(description="Directory path relative to workspace")],
        parents: Annotated[bool, Field(description="Create parent directories if needed")] = True,
    ) -> dict:
        """Create directory within workspace with optional parent creation. Requires filesystem_writes_enabled. Idempotent (success if exists). Returns created flag."""
        # Check if writes are enabled
        if not self.config.filesystem_writes_enabled:
            return self._create_error_response(
                error="writes_disabled",
                message="Filesystem writes are disabled. Set filesystem_writes_enabled=true in configuration.",
            )

        # Resolve and validate path
        resolved = self._resolve_path(path)
        if isinstance(resolved, dict):
            return resolved  # Error response

        # Check if path exists
        if resolved.exists():
            if resolved.is_dir():
                # Already exists - idempotent success
                result = {"path": path, "created": False, "parents_created": 0}
                return self._create_success_response(
                    result=result, message=f"Directory already exists: {path}"
                )
            else:
                # Exists but is not a directory
                return self._create_error_response(
                    error="not_a_directory", message=f"Path exists but is not a directory: {path}"
                )

        # Create directory
        try:
            if parents:
                # Count parents that will be created
                parents_to_create = []
                check_path = resolved.parent
                workspace_root = self._get_workspace_root()

                while check_path != workspace_root and not check_path.exists():
                    parents_to_create.append(check_path)
                    check_path = check_path.parent

                # Create with parents
                resolved.mkdir(parents=True, exist_ok=True)
                parents_created = len(parents_to_create)
            else:
                # Create without parents (will fail if parent doesn't exist)
                resolved.mkdir(parents=False, exist_ok=True)
                parents_created = 0

            result = {"path": path, "created": True, "parents_created": parents_created}

            return self._create_success_response(
                result=result, message=f"Created directory: {path}"
            )

        except FileNotFoundError:
            return self._create_error_response(
                error="parent_not_found",
                message=f"Parent directory does not exist: {path}. Use parents=true to create.",
            )
        except PermissionError:
            return self._create_error_response(
                error="permission_denied", message=f"Permission denied creating directory: {path}"
            )
        except OSError as e:
            return self._create_error_response(
                error="os_error", message=f"Error creating directory {path}: {str(e)}"
            )
