"""Agent - Generic chatbot agent with extensible tool architecture."""

__version__ = "0.1.0"
__author__ = "Daniel Scholl"

from agent.agent import Agent
from agent.config import AgentConfig

__all__ = ["Agent", "AgentConfig", "__version__"]
