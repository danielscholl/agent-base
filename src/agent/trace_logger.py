"""Trace-level logging for LLM request/response capture.

Provides structured JSON logging of LLM interactions with token usage,
timing, and optional message content for offline analysis and optimization.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TraceLogger:
    """Logger for capturing detailed LLM request/response traces."""

    def __init__(self, trace_file: Path, include_messages: bool = False):
        """Initialize trace logger.

        Args:
            trace_file: Path to trace log file
            include_messages: Whether to include full message content in traces
        """
        self.trace_file = trace_file
        self.include_messages = include_messages
        self._ensure_trace_file()

    def _ensure_trace_file(self) -> None:
        """Ensure trace log file and directory exist."""
        self.trace_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.trace_file.exists():
            self.trace_file.touch()
            logger.debug(f"Created trace log file: {self.trace_file}")

    def log_interaction(
        self,
        *,
        request_id: str,
        messages: list[dict[str, Any]] | None = None,
        response_content: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        latency_ms: float | None = None,
        provider: str | None = None,
        error: str | None = None,
    ) -> None:
        """Log a complete LLM interaction with request and response data.

        Args:
            request_id: Unique identifier for this request
            messages: Request messages (logged only if include_messages=True)
            response_content: LLM response text
            model: Model name used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total tokens used
            latency_ms: Response latency in milliseconds
            provider: LLM provider name
            error: Error message if request failed
        """
        trace_entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "model": model,
            "provider": provider,
        }

        # Add message data if enabled
        if self.include_messages and messages:
            trace_entry["message_count"] = len(messages)
            trace_entry["messages"] = messages
        elif messages:
            # Include count but not content
            trace_entry["message_count"] = len(messages)

        # Add response data
        if response_content is not None:
            if self.include_messages:
                trace_entry["response"] = response_content
            else:
                # Include length but not content
                trace_entry["response_length"] = len(response_content)

        # Add token usage
        if input_tokens is not None or output_tokens is not None or total_tokens is not None:
            trace_entry["tokens"] = {}
            if input_tokens is not None:
                trace_entry["tokens"]["input"] = input_tokens
            if output_tokens is not None:
                trace_entry["tokens"]["output"] = output_tokens
            if total_tokens is not None:
                trace_entry["tokens"]["total"] = total_tokens

        # Add timing
        if latency_ms is not None:
            trace_entry["latency_ms"] = round(latency_ms, 2)

        # Add error if present
        if error:
            trace_entry["error"] = error

        # Write to trace log file (append mode)
        try:
            with open(self.trace_file, "a") as f:
                json.dump(trace_entry, f)
                f.write("\n")  # Write each entry on its own line
        except Exception as e:
            logger.error(f"Failed to write trace log: {e}")

    def log_request(
        self,
        *,
        request_id: str,
        messages: list[dict[str, Any]],
        model: str | None = None,
        provider: str | None = None,
        system_instructions: str | None = None,
        tools_summary: dict[str, Any] | None = None,
    ) -> None:
        """Log LLM request data.

        Args:
            request_id: Unique identifier for this request
            messages: Request messages
            model: Model name
            provider: Provider name
            system_instructions: System prompt sent to LLM (if include_messages=True)
            tools_summary: Tool definitions summary (if include_messages=True)
        """
        trace_entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "type": "request",
            "model": model,
            "provider": provider,
        }

        if self.include_messages:
            trace_entry["message_count"] = len(messages)
            trace_entry["messages"] = messages

            # Add system instructions if provided
            if system_instructions:
                trace_entry["system_instructions"] = system_instructions
                trace_entry["system_instructions_length"] = len(system_instructions)
                trace_entry["system_instructions_tokens_est"] = len(system_instructions) // 4

            # Add tools summary if provided
            if tools_summary:
                trace_entry["tools"] = tools_summary
        else:
            trace_entry["message_count"] = len(messages)

        try:
            with open(self.trace_file, "a") as f:
                json.dump(trace_entry, f, default=str, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write trace log: {e}")

    def log_response(
        self,
        *,
        request_id: str,
        response_content: str,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
        latency_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        """Log LLM response data with token usage.

        Args:
            request_id: Unique identifier matching the request
            response_content: LLM response text
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            total_tokens: Total tokens used
            latency_ms: Response latency in milliseconds
            error: Error message if request failed
        """
        trace_entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "type": "response",
            "model": model,
        }

        if self.include_messages:
            trace_entry["response"] = response_content
        else:
            trace_entry["response_length"] = len(response_content)

        if input_tokens is not None or output_tokens is not None or total_tokens is not None:
            trace_entry["tokens"] = {}
            if input_tokens is not None:
                trace_entry["tokens"]["input"] = input_tokens
            if output_tokens is not None:
                trace_entry["tokens"]["output"] = output_tokens
            if total_tokens is not None:
                trace_entry["tokens"]["total"] = total_tokens

        if latency_ms is not None:
            trace_entry["latency_ms"] = round(latency_ms, 2)

        if error:
            trace_entry["error"] = error

        try:
            with open(self.trace_file, "a") as f:
                json.dump(trace_entry, f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to write trace log: {e}")
