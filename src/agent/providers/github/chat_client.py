"""
GitHub Models chat client implementation using OpenAI-compatible API.

This module provides GitHubChatClient that integrates GitHub Models
with the Microsoft Agent Framework. GitHub Models uses an OpenAI-compatible
API at https://models.github.ai.
"""

import logging

from agent_framework.openai import OpenAIChatClient

from .auth import get_github_token

logger = logging.getLogger(__name__)


class GitHubChatClient(OpenAIChatClient):
    """Chat client for GitHub Models using OpenAI-compatible API.

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

    def __init__(
        self,
        model_id: str,
        token: str | None = None,
        endpoint: str = "https://models.github.ai",
        org: str | None = None,
    ):
        """Initialize GitHubChatClient with model and authentication.

        Args:
            model_id: GitHub model name
            token: GitHub token (optional, will use get_github_token() if not provided)
            endpoint: GitHub Models API endpoint (default: https://models.github.ai)
            org: Organization name for enterprise rate limits (optional)

        Raises:
            ValueError: If authentication fails

        Note:
            For enterprise users, providing org enables organization-scoped requests
            which offer 15,000 requests/hour instead of free tier limits.
            Example: org="microsoft" uses https://models.github.ai/orgs/microsoft
        """
        # Get token if not provided
        if token is None:
            token = get_github_token()

        # Construct base URL with organization scope if provided
        # OpenAI client will append /chat/completions to the base URL
        if org:
            base_url = f"{endpoint}/orgs/{org}/inference"
            logger.info(f"Using organization-scoped endpoint: {base_url}")
        else:
            base_url = f"{endpoint}/inference"
            logger.info(f"Using personal endpoint: {base_url}")

        # Initialize OpenAI client with GitHub Models endpoint
        # GitHub Models uses OpenAI-compatible API with model in request body
        super().__init__(
            model_id=model_id,
            base_url=base_url,
            api_key=token,
        )

        logger.info(f"GitHubChatClient initialized with model: {model_id}")
