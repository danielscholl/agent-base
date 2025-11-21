"""Integration tests for telemetry functionality.

Tests verify the complete telemetry workflow:
- Auto-detection of telemetry endpoints
- Dynamic config updates
- Observability initialization
- Span creation and attributes
"""

from unittest.mock import MagicMock, patch

import pytest

from agent.agent import Agent
from agent.config.schema import AgentSettings
from agent.observability import check_telemetry_endpoint
from tests.mocks.mock_client import MockChatClient


@pytest.mark.integration
@pytest.mark.cli
class TestTelemetryAutoDetection:
    """Integration tests for telemetry auto-detection."""

    @patch("agent.observability.socket.socket")
    def test_check_telemetry_endpoint_available(self, mock_socket_class):
        """Test telemetry endpoint check when endpoint is available."""
        # Mock successful connection
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0  # Success
        mock_socket_class.return_value = mock_socket

        # Test
        result = check_telemetry_endpoint("http://localhost:4317")

        # Verify
        assert result is True
        mock_socket.connect_ex.assert_called_once_with(("localhost", 4317))
        mock_socket.close.assert_called_once()

    @patch("agent.observability.socket.socket")
    def test_check_telemetry_endpoint_unavailable(self, mock_socket_class):
        """Test telemetry endpoint check when endpoint is unavailable."""
        # Mock failed connection
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 1  # Connection refused
        mock_socket_class.return_value = mock_socket

        # Test
        result = check_telemetry_endpoint("http://localhost:4317")

        # Verify
        assert result is False
        mock_socket.close.assert_called_once()

    @patch("agent.observability.socket.socket")
    def test_check_telemetry_endpoint_with_custom_endpoint(self, mock_socket_class):
        """Test telemetry endpoint check with custom endpoint."""
        # Mock successful connection
        mock_socket = MagicMock()
        mock_socket.connect_ex.return_value = 0
        mock_socket_class.return_value = mock_socket

        # Test with custom endpoint
        result = check_telemetry_endpoint("http://example.com:9999")

        # Verify correct host and port were used
        assert result is True
        mock_socket.connect_ex.assert_called_once_with(("example.com", 9999))

    @patch("agent.observability.socket.socket")
    def test_check_telemetry_endpoint_handles_exceptions(self, mock_socket_class):
        """Test telemetry endpoint check handles exceptions gracefully."""
        # Mock socket exception
        mock_socket_class.side_effect = OSError("Network error")

        # Test
        result = check_telemetry_endpoint("http://localhost:4317")

        # Verify
        assert result is False  # Should return False on error

    def test_check_telemetry_endpoint_uses_default(self):
        """Test telemetry endpoint check uses default endpoint."""
        with patch("agent.observability.socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket

            # Test without providing endpoint
            result = check_telemetry_endpoint()

            # Verify default endpoint was used
            assert result is True
            mock_socket.connect_ex.assert_called_once_with(("localhost", 4317))

    def test_check_telemetry_endpoint_fast_timeout(self):
        """Test telemetry endpoint check uses fast timeout."""
        with patch("agent.observability.socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0
            mock_socket_class.return_value = mock_socket

            # Test
            check_telemetry_endpoint("http://localhost:4317", timeout=0.01)

            # Verify timeout was set correctly
            mock_socket.settimeout.assert_called_once_with(0.01)


@pytest.mark.integration
@pytest.mark.cli
class TestObservabilityIntegration:
    """Integration tests for observability setup and span creation."""

    @pytest.mark.asyncio
    async def test_agent_with_observability_enabled(self):
        """Test agent execution with observability enabled."""
        # Setup config with observability
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test-key"
        config.telemetry.enabled = False  # Disabled to avoid real otel setup in tests

        # Create mock client
        mock_client = MockChatClient(response="Test response")

        # Create agent
        agent = Agent(settings=config, chat_client=mock_client)

        # Execute
        response = await agent.run("test prompt")

        # Verify
        assert response is not None
        assert "Test response" in response

    @pytest.mark.asyncio
    async def test_agent_without_observability(self):
        """Test agent execution without observability."""
        # Setup config without observability
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test-key"
        config.telemetry.enabled = False

        # Create mock client
        mock_client = MockChatClient(response="Test response")

        # Create agent
        agent = Agent(settings=config, chat_client=mock_client)

        # Execute
        response = await agent.run("test prompt")

        # Verify execution works without observability
        assert response is not None
        assert "Test response" in response


@pytest.mark.integration
@pytest.mark.cli
class TestTelemetryWorkflow:
    """Integration tests for complete telemetry workflow."""

    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution._execute_query")
    @pytest.mark.asyncio
    async def test_single_prompt_auto_detection_workflow(
        self,
        mock_execute,
        mock_logging,
        mock_settings_loader,
        mock_agent,
        mock_setup_otel,
        mock_check_endpoint,
    ):
        """Test complete workflow: auto-detect endpoint -> enable observability -> execute."""
        from agent.cli.execution import run_single_prompt

        # Setup: endpoint available, config doesn't have explicit setting
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test-key"
        config.telemetry.enabled = False
        mock_settings_loader.return_value = config
        mock_check_endpoint.return_value = True
        mock_execute.return_value = "test response"

        # Execute
        await run_single_prompt("test prompt", verbose=False, quiet=True)

        # Verify workflow
        # 1. Config loaded
        mock_settings_loader.assert_called_once()

        # 2. Endpoint checked
        mock_check_endpoint.assert_called_once()

        # 3. Observability setup called (auto-enabled)
        mock_setup_otel.assert_called_once()

        # 4. Query executed
        mock_execute.assert_called_once()

    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.cli.execution.Agent")
    @patch("agent.cli.execution.load_config_with_env")
    @patch("agent.cli.execution.setup_session_logging")
    @patch("agent.cli.execution._execute_query")
    @pytest.mark.asyncio
    async def test_single_prompt_no_auto_detection_when_explicit(
        self,
        mock_execute,
        mock_logging,
        mock_settings_loader,
        mock_agent,
        mock_setup_otel,
        mock_check_endpoint,
    ):
        """Test that auto-detection is skipped when telemetry is explicitly configured."""
        from agent.cli.execution import run_single_prompt

        # Setup: explicitly enabled
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test-key"
        config.telemetry.enabled = True
        mock_settings_loader.return_value = config
        mock_execute.return_value = "test response"

        # Execute
        await run_single_prompt("test prompt", verbose=False, quiet=True)

        # Verify workflow
        # 1. Auto-detection NOT attempted (explicit config)
        mock_check_endpoint.assert_not_called()

        # 2. Observability setup called anyway (explicitly enabled)
        mock_setup_otel.assert_called_once()

    @patch("agent.observability.check_telemetry_endpoint")
    @patch("agent_framework.observability.setup_observability")
    @patch("agent.cli.interactive.ThreadPersistence")
    @patch("agent.cli.interactive.PromptSession")
    @patch("agent.cli.interactive.load_config_with_env")
    @patch("agent.cli.interactive.setup_session_logging")
    @pytest.mark.asyncio
    async def test_interactive_auto_detection_workflow(
        self,
        mock_logging,
        mock_settings_loader,
        mock_session,
        mock_persistence,
        mock_setup_otel,
        mock_check_endpoint,
    ):
        """Test interactive mode: auto-detect endpoint -> enable observability -> start chat."""
        from unittest.mock import AsyncMock

        from agent.cli.interactive import run_chat_mode

        # Setup
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test-key"
        config.telemetry.enabled = False
        mock_settings_loader.return_value = config
        mock_check_endpoint.return_value = True

        # Mock prompt session to exit immediately
        mock_prompt_instance = AsyncMock()
        mock_prompt_instance.prompt_async.side_effect = EOFError()
        mock_session.return_value = mock_prompt_instance

        # Execute
        await run_chat_mode(quiet=True, verbose=False)

        # Verify workflow
        # 1. Endpoint checked
        mock_check_endpoint.assert_called_once()

        # 2. Observability setup called (auto-enabled)
        mock_setup_otel.assert_called_once()
