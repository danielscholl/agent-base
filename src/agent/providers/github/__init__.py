"""
GitHub Models provider implementation.

This module provides authentication and chat client for GitHub Models
through the Azure AI Inference SDK.
"""

from .auth import get_github_token
from .chat_client import GitHubChatClient

__all__ = ["get_github_token", "GitHubChatClient"]
