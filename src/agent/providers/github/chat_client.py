"""
GitHub Models chat client implementation using Azure AI Inference SDK.

This module provides GitHubChatClient that integrates GitHub Models
with the Microsoft Agent Framework. GitHub Models uses Azure's OpenAI-compatible
API at https://models.inference.ai.azure.com.
"""

import logging

from agent_framework.openai import OpenAIChatClient

from .auth import get_github_token

logger = logging.getLogger(__name__)


class GitHubChatClient(OpenAIChatClient):
    """Chat client for GitHub Models using Azure AI Inference SDK.

    This client extends OpenAIChatClient since GitHub Models uses an
    OpenAI-compatible API with model parameter in request body (not deployment path).

    Args:
        model_id: Model name (e.g., "gpt-5-nano", "gpt-4o-mini", "Mistral-small", "Meta-Llama-3.1-8B-Instruct")
        token: GitHub token (optional, will use get_github_token() if not provided)

    Example:
        >>> client = GitHubChatClient(model_id="gpt-5-nano")
        >>> # Token automatically fetched from GITHUB_TOKEN or gh CLI

    Available Models:
        - gpt-5-nano (default), gpt-4o-mini, gpt-4o (OpenAI models)
        - Mistral-small, Mistral-Nemo, Mistral-large-2407 (Mistral models)
        - Meta-Llama-3.1-8B-Instruct, Meta-Llama-3.1-70B-Instruct, Meta-Llama-3.1-405B-Instruct
        - AI21-Jamba-Instruct
    """

    # OpenTelemetry provider name for tracing
    OTEL_PROVIDER_NAME = "github"

    def __init__(self, model_id: str, token: str | None = None):
        """Initialize GitHubChatClient with model and authentication.

        Args:
            model_id: GitHub model name
            token: GitHub token (optional)

        Raises:
            ValueError: If authentication fails
        """
        # Get token if not provided
        if token is None:
            token = get_github_token()

        # Initialize OpenAI client with GitHub Models endpoint
        # GitHub Models uses OpenAI-compatible API with model in request body
        super().__init__(
            model_id=model_id,
            base_url="https://models.inference.ai.azure.com",
            api_key=token,
        )

        logger.info(f"GitHubChatClient initialized with model: {model_id}")
