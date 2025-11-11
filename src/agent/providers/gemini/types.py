"""
Type definitions and conversion utilities for Gemini provider.

This module provides functions to convert between agent-framework's message
formats and Google Gemini's expected formats.
"""

from typing import Any

from agent_framework import (
    AIFunction,
    ChatMessage,
    FunctionCallContent,
    FunctionResultContent,
    TextContent,
)


def to_gemini_message(
    message: ChatMessage, call_id_to_name: dict[str, str] | None = None
) -> dict[str, Any]:
    """Convert agent-framework ChatMessage to Gemini message format.

    Args:
        message: ChatMessage from agent-framework

    Returns:
        Dictionary in Gemini's message format

    Example:
        >>> msg = ChatMessage(role="user", contents=[TextContent(text="Hello")])
        >>> to_gemini_message(msg)
        {"role": "user", "parts": [{"text": "Hello"}]}
    """
    # Map roles (agent-framework -> Gemini)
    role_mapping = {
        "user": "user",
        "assistant": "model",
        "system": "user",  # Gemini doesn't have system role, treat as user
        "tool": "user",  # Tool results are supplied as user role in Gemini
    }
    # Handle Role enum or string
    role_str = message.role.value if hasattr(message.role, "value") else str(message.role)
    gemini_role = role_mapping.get(role_str, "user")

    # Convert contents to parts
    parts = []

    # Get contents from message (agent-framework uses 'contents' attribute)
    contents = message.contents if hasattr(message, "contents") else []

    # Handle different content types with role-aware rules
    for item in contents:
        if isinstance(item, TextContent):
            # Text content is allowed in any turn
            parts.append({"text": item.text})
            continue

        if isinstance(item, FunctionCallContent):
            # Function call should only appear in a model (assistant) turn
            if gemini_role == "model":
                parts.append({"function_call": {"name": item.name, "args": item.arguments}})  # type: ignore[dict-item]
            # Skip function_call in non-model turns
            continue

        if isinstance(item, FunctionResultContent):
            # Function result should appear only in a user/tool turn
            if gemini_role == "user":
                name = None
                if call_id_to_name and item.call_id in call_id_to_name:
                    name = call_id_to_name[item.call_id]
                # If we can't resolve the name, skip to avoid invalid request
                if not name:
                    continue
                response_dict: dict[str, Any] = {
                    "function_response": {
                        "name": name,
                        "response": {"result": item.result},
                    }
                }
                parts.append(response_dict)
            # Skip function_result in model turns
            continue

    # If no parts were added, attempt to use message.text; otherwise add empty text part
    if not parts:
        # Some ChatMessage instances may expose text; use it if present
        text_value = getattr(message, "text", "")
        parts.append({"text": text_value})

    return {"role": gemini_role, "parts": parts}


def from_gemini_message(gemini_response: Any) -> ChatMessage:
    """Convert Gemini response to agent-framework ChatMessage.

    Args:
        gemini_response: Response object from Gemini API

    Returns:
        ChatMessage for agent-framework

    Example:
        >>> response = gemini_client.generate_content("Hello")
        >>> msg = from_gemini_message(response)
        >>> msg.role
        'assistant'
    """
    content_items: list[TextContent | FunctionCallContent] = []

    # Extract text and function calls from response
    if hasattr(gemini_response, "candidates") and gemini_response.candidates:
        candidate = gemini_response.candidates[0]
        if hasattr(candidate, "content") and candidate.content:
            for part in candidate.content.parts:
                # Text content
                if hasattr(part, "text") and part.text:
                    content_items.append(TextContent(text=part.text))

                # Function call
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    # Generate a call_id if not provided by Gemini
                    call_id = getattr(fc, "id", None) or f"{fc.name}_{id(fc)}"
                    content_items.append(
                        FunctionCallContent(
                            call_id=call_id,
                            name=fc.name,
                            arguments=dict(fc.args) if hasattr(fc, "args") else {},
                        )
                    )

    # Return ChatMessage with contents list
    # Note: agent-framework uses 'contents' (plural) not 'content'
    if not content_items:
        content_items = [TextContent(text="")]

    return ChatMessage(role="assistant", contents=content_items)


def to_gemini_tools(tools: list[AIFunction]) -> list[dict[str, Any]]:
    """Convert agent-framework AIFunction tools to Gemini function declarations.

    Args:
        tools: List of AIFunction objects from agent-framework

    Returns:
        List of Gemini function declaration dictionaries

    Example:
        >>> tools = [AIFunction(name="get_weather", description="Get weather")]
        >>> gemini_tools = to_gemini_tools(tools)
        >>> gemini_tools[0]["name"]
        'get_weather'
    """
    function_declarations = []

    for tool in tools:
        # Extract function schema
        function_declaration = {
            "name": tool.name,
            "description": tool.description or "",
        }

        # Add parameters if available
        # Note: tool.parameters might be a method, so check if callable
        if hasattr(tool, "parameters"):
            params = tool.parameters() if callable(tool.parameters) else tool.parameters
            if params:
                # Convert parameters to Gemini format
                function_declaration["parameters"] = _convert_parameters(params)  # type: ignore[assignment]

        function_declarations.append(function_declaration)

    # Return a single tools object with all function declarations
    return [{"function_declarations": function_declarations}] if function_declarations else []


def _convert_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Convert agent-framework parameter schema to Gemini format.

    Args:
        parameters: Parameter schema from AIFunction

    Returns:
        Gemini-compatible parameter schema
    """
    # Gemini expects OpenAPI-like schema
    gemini_params = {
        "type": "object",
        "properties": {},
    }

    # Copy properties if they exist
    if "properties" in parameters:
        gemini_params["properties"] = parameters["properties"]

    # Copy required fields if they exist
    if "required" in parameters:
        gemini_params["required"] = parameters["required"]

    return gemini_params


def extract_usage_metadata(gemini_response: Any) -> dict[str, Any]:
    """Extract token usage information from Gemini response.

    Args:
        gemini_response: Response object from Gemini API

    Returns:
        Dictionary with usage metadata

    Example:
        >>> usage = extract_usage_metadata(response)
        >>> usage["prompt_tokens"]
        15
    """
    usage = {}

    if hasattr(gemini_response, "usage_metadata"):
        metadata = gemini_response.usage_metadata
        usage["prompt_tokens"] = getattr(metadata, "prompt_token_count", 0)
        usage["completion_tokens"] = getattr(metadata, "candidates_token_count", 0)
        usage["total_tokens"] = getattr(metadata, "total_token_count", 0)

    return usage
