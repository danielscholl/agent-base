"""Utility functions for CLI module."""

import os
import platform
import sys

from rich.console import Console


def get_console() -> Console:
    """Create Rich console with proper encoding for Windows.

    On Windows in non-interactive mode (subprocess, pipe, etc.), the default
    encoding is often CP1252 which cannot handle Unicode characters. This
    function detects such cases and forces UTF-8 encoding when possible.

    Returns:
        Console: Configured Rich console instance
    """
    if platform.system() == "Windows" and not sys.stdout.isatty():
        # Running in non-interactive mode (subprocess, pipe, etc)
        # Try to use UTF-8 if available
        try:
            import locale

            encoding = locale.getpreferredencoding() or ""
            if "utf" not in encoding.lower():
                # Force UTF-8 for better Unicode support
                os.environ["PYTHONIOENCODING"] = "utf-8"
                # Create console with legacy Windows mode disabled
                return Console(force_terminal=True, legacy_windows=False)
            else:
                return Console()
        except Exception:
            # Fallback to safe ASCII mode if encoding detection fails
            return Console(legacy_windows=True, safe_box=True)
    else:
        # Normal interactive mode or non-Windows
        return Console()
