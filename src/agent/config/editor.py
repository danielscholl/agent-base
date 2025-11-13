"""Editor integration utilities for opening and editing configuration files."""

import os
import shutil
import subprocess
from pathlib import Path


class EditorError(Exception):
    """Raised when editor operations fail."""

    pass


def detect_editor() -> str | None:
    """Detect available text editor.

    Checks in order:
    1. EDITOR environment variable
    2. VISUAL environment variable
    3. VSCode (code command)
    4. vim
    5. nano
    6. vi

    Returns:
        Editor command if found, None otherwise

    Example:
        >>> editor = detect_editor()
        >>> if editor:
        ...     print(f"Found editor: {editor}")
    """
    # Check environment variables first
    if editor := os.getenv("EDITOR"):
        return editor
    if editor := os.getenv("VISUAL"):
        return editor

    # Check common editors in order of preference (cross-platform)
    common_editors = ["code", "vim", "nano", "vi"]
    for editor in common_editors:
        if shutil.which(editor):
            return editor

    return None


def open_in_editor(file_path: Path, wait: bool = True) -> bool:
    """Open file in detected text editor.

    Args:
        file_path: Path to file to open
        wait: If True, wait for editor to close before returning

    Returns:
        True if editor opened successfully, False otherwise

    Raises:
        EditorError: If no editor found or editor fails to open

    Example:
        >>> from pathlib import Path
        >>> config_path = Path.home() / ".agent" / "settings.json"
        >>> open_in_editor(config_path)
        True
    """
    editor = detect_editor()
    if not editor:
        raise EditorError(
            "No text editor found. Please set EDITOR environment variable "
            "or install one of: code, vim, nano"
        )

    # Ensure file exists
    if not file_path.exists():
        raise EditorError(
            f"File not found: {file_path}\n"
            "To create a new configuration file, run: agent config init"
        )

    try:
        # Special handling for VSCode
        if editor == "code":
            # VSCode: use --wait flag to wait for editor to close
            args = [editor, "--wait" if wait else "", str(file_path)]
            args = [arg for arg in args if arg]  # Remove empty strings
        else:
            # Other editors
            args = [editor, str(file_path)]

        result = subprocess.run(args, check=True)
        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        raise EditorError(f"Failed to open editor '{editor}': {e}") from e
    except FileNotFoundError:
        raise EditorError(f"Editor '{editor}' not found. Please check your installation.") from None


def wait_for_editor(file_path: Path) -> None:
    """Wait for editor to close (blocking).

    This is a convenience function that opens the editor and waits.
    Most of the time you'll want to use open_in_editor(wait=True) instead.

    Args:
        file_path: Path to file being edited

    Raises:
        EditorError: If editor fails

    Example:
        >>> from pathlib import Path
        >>> config_path = Path.home() / ".agent" / "settings.json"
        >>> wait_for_editor(config_path)
    """
    open_in_editor(file_path, wait=True)


def validate_after_edit(file_path: Path) -> tuple[bool, list[str]]:
    """Validate configuration file after editing.

    Args:
        file_path: Path to edited configuration file

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if file is valid JSON and passes schema validation
        - error_messages: List of validation errors (empty if valid)

    Example:
        >>> from pathlib import Path
        >>> config_path = Path.home() / ".agent" / "settings.json"
        >>> is_valid, errors = validate_after_edit(config_path)
        >>> if not is_valid:
        ...     print("Validation errors:", errors)
    """
    from .manager import ConfigurationError, load_config, validate_config

    errors = []

    try:
        # Try to load the file
        settings = load_config(file_path)

        # Validate the settings
        validation_errors = validate_config(settings)
        if validation_errors:
            errors.extend(validation_errors)
            return False, errors

        return True, []

    except ConfigurationError as e:
        errors.append(str(e))
        return False, errors
    except Exception as e:
        errors.append(f"Unexpected error: {e}")
        return False, errors


def edit_and_validate(file_path: Path) -> tuple[bool, list[str]]:
    """Open file in editor, wait for close, then validate.

    This is a convenience function that combines opening in editor
    and validation in one step.

    Args:
        file_path: Path to configuration file

    Returns:
        Tuple of (is_valid, error_messages)

    Raises:
        EditorError: If editor fails to open

    Example:
        >>> from pathlib import Path
        >>> config_path = Path.home() / ".agent" / "settings.json"
        >>> is_valid, errors = edit_and_validate(config_path)
        >>> if not is_valid:
        ...     print("Please fix these errors:")
        ...     for error in errors:
        ...         print(f"  - {error}")
    """
    # Open in editor and wait
    open_in_editor(file_path, wait=True)

    # Validate after editing
    return validate_after_edit(file_path)
