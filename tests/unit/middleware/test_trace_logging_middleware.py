"""Unit tests for trace logging in middleware."""

import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest

from agent.middleware import (
    agent_run_logging_middleware,
    get_trace_logger,
    set_trace_logger,
)
from agent.trace_logger import TraceLogger


@pytest.mark.unit
@pytest.mark.middleware
class TestTraceLoggerGlobal:
    """Test global trace logger getter/setter."""

    def test_get_trace_logger_default_none(self):
        """Test trace logger defaults to None."""
        # Reset to None first
        set_trace_logger(None)
        assert get_trace_logger() is None

    def test_set_and_get_trace_logger(self, tmp_path: Path):
        """Test setting and getting trace logger."""
        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file)

        set_trace_logger(logger)
        assert get_trace_logger() is logger

        # Cleanup
        set_trace_logger(None)

    def test_set_trace_logger_to_none(self):
        """Test setting trace logger to None."""
        set_trace_logger(None)
        assert get_trace_logger() is None


@pytest.mark.unit
@pytest.mark.middleware
class TestMiddlewareTraceLogging:
    """Test trace logging integration in middleware."""

    @pytest.fixture(autouse=True)
    def reset_emitter(self):
        """Reset event emitter and trace logger before each test."""
        from agent.display.events import get_event_emitter

        emitter = get_event_emitter()
        emitter.clear()
        emitter.enable()
        set_trace_logger(None)
        yield
        emitter.clear()
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_without_trace_logger(self):
        """Test middleware works when trace logger is not set."""
        # No trace logger set
        set_trace_logger(None)

        context = Mock(spec=["messages"])
        context.messages = []

        async def mock_next(ctx):
            # Simulate adding a response to context
            ctx.response = Mock(spec=["content"])
            ctx.response.content = "Test response"

        # Should not raise even without trace logger
        await agent_run_logging_middleware(context, mock_next)

    @pytest.mark.asyncio
    async def test_middleware_logs_request(self, tmp_path: Path):
        """Test middleware logs request data to trace logger."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=False)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        # Create mock context with messages
        context = Mock(spec=["messages"])
        context.messages = [
            Mock(model_dump=lambda: {"role": "user", "content": "Hello"}),
            Mock(model_dump=lambda: {"role": "assistant", "content": "Hi"}),
        ]

        async def mock_next(ctx):
            # Simulate response
            ctx.result = Mock(spec=["text", "usage_details"])
            ctx.result.text = "Test response"
            ctx.result.usage_details = None

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Read trace log
        log_entries = trace_file.read_text().strip().split("\n")
        assert len(log_entries) == 2  # Request and response

        # Verify request entry
        request_entry = json.loads(log_entries[0])
        assert request_entry["type"] == "request"
        assert request_entry["model"] == "gpt-4o-mini"
        assert request_entry["provider"] == "openai"
        assert request_entry["message_count"] == 2
        assert "request_id" in request_entry

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_logs_response_with_tokens(self, tmp_path: Path):
        """Test middleware logs response data with token usage."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=False)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        context = Mock(spec=["messages"])
        context.messages = []

        # Mock result with token usage
        result = Mock(spec=["text", "usage_details"])
        result.text = "Test response"
        usage_details = Mock(spec=["input_token_count", "output_token_count", "total_token_count"])
        usage_details.input_token_count = 150
        usage_details.output_token_count = 75
        usage_details.total_token_count = 225
        result.usage_details = usage_details

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Read trace log
        log_entries = trace_file.read_text().strip().split("\n")
        assert len(log_entries) == 2  # Request and response

        # Verify response entry
        response_entry = json.loads(log_entries[1])
        assert response_entry["type"] == "response"
        assert response_entry["model"] == "gpt-4o-mini"
        assert response_entry["response_length"] == len("Test response")
        assert "tokens" in response_entry
        assert response_entry["tokens"]["input"] == 150
        assert response_entry["tokens"]["output"] == 75
        assert response_entry["tokens"]["total"] == 225
        assert "latency_ms" in response_entry

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_logs_response_with_include_messages(self, tmp_path: Path):
        """Test middleware includes full content when include_messages=True."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=True)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        context = Mock(spec=["messages"])
        context.messages = [
            Mock(to_dict=lambda: {"role": "user", "content": "Hello"}),
        ]

        result = Mock(spec=["text", "usage_details"])
        result.text = "Full response content"
        result.usage_details = None

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Read trace log
        log_entries = trace_file.read_text().strip().split("\n")

        # Verify request includes messages
        request_entry = json.loads(log_entries[0])
        assert "messages" in request_entry
        assert request_entry["messages"][0]["content"] == "Hello"

        # Verify response includes content
        response_entry = json.loads(log_entries[1])
        assert response_entry["response"] == "Full response content"
        assert "response_length" not in response_entry

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_logs_error(self, tmp_path: Path):
        """Test middleware logs error when LLM call fails."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        context = Mock(spec=["messages"])
        context.messages = []

        async def mock_next_that_fails(ctx):
            raise ValueError("API rate limit exceeded")

        # Should raise the exception
        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            with pytest.raises(ValueError, match="API rate limit exceeded"):
                await agent_run_logging_middleware(context, mock_next_that_fails)

        # Verify error was logged
        log_entries = trace_file.read_text().strip().split("\n")
        assert len(log_entries) == 2  # Request and error response

        response_entry = json.loads(log_entries[1])
        assert response_entry["type"] == "response"
        assert response_entry["error"] == "API rate limit exceeded"
        assert "latency_ms" in response_entry

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_handles_trace_logger_exception(self, tmp_path: Path):
        """Test middleware handles trace logger exceptions gracefully."""
        # Create trace logger with read-only file to cause write failure
        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file)
        trace_file.chmod(0o444)  # Make read-only
        set_trace_logger(logger)

        context = Mock(spec=["messages"])
        context.messages = []

        response = Mock(spec=["content", "usage"])
        response.content = "Test"
        response.usage = None

        async def mock_next(ctx):
            ctx.response = response

        # Should not raise even if trace logging fails
        # The key assertion is that this completes without raising an exception
        await agent_run_logging_middleware(context, mock_next)

        # Success - middleware handled the exception gracefully
        # Cleanup
        trace_file.chmod(0o644)
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_handles_context_without_attributes(self, tmp_path: Path):
        """Test middleware handles context missing expected attributes."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        # Context without messages, model, provider attributes
        context = Mock(spec=[])  # Empty spec - no attributes

        async def mock_next(ctx):
            pass

        # Should not raise
        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Verify basic logging still works
        log_entries = trace_file.read_text().strip().split("\n")
        assert len(log_entries) == 2  # Request and response

        request_entry = json.loads(log_entries[0])
        assert "request_id" in request_entry

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_converts_messages_to_dict(self, tmp_path: Path):
        """Test middleware converts message objects to dict format."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=True)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        # Messages with different serialization methods
        # Use to_dict
        msg1 = Mock(spec=["to_dict"])
        msg1.to_dict = lambda: {"role": "user", "content": "Using to_dict"}

        # Use model_dump (no to_dict attribute)
        msg2 = Mock(spec=["model_dump"])
        msg2.model_dump = lambda: {"role": "assistant", "content": "Using model_dump"}

        # Plain string (no serialization methods)
        msg3 = "Plain string message"

        context = Mock(spec=["messages"])
        context.messages = [msg1, msg2, msg3]

        result = Mock(spec=["text", "usage_details"])
        result.text = "Response"
        result.usage_details = None

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Verify messages were converted
        log_entries = trace_file.read_text().strip().split("\n")
        request_entry = json.loads(log_entries[0])

        assert len(request_entry["messages"]) == 3
        assert request_entry["messages"][0]["content"] == "Using to_dict"
        assert request_entry["messages"][1]["content"] == "Using model_dump"
        assert request_entry["messages"][2]["content"] == "Plain string message"

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_extracts_response_content(self, tmp_path: Path):
        """Test middleware extracts response content from various formats."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=True)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        context = Mock(spec=["messages"])
        context.messages = []

        # Result with text attribute
        result = Mock(spec=["text", "usage_details"])
        result.text = "Response content"
        result.usage_details = None

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        log_entries = trace_file.read_text().strip().split("\n")
        response_entry = json.loads(log_entries[1])

        assert response_entry["response"] == "Response content"

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_uses_same_request_id(self, tmp_path: Path):
        """Test middleware uses same request_id for request and response."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        context = Mock(spec=["messages"])
        context.messages = []

        response = Mock(spec=["content", "usage"])
        response.content = "Test"
        response.usage = None

        async def mock_next(ctx):
            ctx.response = response

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        log_entries = trace_file.read_text().strip().split("\n")
        request_entry = json.loads(log_entries[0])
        response_entry = json.loads(log_entries[1])

        # Request and response should have same request_id
        assert request_entry["request_id"] == response_entry["request_id"]

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_measures_latency(self, tmp_path: Path):
        """Test middleware measures and logs latency."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o-mini"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["openai"]

        context = Mock(spec=["messages"])
        context.messages = []

        response = Mock(spec=["content", "usage"])
        response.content = "Test"
        response.usage = None

        async def mock_next(ctx):
            await asyncio.sleep(0.05)  # Simulate 50ms delay
            ctx.response = response

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        log_entries = trace_file.read_text().strip().split("\n")
        response_entry = json.loads(log_entries[1])

        # Latency should be >= 50ms
        assert "latency_ms" in response_entry
        assert response_entry["latency_ms"] >= 45.0  # Allow some tolerance

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_logs_system_instructions_and_tools(self, tmp_path: Path):
        """Test middleware captures system instructions and tools when include_messages=True."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=True)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_model = "claude-haiku-4-5-20251001"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["anthropic"]

        # Mock agent with chat_options
        chat_options = Mock()
        chat_options.instructions = "You are a helpful assistant."

        # Mock tools
        tool1 = Mock()
        tool1.to_dict = lambda: {"name": "tool1", "description": "First tool"}
        tool2 = Mock()
        tool2.to_dict = lambda: {"name": "tool2", "description": "Second tool"}
        chat_options.tools = [tool1, tool2]

        agent = Mock()
        agent.chat_options = chat_options

        context = Mock(spec=["messages", "agent"])
        context.messages = []
        context.agent = agent

        result = Mock(spec=["text", "usage_details"])
        result.text = "Response"
        result.usage_details = None

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Verify system instructions and tools captured
        log_entries = trace_file.read_text().strip().split("\n")
        request_entry = json.loads(log_entries[0])

        assert "system_instructions" in request_entry
        assert request_entry["system_instructions"] == "You are a helpful assistant."
        assert "system_instructions_length" in request_entry
        assert "system_instructions_tokens_est" in request_entry

        assert "tools" in request_entry
        assert request_entry["tools"]["count"] == 2
        assert len(request_entry["tools"]["tools"]) == 2
        assert request_entry["tools"]["tools"][0]["name"] == "tool1"
        assert request_entry["tools"]["tools"][1]["name"] == "tool2"
        assert "total_estimated_tokens" in request_entry["tools"]

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_extracts_tokens_from_thread_messages(self, tmp_path: Path):
        """Test middleware extracts token usage from thread messages when not in result."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=False)
        set_trace_logger(logger)

        # Mock config
        mock_settings = Mock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_model = "gpt-4o"

        # Mock thread with usage in last message
        last_message = Mock()
        usage_details = Mock()
        usage_details.input_token_count = 500
        usage_details.output_token_count = 100
        usage_details.total_token_count = 600
        last_message.usage = usage_details
        last_message.contents = []

        thread = Mock()
        thread.messages = [last_message]

        context = Mock(spec=["messages", "thread"])
        context.messages = []
        context.thread = thread

        # Result without usage_details
        result = Mock(spec=["text"])
        result.text = "Response from thread"

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Verify tokens extracted from thread
        log_entries = trace_file.read_text().strip().split("\n")
        response_entry = json.loads(log_entries[1])

        assert "tokens" in response_entry
        assert response_entry["tokens"]["input"] == 500
        assert response_entry["tokens"]["output"] == 100
        assert response_entry["tokens"]["total"] == 600

        # Cleanup
        set_trace_logger(None)

    @pytest.mark.asyncio
    async def test_middleware_extracts_tokens_from_content_usage(self, tmp_path: Path):
        """Test middleware extracts token usage from message contents."""
        import json
        from unittest.mock import patch

        trace_file = tmp_path / "trace.log"
        logger = TraceLogger(trace_file=trace_file, include_messages=False)
        set_trace_logger(logger)

        # Mock config with proper provider structure
        mock_settings = Mock()
        mock_settings.llm_provider = "gemini"
        mock_settings.gemini_model = "gemini-2.0-flash"
        mock_settings.providers = Mock()
        mock_settings.providers.enabled = ["gemini"]

        # Mock thread with usage in content
        usage_content = Mock()
        usage_details = Mock()
        usage_details.input_token_count = 300
        usage_details.output_token_count = 50
        usage_details.total_token_count = 350
        usage_content.usage = usage_details

        last_message = Mock()
        last_message.usage = None  # No usage on message
        last_message.contents = [usage_content]

        thread = Mock()
        thread.messages = [last_message]

        context = Mock(spec=["messages", "thread"])
        context.messages = []
        context.thread = thread

        result = Mock(spec=["text"])
        result.text = "Response"

        async def mock_next(ctx):
            ctx.result = result

        with patch("agent.middleware.load_config") as MockConfig:
            MockConfig.return_value = mock_settings
            await agent_run_logging_middleware(context, mock_next)

        # Verify tokens extracted from content
        log_entries = trace_file.read_text().strip().split("\n")
        response_entry = json.loads(log_entries[1])

        assert "tokens" in response_entry
        assert response_entry["tokens"]["input"] == 300
        assert response_entry["tokens"]["output"] == 50
        assert response_entry["tokens"]["total"] == 350

        # Cleanup
        set_trace_logger(None)
