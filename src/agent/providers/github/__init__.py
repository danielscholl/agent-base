"""
GitHub Models provider implementation.

This module provides authentication and chat client for GitHub Models
through the GitHub Models API.
"""

from .auth import get_github_org, get_github_token
from .chat_client import GitHubChatClient

__all__ = ["get_github_token", "get_github_org", "GitHubChatClient"]
