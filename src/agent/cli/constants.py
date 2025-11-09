"""Constants for CLI module."""


class Commands:
    """CLI command aliases."""

    EXIT = ["exit", "quit", "q"]
    HELP = ["help", "?", "/help"]
    CLEAR = ["/clear", "clear"]
    CONTINUE = ["/continue"]
    PURGE = ["/purge"]


class ExitCodes:
    """Standard exit codes."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    INTERRUPTED = 130
