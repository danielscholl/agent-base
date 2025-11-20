"""Agent - Generic chatbot agent with extensible tool architecture."""

from importlib.metadata import PackageNotFoundError, version

# Read version from package metadata (pyproject.toml)
# This ensures the version shown matches the installed package version
try:
    __version__ = version("agent-base")
except PackageNotFoundError:
    # Fallback for development environments where package isn't installed
    __version__ = "0.0.0.dev"

__author__ = "Daniel Scholl"

from agent.agent import Agent
from agent.config import AgentConfig

__all__ = ["Agent", "AgentConfig", "__version__"]
