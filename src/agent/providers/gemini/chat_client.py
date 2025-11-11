"""
Google Gemini chat client implementation.

This module provides a custom GeminiChatClient that integrates Google's Gemini
models with the Microsoft Agent Framework by extending BaseChatClient.
"""

import logging
from collections.abc import AsyncIterator
from typing import Any

from agent_framework import (
    BaseChatClient,
    ChatMessage,
    ChatOptions,
    ChatResponse,
    ChatResponseUpdate,
    use_function_invocation,
)
from google import genai

from .types import (
    extract_usage_metadata,
    from_gemini_message,
    to_gemini_message,
    to_gemini_tools,
)

logger = logging.getLogger(__name__)


@use_function_invocation
class GeminiChatClient(BaseChatClient):
    """Chat client for Google Gemini models.

    This client extends BaseChatClient to provide integration with Google's
    Gemini API, supporting both API key authentication (Gemini Developer API)
    and Vertex AI authentication (Google Cloud Platform).

    Args:
        model_id: Gemini model name (e.g., "gemini-2.0-flash-exp", "gemini-2.5-pro")
        api_key: Gemini API key for developer API authentication (optional)
        project_id: GCP project ID for Vertex AI authentication (optional)
        location: GCP location for Vertex AI (e.g., "us-central1") (optional)
        use_vertexai: Whether to use Vertex AI authentication (default: False)

    Example:
        >>> # Using API key
        >>> client = GeminiChatClient(
        ...     model_id="gemini-2.0-flash-exp",
        ...     api_key="your-api-key"
        ... )

        >>> # Using Vertex AI
        >>> client = GeminiChatClient(
        ...     model_id="gemini-2.5-pro",
        ...     project_id="your-gcp-project",
        ...     location="us-central1",
        ...     use_vertexai=True
        ... )
    """

    # OpenTelemetry provider name for tracing
    OTEL_PROVIDER_NAME = "gemini"

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        project_id: str | None = None,
        location: str | None = None,
        use_vertexai: bool = False,
    ):
        """Initialize GeminiChatClient with authentication credentials.

        Args:
            model_id: Gemini model name
            api_key: API key for Gemini Developer API
            project_id: GCP project ID for Vertex AI
            location: GCP location for Vertex AI
            use_vertexai: Use Vertex AI authentication

        Raises:
            ValueError: If required credentials are missing
        """
        super().__init__()

        self.model_id = model_id
        self.use_vertexai = use_vertexai

        # Initialize Google Gen AI client based on authentication method
        if use_vertexai:
            # Vertex AI authentication (uses Google Cloud default credentials)
            if not project_id or not location:
                raise ValueError("Vertex AI authentication requires both project_id and location")
            self.client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
            )
            logger.info(
                f"Initialized Gemini client with Vertex AI (project={project_id}, location={location})"
            )
        else:
            # API key authentication
            if not api_key:
                raise ValueError("API key authentication requires api_key")
            self.client = genai.Client(api_key=api_key)
            logger.info("Initialized Gemini client with API key")

    def _prepare_options(
        self, messages: list[ChatMessage], chat_options: ChatOptions | None = None
    ) -> dict[str, Any]:
        """Prepare generation config from ChatOptions.

        Args:
            messages: List of chat messages
            chat_options: Optional chat configuration

        Returns:
            Dictionary with Gemini generation configuration
        """
        config: dict[str, Any] = {}

        if chat_options:
            # Map temperature
            if chat_options.temperature is not None:
                config["temperature"] = chat_options.temperature

            # Map max_tokens
            if chat_options.max_tokens is not None:
                config["max_output_tokens"] = chat_options.max_tokens

            # Map top_p
            if chat_options.top_p is not None:
                config["top_p"] = chat_options.top_p

            # Handle tools/functions (pass via config for google-genai)
            tools = chat_options.tools() if callable(chat_options.tools) else chat_options.tools
            if tools:
                config["tools"] = to_gemini_tools(tools)

        return config

    def _handle_gemini_error(self, error: Exception) -> Exception:
        """Map Gemini SDK exceptions to agent-framework exceptions.

        Args:
            error: Exception from Gemini SDK

        Returns:
            Mapped exception for agent-framework
        """
        # For now, pass through the original exception
        # In the future, we can map specific Gemini exceptions to framework exceptions
        import traceback

        logger.error(f"Gemini API error: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error

    async def _inner_get_response(
        self, messages: list[ChatMessage], chat_options: ChatOptions | None = None
    ) -> ChatResponse:
        """Get non-streaming response from Gemini API.

        This method is required by BaseChatClient and handles synchronous
        chat completions.

        Args:
            messages: List of chat messages
            chat_options: Optional chat configuration

        Returns:
            ChatResponse with the model's reply

        Raises:
            Exception: If API call fails
        """
        try:
            # Build mapping from function call_id to function name
            call_id_to_name: dict[str, str] = {}
            for m in messages:
                for c in getattr(m, "contents", []) or []:
                    try:
                        # Lazy import to avoid circular types
                        from agent_framework import FunctionCallContent

                        if isinstance(c, FunctionCallContent):
                            call_id_to_name[c.call_id] = c.name
                    except Exception:
                        pass

            # Convert messages to Gemini format
            gemini_messages = [to_gemini_message(msg, call_id_to_name) for msg in messages]

            # Prepare generation config (contains tools when provided)
            config = self._prepare_options(messages, chat_options)

            # Build contents for Gemini API
            # Note: Gemini expects a list of content objects
            contents = []
            for msg in gemini_messages:
                contents.append({"role": msg["role"], "parts": msg["parts"]})

            # Call Gemini API (synchronous)
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config if config else None,
            )

            # Convert response to ChatResponse
            chat_message = from_gemini_message(response)

            # Extract usage metadata
            usage = extract_usage_metadata(response)

            # Create ChatResponse with usage_details (let class handle dict -> UsageDetails)
            return ChatResponse(messages=[chat_message], usage_details=usage or None)

        except Exception as e:
            raise self._handle_gemini_error(e)

    async def _inner_get_streaming_response(
        self, messages: list[ChatMessage], chat_options: ChatOptions | None = None
    ) -> AsyncIterator[ChatResponseUpdate]:
        """Get streaming response from Gemini API.

        This method is required by BaseChatClient and handles streaming
        chat completions, yielding response chunks as they arrive.

        Args:
            messages: List of chat messages
            chat_options: Optional chat configuration

        Yields:
            ChatResponseUpdate objects with response chunks

        Raises:
            Exception: If API call fails
        """
        try:
            # Build mapping from function call_id to function name
            call_id_to_name: dict[str, str] = {}
            for m in messages:
                for c in getattr(m, "contents", []) or []:
                    try:
                        from agent_framework import FunctionCallContent

                        if isinstance(c, FunctionCallContent):
                            call_id_to_name[c.call_id] = c.name
                    except Exception:
                        pass

            # Convert messages to Gemini format
            gemini_messages = [to_gemini_message(msg, call_id_to_name) for msg in messages]

            # Prepare generation config (contains tools when provided)
            config = self._prepare_options(messages, chat_options)

            # Build contents for Gemini API
            contents = []
            for msg in gemini_messages:
                contents.append({"role": msg["role"], "parts": msg["parts"]})

            # Call Gemini API with streaming
            stream = self.client.models.generate_content_stream(
                model=self.model_id,
                contents=contents,
                config=config if config else None,
            )

            # Yield chunks as they arrive
            for chunk in stream:
                if hasattr(chunk, "text") and chunk.text:
                    yield ChatResponseUpdate(
                        text=chunk.text,
                        role="assistant",
                    )

        except Exception as e:
            raise self._handle_gemini_error(e)
