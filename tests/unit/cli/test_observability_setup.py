"""Unit tests for observability setup in CLI modules.

Tests verify that observability is properly initialized in both
execution.py (single prompt) and interactive.py (chat mode) modules.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.config.schema import AgentSettings


@pytest.fixture
def mock_settings_otel_disabled():
    """Config with telemetry disabled."""
    config = AgentSettings()
    config.providers.enabled = ["openai"]
    config.providers.openai.api_key = "test-key"
    config.telemetry.enabled = False
    return config


@pytest.fixture
def mock_settings_otel_explicit():
    """Config with telemetry explicitly enabled."""
    config = AgentSettings()
    config.providers.enabled = ["openai"]
    config.providers.openai.api_key = "test-key"
    config.telemetry.enabled = True
    return config


@pytest.fixture
def mock_settings_otel_auto():
    """Config without explicit telemetry setting (for auto-detection)."""
    config = AgentSettings()
    config.providers.enabled = ["openai"]
    config.providers.openai.api_key = "test-key"
    config.telemetry.enabled = False
    config.telemetry.otlp_endpoint = "http://localhost:4317"
    return config


@pytest.mark.unit
@pytest.mark.cli
class TestExecutionObservabilitySetup:
    """Tests for observability setup in execution.py (single prompt mode)."""

    @pytest.mark.asyncio
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution._execute_query")
    async def test_observability_enabled_when_explicit(
        self,
        mock_execute,
        mock_logging,
        mock_agent,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_explicit,
    ):
        """Test observability is enabled when explicitly configured."""
        from agent.cli.execution import run_single_prompt

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_explicit
        mock_execute.return_value = "test response"

        # Execute
        await run_single_prompt("test prompt", verbose=False, quiet=True)

        # Verify setup_observability was called
        mock_setup_otel.assert_called_once_with(
            enable_sensitive_data=mock_settings_otel_explicit.enable_sensitive_data,
            otlp_endpoint=mock_settings_otel_explicit.otlp_endpoint,
            applicationinsights_connection_string=mock_settings_otel_explicit.applicationinsights_connection_string,
        )

    @pytest.mark.asyncio
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution._execute_query")
    async def test_observability_auto_detected_when_endpoint_available(
        self,
        mock_execute,
        mock_logging,
        mock_agent,
        mock_check_endpoint,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_auto,
    ):
        """Test observability auto-detection when endpoint is available."""
        from agent.cli.execution import run_single_prompt

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_auto
        mock_check_endpoint.return_value = True  # Endpoint is available
        mock_execute.return_value = "test response"

        # Execute
        await run_single_prompt("test prompt", verbose=False, quiet=True)

        # Verify auto-detection was attempted
        mock_check_endpoint.assert_called_once_with(mock_settings_otel_auto.otlp_endpoint)

        # Verify setup_observability was called (auto-enabled)
        mock_setup_otel.assert_called_once()

    @pytest.mark.asyncio
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution._execute_query")
    async def test_observability_not_enabled_when_endpoint_unavailable(
        self,
        mock_execute,
        mock_logging,
        mock_agent,
        mock_check_endpoint,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_auto,
    ):
        """Test observability is not enabled when endpoint is unavailable."""
        from agent.cli.execution import run_single_prompt

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_auto
        mock_check_endpoint.return_value = False  # Endpoint NOT available
        mock_execute.return_value = "test response"

        # Execute
        await run_single_prompt("test prompt", verbose=False, quiet=True)

        # Verify auto-detection was attempted
        mock_check_endpoint.assert_called_once_with(mock_settings_otel_auto.otlp_endpoint)

        # Verify setup_observability was NOT called
        mock_setup_otel.assert_not_called()

    @pytest.mark.asyncio
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution._execute_query")
    async def test_observability_not_enabled_when_disabled(
        self,
        mock_execute,
        mock_logging,
        mock_agent,
        mock_check_endpoint,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_disabled,
    ):
        """Test observability is not enabled when disabled and endpoint unavailable."""
        from agent.cli.execution import run_single_prompt

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_disabled
        mock_check_endpoint.return_value = False  # Endpoint not available
        mock_execute.return_value = "test response"

        # Execute
        await run_single_prompt("test prompt", verbose=False, quiet=True)

        # Verify setup_observability was NOT called
        mock_setup_otel.assert_not_called()


@pytest.mark.unit
@pytest.mark.cli
class TestInteractiveObservabilitySetup:
    """Tests for observability setup in interactive.py (chat mode)."""

    @pytest.mark.asyncio
    @patch("agent.cli.interactive.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.cli.interactive.ThreadPersistence")
    @patch("agent.cli.interactive.PromptSession")
    @patch("agent.cli.interactive.setup_session_logging")
    async def test_observability_enabled_when_explicit(
        self,
        mock_logging,
        mock_session,
        mock_persistence,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_explicit,
    ):
        """Test observability is enabled when explicitly configured."""
        from agent.cli.interactive import run_chat_mode

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_explicit

        # Mock prompt session to exit immediately
        mock_prompt_instance = AsyncMock()
        mock_prompt_instance.prompt_async.side_effect = EOFError()
        mock_session.return_value = mock_prompt_instance

        # Execute (will exit on first prompt due to EOFError)
        await run_chat_mode(quiet=True, verbose=False)

        # Verify setup_observability was called
        mock_setup_otel.assert_called_once_with(
            enable_sensitive_data=mock_settings_otel_explicit.enable_sensitive_data,
            otlp_endpoint=mock_settings_otel_explicit.otlp_endpoint,
            applicationinsights_connection_string=mock_settings_otel_explicit.applicationinsights_connection_string,
        )

    @pytest.mark.asyncio
    @patch("agent.cli.interactive.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent.cli.interactive.ThreadPersistence")
    @patch("agent.cli.interactive.PromptSession")
    @patch("agent.cli.interactive.setup_session_logging")
    async def test_observability_auto_detected_when_endpoint_available(
        self,
        mock_logging,
        mock_session,
        mock_persistence,
        mock_check_endpoint,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_auto,
    ):
        """Test observability auto-detection when endpoint is available."""
        from agent.cli.interactive import run_chat_mode

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_auto
        mock_check_endpoint.return_value = True  # Endpoint is available

        # Mock prompt session to exit immediately
        mock_prompt_instance = AsyncMock()
        mock_prompt_instance.prompt_async.side_effect = EOFError()
        mock_session.return_value = mock_prompt_instance

        # Execute (will exit on first prompt)
        await run_chat_mode(quiet=True, verbose=False)

        # Verify auto-detection was attempted
        mock_check_endpoint.assert_called_once_with(mock_settings_otel_auto.otlp_endpoint)

        # Verify setup_observability was called (auto-enabled)
        mock_setup_otel.assert_called_once()

    @pytest.mark.asyncio
    @patch("agent.cli.interactive.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent.cli.interactive.ThreadPersistence")
    @patch("agent.cli.interactive.PromptSession")
    @patch("agent.cli.interactive.setup_session_logging")
    async def test_observability_not_enabled_when_endpoint_unavailable(
        self,
        mock_logging,
        mock_session,
        mock_persistence,
        mock_check_endpoint,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_auto,
    ):
        """Test observability is not enabled when endpoint is unavailable."""
        from agent.cli.interactive import run_chat_mode

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_auto
        mock_check_endpoint.return_value = False  # Endpoint NOT available

        # Mock prompt session to exit immediately
        mock_prompt_instance = AsyncMock()
        mock_prompt_instance.prompt_async.side_effect = EOFError()
        mock_session.return_value = mock_prompt_instance

        # Execute
        await run_chat_mode(quiet=True, verbose=False)

        # Verify auto-detection was attempted
        mock_check_endpoint.assert_called_once_with(mock_settings_otel_auto.otlp_endpoint)

        # Verify setup_observability was NOT called
        mock_setup_otel.assert_not_called()


@pytest.mark.unit
@pytest.mark.cli
class TestObservabilitySpanCreation:
    """Tests for span creation during execution."""

    @pytest.mark.asyncio
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent_framework.observability.get_tracer")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution.execute_with_visualization")
    async def test_span_created_when_observability_enabled(
        self,
        mock_execute_viz,
        mock_logging,
        mock_agent,
        mock_tracer,
        mock_setup_otel,
        mock_settings_loader,
        mock_settings_otel_explicit,
    ):
        """Test that spans are created when observability is enabled."""
        from agent.cli.execution import run_single_prompt

        # Setup
        mock_settings_loader.return_value = mock_settings_otel_explicit
        mock_execute_viz.return_value = "test response"

        # Mock tracer
        mock_span = MagicMock()
        mock_tracer_instance = MagicMock()
        mock_tracer_instance.start_as_current_span.return_value.__enter__ = MagicMock(
            return_value=mock_span
        )
        mock_tracer_instance.start_as_current_span.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_tracer.return_value = mock_tracer_instance

        # Execute
        await run_single_prompt("test prompt", verbose=True, quiet=False)

        # Verify tracer was retrieved
        mock_tracer.assert_called_once()

        # Verify span was started
        mock_tracer_instance.start_as_current_span.assert_called_once()

        # Directly check that expected attributes were set
        from unittest import mock

        mock_span.set_attribute.assert_any_call("session.id", mock.ANY)
        mock_span.set_attribute.assert_any_call("mode", "single-prompt")
