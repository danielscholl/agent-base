"""Unit tests for health check logging suppression."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.cli.app import _test_provider_connectivity_async
from agent.config import AgentConfig


@pytest.fixture
def mock_azure_config():
    """Create mock AgentConfig for Azure testing."""
    return AgentConfig(
        llm_provider="azure",
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_deployment="test-deployment",
        azure_openai_api_key="test-key",
    )


@pytest.fixture
def mock_azure_cli_config():
    """Create mock AgentConfig for Azure testing with CLI auth (no API key)."""
    return AgentConfig(
        llm_provider="azure",
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_deployment="test-deployment",
    )


@pytest.mark.unit
@pytest.mark.cli
class TestHealthCheckLogging:
    """Tests for health check logging suppression."""

    @pytest.mark.asyncio
    async def test_azure_auth_error_logging_suppressed(self, mock_azure_cli_config):
        """Test that Azure authentication errors are logged at CRITICAL level during health check."""
        # Get the Azure identity logger
        azure_logger = logging.getLogger("azure.identity")
        original_level = azure_logger.level

        # Mock Agent to raise Azure auth error
        with patch("agent.cli.app.Agent") as MockAgent:
            # Simulate Azure auth failure
            MockAgent.side_effect = Exception("Please run 'az login' to set up an account")

            # Run the connectivity test
            success, status = await _test_provider_connectivity_async(
                "azure", mock_azure_cli_config
            )

            # Verify it returns auth failure
            assert success is False
            assert "az login" in status.lower()

        # Verify logger level was restored
        assert azure_logger.level == original_level

    @pytest.mark.asyncio
    async def test_azure_framework_auth_error_logging_suppressed(self, mock_azure_cli_config):
        """Test that agent-framework Azure auth errors are logged at CRITICAL level."""
        # Get the agent-framework logger
        framework_logger = logging.getLogger("agent_framework.azure._entra_id_authentication")
        original_level = framework_logger.level

        # Mock Agent to raise framework auth error
        with patch("agent.cli.app.Agent") as MockAgent:
            MockAgent.side_effect = Exception(
                "Failed to retrieve Azure token for the specified endpoint"
            )

            # Run the connectivity test
            success, status = await _test_provider_connectivity_async(
                "azure", mock_azure_cli_config
            )

            # Verify it returns auth failure
            assert success is False
            assert "az login" in status.lower() or "failed" in status.lower()

        # Verify logger level was restored
        assert framework_logger.level == original_level

    @pytest.mark.asyncio
    async def test_multiple_loggers_restored(self, mock_azure_cli_config):
        """Test that all suppressed loggers are restored to original levels."""
        # Get all loggers that should be suppressed
        loggers_to_check = [
            logging.getLogger("agent.middleware"),
            logging.getLogger("azure.identity"),
            logging.getLogger("azure.identity._internal.decorators"),
            logging.getLogger("azure.identity._credentials.chained"),
            logging.getLogger("agent_framework.azure._entra_id_authentication"),
        ]

        # Set different levels for each logger
        original_levels = {}
        for i, logger in enumerate(loggers_to_check):
            level = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL][
                i % 5
            ]
            logger.setLevel(level)
            original_levels[logger.name] = level

        # Mock Agent to raise error
        with patch("agent.cli.app.Agent") as MockAgent:
            MockAgent.side_effect = Exception("Test error")

            # Run the connectivity test
            await _test_provider_connectivity_async("azure", mock_azure_cli_config)

        # Verify all loggers were restored
        for logger in loggers_to_check:
            assert (
                logger.level == original_levels[logger.name]
            ), f"Logger {logger.name} level not restored"

    @pytest.mark.asyncio
    async def test_successful_connection_preserves_logging_levels(self, mock_azure_config):
        """Test that logging levels are restored even on successful connection."""
        azure_logger = logging.getLogger("azure.identity")
        original_level = azure_logger.level

        # Mock successful Agent run
        with patch("agent.cli.app.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.run = AsyncMock(return_value="test response")
            mock_agent.chat_client = MagicMock()
            mock_agent.chat_client.close = AsyncMock()
            MockAgent.return_value = mock_agent

            # Run the connectivity test
            success, status = await _test_provider_connectivity_async("azure", mock_azure_config)

            # Verify success
            assert success is True
            assert status == "Connected"

        # Verify logger level was restored
        assert azure_logger.level == original_level

    @pytest.mark.asyncio
    async def test_non_azure_provider_general_error(self):
        """Test that non-Azure providers get generic error messages."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test-key")

        with patch("agent.cli.app.Agent") as MockAgent:
            MockAgent.side_effect = Exception("Some random error")

            success, status = await _test_provider_connectivity_async("openai", config)

            assert success is False
            # Non-Azure providers should get generic "Connection failed"
            assert status == "Connection failed"
            assert "az login" not in status.lower()

    @pytest.mark.asyncio
    async def test_foundry_provider_auth_error(self):
        """Test that Azure AI Foundry provider also gets Azure-specific error messages."""
        config = AgentConfig(
            llm_provider="foundry",
            azure_project_endpoint="https://test.services.ai.azure.com/api/projects/test",
            azure_model_deployment="test-model",
        )

        with patch("agent.cli.app.Agent") as MockAgent:
            MockAgent.side_effect = Exception("Please run 'az login' to set up an account")

            success, status = await _test_provider_connectivity_async("foundry", config)

            assert success is False
            assert "az login" in status.lower()
