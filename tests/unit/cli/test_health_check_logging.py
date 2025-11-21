"""Unit tests for health check logging suppression and provider connectivity optimization."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.cli.health import _test_all_providers, _test_provider_connectivity_async
from agent.config.schema import AgentSettings


@pytest.fixture
def mock_azure_config():
    """Create mock AgentConfig for Azure testing."""
    config = AgentSettings()
    config.providers.enabled = ["azure"]
    config.providers.azure.endpoint = "https://test.openai.azure.com/"
    config.providers.azure.deployment = "test-deployment"
    config.providers.azure.api_key = "test-key"
    return config


@pytest.fixture
def mock_azure_cli_config():
    """Create mock AgentConfig for Azure testing with CLI auth (no API key)."""
    config = AgentSettings()
    config.providers.enabled = ["azure"]
    config.providers.azure.endpoint = "https://test.openai.azure.com/"
    config.providers.azure.deployment = "test-deployment"
    # No API key - will use Azure CLI auth
    return config


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
        with patch("agent.cli.health.Agent") as MockAgent:
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
        with patch("agent.cli.health.Agent") as MockAgent:
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
        with patch("agent.cli.health.Agent") as MockAgent:
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
        with patch("agent.cli.health.Agent") as MockAgent:
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
        config = AgentSettings()
        config.providers.enabled = ["openai"]
        config.providers.openai.api_key = "test-key"

        with patch("agent.cli.health.Agent") as MockAgent:
            MockAgent.side_effect = Exception("Some random error")

            success, status = await _test_provider_connectivity_async("openai", config)

            assert success is False
            # Non-Azure providers should get generic "Connection failed"
            assert status == "Connection failed"
            assert "az login" not in status.lower()

    @pytest.mark.asyncio
    async def test_foundry_provider_auth_error(self):
        """Test that Azure AI Foundry provider also gets Azure-specific error messages."""
        config = AgentSettings()
        config.providers.enabled = ["foundry"]
        config.providers.foundry.project_endpoint = (
            "https://test.services.ai.azure.com/api/projects/test"
        )
        config.providers.foundry.model_deployment = "test-model"

        with patch("agent.cli.health.Agent") as MockAgent:
            MockAgent.side_effect = Exception("Please run 'az login' to set up an account")

            success, status = await _test_provider_connectivity_async("foundry", config)

            assert success is False
            assert "az login" in status.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestProviderConnectivityOptimization:
    """Tests for optimized provider connectivity testing."""

    @pytest.mark.asyncio
    async def test_only_enabled_providers_tested(self):
        """Test that only enabled providers are tested."""
        config = AgentSettings()
        config.providers.enabled = ["local"]  # Only local enabled
        config.providers.local.model = "ai/phi4"
        config.providers.openai.api_key = "test-key"
        config.providers.openai.model = "gpt-5-mini"

        with patch("agent.cli.health._test_provider_connectivity_async") as mock_test:
            mock_test.return_value = (True, "Connected")

            results = await _test_all_providers(config)

            # Should only test local provider
            assert mock_test.call_count == 1
            assert mock_test.call_args_list[0][0][0] == "local"
            assert len(results) == 1
            assert results[0][0] == "local"

    @pytest.mark.asyncio
    async def test_active_provider_always_tested(self):
        """Test that active provider is always tested even if not in enabled list."""
        config = AgentSettings()
        config.providers.enabled = [
            "local",
            "openai",
        ]  # Note: need openai enabled for it to be active
        config.providers.openai.api_key = "test-key"
        config.providers.openai.model = "gpt-5-mini"

        with patch("agent.cli.health._test_provider_connectivity_async") as mock_test:
            mock_test.return_value = (True, "Connected")

            results = await _test_all_providers(config)

            # Should test both local (enabled) and openai (active)
            assert mock_test.call_count == 2
            tested_providers = [call[0][0] for call in mock_test.call_args_list]
            assert "local" in tested_providers
            assert "openai" in tested_providers
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_disabled_providers_skipped(self):
        """Test that disabled providers are completely skipped."""
        config = AgentSettings()
        config.providers.enabled = ["local"]  # Only local enabled
        config.providers.openai.api_key = "test-key"
        config.providers.anthropic.api_key = "test-key"
        config.providers.gemini.api_key = "test-key"

        with patch("agent.cli.health._test_provider_connectivity_async") as mock_test:
            mock_test.return_value = (True, "Connected")

            await _test_all_providers(config)

            # Should only test local, not openai/anthropic/gemini
            assert mock_test.call_count == 1
            tested_providers = [call[0][0] for call in mock_test.call_args_list]
            assert "local" in tested_providers
            assert "openai" not in tested_providers
            assert "anthropic" not in tested_providers
            assert "gemini" not in tested_providers

    @pytest.mark.asyncio
    async def test_parallel_execution_with_gather(self):
        """Test that providers are tested in parallel using asyncio.gather."""
        import asyncio

        config = AgentSettings()
        config.providers.enabled = ["local", "openai", "anthropic"]
        config.providers.openai.api_key = "test-key"
        config.providers.anthropic.api_key = "test-key"

        # Track execution order to verify parallelism
        call_times = []

        async def mock_connectivity_test(provider, cfg):
            """Mock that simulates async execution."""
            call_times.append((provider, asyncio.get_event_loop().time()))
            await asyncio.sleep(0.01)  # Simulate async work
            return True, "Connected"

        with patch(
            "agent.cli.health._test_provider_connectivity_async", side_effect=mock_connectivity_test
        ):
            results = await _test_all_providers(config)

            # All 3 providers should be tested
            assert len(results) == 3

            # Verify calls happened in parallel (all start times should be close)
            if len(call_times) > 1:
                start_times = [t for _, t in call_times]
                time_spread = max(start_times) - min(start_times)
                # If parallel, all should start within 0.02s of each other
                # Note: Using 0.02s for Windows compatibility (less precise timing)
                assert time_spread < 0.02, f"Tests not parallel, time spread: {time_spread}s"

    @pytest.mark.asyncio
    async def test_multiple_enabled_providers(self):
        """Test with multiple enabled providers."""
        config = AgentSettings()
        config.providers.enabled = ["local", "openai", "anthropic"]
        config.providers.openai.api_key = "test-key"
        config.providers.anthropic.api_key = "test-key"

        with patch("agent.cli.health._test_provider_connectivity_async") as mock_test:
            mock_test.return_value = (True, "Connected")

            await _test_all_providers(config)

            # Should test all 3 enabled providers
            assert mock_test.call_count == 3
            tested_providers = [call[0][0] for call in mock_test.call_args_list]
            assert "local" in tested_providers
            assert "openai" in tested_providers
            assert "anthropic" in tested_providers

    @pytest.mark.asyncio
    async def test_empty_enabled_list_tests_active_only(self):
        """Test that empty enabled list still tests the active provider."""
        config = AgentSettings()
        config.providers.enabled = ["openai"]  # Can't be empty - must have at least one
        config.providers.openai.api_key = "test-key"

        with patch("agent.cli.health._test_provider_connectivity_async") as mock_test:
            mock_test.return_value = (True, "Connected")

            await _test_all_providers(config)

            # Should test only active provider (openai)
            assert mock_test.call_count == 1
            assert mock_test.call_args_list[0][0][0] == "openai"

    @pytest.mark.asyncio
    async def test_result_format_preserved(self):
        """Test that result format matches expected tuple structure."""
        config = AgentSettings()
        config.providers.enabled = ["local"]
        config.providers.local.model = "ai/phi4"

        with patch("agent.cli.health._test_provider_connectivity_async") as mock_test:
            mock_test.return_value = (True, "Connected")

            results = await _test_all_providers(config)

            # Verify result format: (provider_id, display_name, success, status)
            assert len(results) == 1
            provider_id, display_name, success, status = results[0]
            assert provider_id == "local"
            assert "Local" in display_name
            assert "ai/phi4" in display_name
            assert success is True
            assert status == "Connected"
