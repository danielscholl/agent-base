"""Middleware functions for Agent execution pipeline.

This module provides middleware functions for logging and event emission
in the agent request/response pipeline. Middleware allows automatic event
tracking without modifying individual tools.

Middleware Types:
    - Agent-level: Wrap entire agent execution (LLM calls)
    - Function-level: Wrap individual tool calls

Event Emission:
    Middleware emits execution events for display visualization when
    should_show_visualization() returns True. This enables real-time
    execution tree display without coupling tools to display logic.
"""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

# TYPE_CHECKING import for forward reference
from typing import TYPE_CHECKING, Any, cast

from agent_framework import (
    AgentRunContext,
    FunctionInvocationContext,
    FunctionMiddleware,
)

from agent.config.manager import load_config
from agent.config.schema import AgentSettings

if TYPE_CHECKING:
    from agent.trace_logger import TraceLogger

logger = logging.getLogger(__name__)

# Global trace logger instance (set by session setup)
_trace_logger: "TraceLogger | None" = None


def set_trace_logger(trace_logger: "TraceLogger | None") -> None:
    """Set the global trace logger instance.

    Args:
        trace_logger: TraceLogger instance or None
    """
    global _trace_logger
    _trace_logger = trace_logger


def get_trace_logger() -> "TraceLogger | None":
    """Get the current trace logger instance.

    Returns:
        TraceLogger instance or None
    """
    return _trace_logger


def _extract_model_from_config(config: AgentSettings) -> str | None:
    """Extract model name from config based on provider.

    Args:
        config: Agent configuration

    Returns:
        Model name or None
    """
    provider = config.llm_provider
    if provider == "openai":
        return config.openai_model
    elif provider == "anthropic":
        return config.anthropic_model
    elif provider == "azure":
        return config.azure_openai_deployment
    elif provider == "gemini":
        return config.gemini_model
    elif provider == "github":
        return config.github_model
    elif provider == "local":
        return config.local_model
    elif provider == "foundry":
        return config.azure_model_deployment
    return None


# ============================================================================
# Agent-Level Middleware
# ============================================================================


async def agent_run_logging_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Log agent execution lifecycle and emit LLM request/response events.

    This middleware:
    - Logs agent execution start/complete
    - Emits LLMRequestEvent before LLM call
    - Emits LLMResponseEvent after LLM call with duration
    - Captures trace-level LLM request/response data (if enabled)
    - Only emits events if should_show_visualization() is True

    Args:
        context: Agent run context containing messages and state
        next: Next middleware in chain

    Example:
        >>> middleware = {"agent": [agent_run_logging_middleware]}
        >>> agent = chat_client.create_agent(..., middleware=middleware)
    """
    from agent.display import (
        LLMRequestEvent,
        LLMResponseEvent,
        get_event_emitter,
        should_show_visualization,
    )

    logger.debug("Agent run starting...")

    # Generate request ID for trace logging
    request_id = str(uuid.uuid4())

    # Load config for trace logging if enabled (reused for request and response)
    trace_logger = get_trace_logger()
    config = load_config() if trace_logger else None

    # Emit LLM request event
    llm_event_id = None
    if should_show_visualization():
        message_count = len(context.messages) if hasattr(context, "messages") else 0
        event = LLMRequestEvent(message_count=message_count)
        llm_event_id = event.event_id
        get_event_emitter().emit(event)
        logger.debug(f"Emitted LLM request event with {message_count} messages")

    # Trace logging: Log request data with full context
    if trace_logger:
        try:
            # Extract conversation messages
            messages = []
            if hasattr(context, "messages"):
                for msg in context.messages:
                    if hasattr(msg, "to_dict"):
                        messages.append(msg.to_dict())
                    elif hasattr(msg, "model_dump"):
                        messages.append(msg.model_dump())
                    elif hasattr(msg, "dict"):
                        messages.append(msg.dict())
                    else:
                        messages.append({"content": str(msg)})

            # Get model and provider from config (already loaded at middleware start)
            assert config is not None, "Config should be loaded when trace logger is enabled"
            provider = config.llm_provider
            model = _extract_model_from_config(config)

            # Extract FULL payload info if include_messages is enabled
            system_instructions: str | None = None
            tools_summary: dict[str, Any] | None = None

            if trace_logger.include_messages:
                if hasattr(context, "agent"):
                    agent = context.agent

                    # Get system instructions and tools from chat_options
                    if hasattr(agent, "chat_options"):
                        chat_options = agent.chat_options

                        # Get instructions
                        if hasattr(chat_options, "instructions") and chat_options.instructions:
                            system_instructions = chat_options.instructions

                        # Get tools
                        if hasattr(chat_options, "tools") and chat_options.tools:
                            tools = chat_options.tools
                            tools_data = []
                            for tool in tools:
                                tool_dict = (
                                    tool.to_dict()
                                    if hasattr(tool, "to_dict")
                                    else {"name": str(tool)}
                                )
                                tool_json = json.dumps(tool_dict, default=str)
                                tools_data.append(
                                    {
                                        "name": tool_dict.get("name", "unknown"),
                                        "description": (
                                            tool_dict.get("description", "")[:100]
                                            if tool_dict.get("description")
                                            else ""
                                        ),
                                        "estimated_tokens": len(tool_json) // 4,
                                    }
                                )

                            tools_summary = {
                                "count": len(tools),
                                "tools": tools_data,
                                "total_estimated_tokens": sum(
                                    t["estimated_tokens"] for t in tools_data
                                ),
                            }

            # Log request using TraceLogger
            trace_logger.log_request(
                request_id=request_id,
                messages=messages,
                model=model,
                provider=provider,
                system_instructions=system_instructions,
                tools_summary=tools_summary,
            )

        except Exception as e:
            logger.debug(f"Failed to log trace request: {e}")

    start_time = time.time()

    try:
        await next(context)
        duration = time.time() - start_time
        latency_ms = duration * 1000
        logger.debug("Agent run completed successfully")

        # Emit LLM response event
        if should_show_visualization() and llm_event_id:
            response_event = LLMResponseEvent(duration=duration, event_id=llm_event_id)
            get_event_emitter().emit(response_event)
            logger.debug(f"Emitted LLM response event ({duration:.2f}s)")

        # Trace logging: Log response data with token usage
        if trace_logger:
            try:
                # Extract response content and token usage from result
                response_content = ""
                input_tokens = None
                output_tokens = None
                total_tokens = None

                if hasattr(context, "result") and context.result:
                    result = context.result
                    # Extract content
                    if hasattr(result, "text"):
                        response_content = str(result.text)
                    elif hasattr(result, "content"):
                        response_content = str(result.content)
                    elif hasattr(result, "data"):
                        response_content = str(result.data)
                    else:
                        response_content = str(result)

                    # Extract token usage from result.usage_details
                    if hasattr(result, "usage_details") and result.usage_details:
                        usage = result.usage_details
                        if hasattr(usage, "input_token_count"):
                            input_tokens = usage.input_token_count
                        if hasattr(usage, "output_token_count"):
                            output_tokens = usage.output_token_count
                        if hasattr(usage, "total_token_count"):
                            total_tokens = usage.total_token_count

                # Try to extract token usage from various locations
                # Check thread for usage info (agent-framework stores it in thread messages)
                if hasattr(context, "thread") and context.thread:
                    thread = context.thread
                    if hasattr(thread, "messages") and thread.messages:
                        # Check last message (assistant response) for usage
                        last_msg = thread.messages[-1]

                        # Check for usage in message
                        if hasattr(last_msg, "usage") and last_msg.usage:
                            usage = last_msg.usage
                            if hasattr(usage, "input_token_count"):
                                input_tokens = usage.input_token_count
                            if hasattr(usage, "output_token_count"):
                                output_tokens = usage.output_token_count
                            if hasattr(usage, "total_token_count"):
                                total_tokens = usage.total_token_count

                        # Also check contents for UsageContent
                        if hasattr(last_msg, "contents") and last_msg.contents:
                            for content in last_msg.contents:
                                # UsageContent has usage attribute
                                if hasattr(content, "usage") and content.usage:
                                    usage = content.usage
                                    if hasattr(usage, "input_token_count"):
                                        input_tokens = usage.input_token_count
                                    if hasattr(usage, "output_token_count"):
                                        output_tokens = usage.output_token_count
                                    if hasattr(usage, "total_token_count"):
                                        total_tokens = usage.total_token_count

                # Also check metadata for usage info
                if hasattr(context, "metadata") and context.metadata:
                    metadata = context.metadata
                    if "usage" in metadata:
                        usage = metadata["usage"]
                        if isinstance(usage, dict):
                            input_tokens = usage.get("input_token_count") or usage.get(
                                "input_tokens"
                            )
                            output_tokens = usage.get("output_token_count") or usage.get(
                                "output_tokens"
                            )
                            total_tokens = usage.get("total_token_count") or usage.get(
                                "total_tokens"
                            )

                # Get model from config (loaded once at middleware start)
                model = _extract_model_from_config(config) if config else None

                trace_logger.log_response(
                    request_id=request_id,
                    response_content=response_content,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                )
            except Exception as e:
                logger.debug(f"Failed to log trace response: {e}")

    except Exception as e:
        logger.error(f"Agent run failed: {e}")

        # Trace logging: Log error
        if trace_logger:
            try:
                duration = time.time() - start_time
                latency_ms = duration * 1000
                trace_logger.log_response(
                    request_id=request_id,
                    response_content="",
                    latency_ms=latency_ms,
                    error=str(e),
                )
            except Exception as log_err:
                logger.debug(f"Failed to log trace error: {log_err}")

        # Classify and wrap provider exceptions for better error messages
        from agent.cli.error_handler import classify_provider_error

        wrapped = classify_provider_error(e, config)
        if wrapped:
            # Raise wrapped exception with original as cause (preserves stack trace)
            raise wrapped from e
        else:
            # Unknown error, re-raise as-is
            raise


async def agent_observability_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Track agent execution duration with logging.

    This middleware logs execution duration for all agent runs.
    The agent-framework handles OpenTelemetry instrumentation automatically.

    Args:
        context: Agent run context
        next: Next middleware in chain

    Example:
        >>> middleware = {"agent": [agent_observability_middleware]}
        >>> agent = chat_client.create_agent(..., middleware=middleware)
    """
    start_time = time.time()

    try:
        await next(context)
    finally:
        duration = time.time() - start_time
        logger.info(f"Agent execution took {duration:.2f}s")


# ============================================================================
# Function-Level Middleware
# ============================================================================


async def logging_function_middleware(
    context: FunctionInvocationContext,
    next: Callable,
) -> Any:
    """Middleware to log function/tool calls and emit execution events with OpenTelemetry.

    This middleware:
    - Logs tool execution start/complete/error
    - Emits ToolStartEvent before tool execution
    - Emits ToolCompleteEvent on success with result summary
    - Emits ToolErrorEvent on failure
    - Sets tool context for nested event tracking
    - Creates OpenTelemetry spans for tool execution (when enabled)
    - Only emits events if should_show_visualization() is True

    Args:
        context: Function invocation context with function metadata and arguments
        next: Next middleware in chain

    Returns:
        Result from tool execution

    Example:
        >>> middleware = {"function": [logging_function_middleware]}
        >>> agent = chat_client.create_agent(..., middleware=middleware)
    """
    from agent_framework.observability import OtelAttr, get_meter, get_tracer
    from opentelemetry import trace as ot_trace

    from agent.display import (
        ToolCompleteEvent,
        ToolErrorEvent,
        ToolStartEvent,
        get_current_tool_event_id,
        get_event_emitter,
        set_current_tool_event_id,
        should_show_visualization,
    )
    from agent.observability import get_current_agent_span

    tool_name = context.function.name
    args = context.arguments

    logger.info(f"Tool call: {tool_name}")

    # Emit tool start event (if visualization enabled)
    tool_event_id = None
    parent_id = None
    if should_show_visualization():
        # Get parent event ID for nested tools
        parent_id = get_current_tool_event_id()

        # Convert args to dict for event (using Pydantic v2 model_dump)
        if hasattr(args, "model_dump"):
            args_dict = args.model_dump()
        elif hasattr(args, "dict"):
            # Fallback for Pydantic v1 compatibility
            args_dict = args.dict()
        elif isinstance(args, dict):
            args_dict = args
        else:
            args_dict = {}

        # Sanitize (remove sensitive keys)
        safe_args = {
            k: v
            for k, v in args_dict.items()
            if k not in ["token", "api_key", "password", "secret"]
        }

        event = ToolStartEvent(tool_name=tool_name, arguments=safe_args, parent_id=parent_id)
        tool_event_id = event.event_id
        get_event_emitter().emit(event)

        # Set tool context for child operations (enables nested event display)
        set_current_tool_event_id(tool_event_id)
        logger.debug(f"Set tool context: {tool_name} (event_id: {tool_event_id[:8]}...)")

    # Check if observability is enabled
    config = load_config()
    tracer = get_tracer(__name__) if config.enable_otel else None
    meter = get_meter(__name__) if config.enable_otel else None

    start_time = time.time()

    # Create span context manager (no-op if observability disabled)
    # Prepare parent context for robust nesting
    parent_context = None
    if tracer:
        try:
            from opentelemetry import trace as ot_trace

            current_span = ot_trace.get_current_span()
            # If current span looks invalid, try the saved agent span
            if current_span is None or not getattr(current_span, "is_recording", lambda: False)():
                saved_agent_span = get_current_agent_span()
                if saved_agent_span is not None:
                    parent_context = ot_trace.set_span_in_context(saved_agent_span)
        except Exception:
            parent_context = None

    span_context = (
        tracer.start_as_current_span(f"tool.{tool_name}", context=parent_context)
        if tracer
        else _noop_context_manager()
    )

    with span_context as span:
        try:
            # Set span attributes if observability enabled
            if span and config.enable_otel:
                # Set GenAI span type
                span.set_attribute("span_type", "GenAI")

                # Set operation name and tool info
                span.set_attribute("gen_ai.operation.name", OtelAttr.TOOL_EXECUTION_OPERATION)
                span.set_attribute(OtelAttr.TOOL_NAME, tool_name)

                # Add tool description if available
                if hasattr(context.function, "description"):
                    span.set_attribute(OtelAttr.TOOL_DESCRIPTION, context.function.description)

                # Add tool parameters if sensitive data enabled
                if config.enable_sensitive_data and args:
                    # Convert args to dict for serialization
                    args_data: dict[str, Any] | str
                    if hasattr(args, "model_dump"):
                        args_data = args.model_dump()
                    elif hasattr(args, "dict"):
                        args_data = args.dict()
                    elif isinstance(args, dict):
                        args_data = args
                    else:
                        args_data = str(args)

                    span.set_attribute(
                        OtelAttr.TOOL_ARGUMENTS,
                        json.dumps(args_data) if isinstance(args_data, dict) else args_data,
                    )

            result = await next(context)
            duration = time.time() - start_time
            logger.info(f"Tool call {tool_name} completed successfully ({duration:.2f}s)")

            # Record metrics if observability enabled
            if meter and config.enable_otel:
                duration_histogram = meter.create_histogram(
                    name="tool.execution.duration",
                    description="Tool execution duration in seconds",
                    unit="s",
                )
                duration_histogram.record(duration, {"tool": tool_name, "status": "success"})

            # Set tool result if sensitive data enabled
            if span and config.enable_otel and config.enable_sensitive_data:
                result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                # Truncate to 1000 chars to avoid excessive data
                span.set_attribute(OtelAttr.TOOL_RESULT, result_str[:1000])

            # Emit tool complete event
            if should_show_visualization() and tool_event_id:
                # Extract summary from result
                summary = _extract_tool_summary(tool_name, result)
                complete_event = ToolCompleteEvent(
                    tool_name=tool_name,
                    result_summary=summary,
                    duration=duration,
                    event_id=tool_event_id,
                )
                get_event_emitter().emit(complete_event)

            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Tool call {tool_name} failed: {e}")

            # Record error metrics if observability enabled
            if meter and config.enable_otel:
                duration_histogram = meter.create_histogram(
                    name="tool.execution.duration",
                    description="Tool execution duration in seconds",
                    unit="s",
                )
                duration_histogram.record(duration, {"tool": tool_name, "status": "error"})

            # Capture exception in span
            if span and config.enable_otel:
                span.record_exception(e)
                from opentelemetry.trace import Status, StatusCode

                span.set_status(Status(StatusCode.ERROR, str(e)))

            # Emit tool error event
            if should_show_visualization() and tool_event_id:
                error_event = ToolErrorEvent(
                    tool_name=tool_name,
                    error_message=str(e),
                    duration=duration,
                    event_id=tool_event_id,
                )
                get_event_emitter().emit(error_event)

            raise
        finally:
            # Clear tool context when exiting tool (restore parent)
            if should_show_visualization():
                set_current_tool_event_id(parent_id)
                if parent_id:
                    logger.debug("Restored parent tool context")
                else:
                    logger.debug(f"Cleared tool context: {tool_name}")


def _noop_context_manager() -> Any:
    """No-op context manager for when observability is disabled.

    Returns:
        Context manager that does nothing

    Example:
        >>> with _noop_context_manager() as span:
        ...     # span is None, no telemetry recorded
        ...     pass
    """
    from contextlib import nullcontext

    return nullcontext(None)


def _extract_tool_summary(tool_name: str, result: Any) -> str:
    """Extract human-readable summary from tool result.

    Attempts to extract meaningful summary from common result patterns:
    - Dict with "message" key
    - Dict with "summary" key
    - String result (truncated to 100 chars)
    - Other types return "Complete"

    Args:
        tool_name: Name of the tool
        result: Tool result

    Returns:
        Brief summary string (max 100 chars)

    Example:
        >>> _extract_tool_summary("hello_world", {"message": "Hello, Alice!"})
        'Hello, Alice!'
        >>> _extract_tool_summary("greet_user", "Long result...")
        'Long result...'  # (truncated if > 100 chars)
    """
    if isinstance(result, dict):
        if "message" in result:
            msg = str(result["message"])
            return msg[:100] if len(msg) > 100 else msg
        elif "summary" in result:
            summary = str(result["summary"])
            return summary[:100] if len(summary) > 100 else summary
    elif isinstance(result, str):
        return result[:100] if len(result) > 100 else result

    return "Complete"


# ============================================================================
# Middleware Factory
# ============================================================================


def create_middleware() -> list:
    """Create default middleware for agent and function levels.

    Returns:
        List of middleware (framework auto-categorizes by type)

    Note:
        Memory is handled via ContextProvider, not middleware.
        See MemoryContextProvider for memory management.

    Example:
        >>> from agent.middleware import create_middleware
        >>> middleware = create_middleware()
        >>> agent = chat_client.create_agent(
        ...     name="Agent",
        ...     instructions="...",
        ...     tools=tools,
        ...     middleware=middleware
        ... )
    """
    return [
        agent_run_logging_middleware,
        agent_observability_middleware,
        logging_function_middleware,
    ]


# Backward compatibility
def create_function_middleware() -> list[FunctionMiddleware]:
    """Create list of function middleware (legacy).

    Provided for backward compatibility. Use create_middleware() instead.

    Returns:
        List of function middleware

    Example:
        >>> from agent.middleware import create_function_middleware
        >>> function_mw = create_function_middleware()
    """
    return [cast(FunctionMiddleware, logging_function_middleware)]
