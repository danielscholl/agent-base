"""Unit tests for mem0 utility functions."""

from unittest.mock import Mock, patch

import pytest

from agent.config import AgentConfig
from agent.memory.mem0_utils import check_mem0_endpoint, get_mem0_client


@pytest.mark.unit
@pytest.mark.memory
class TestMem0Utils:
    """Tests for mem0 utility functions."""

    def test_check_mem0_endpoint_success(self):
        """Test endpoint check succeeds when connection is successful."""
        with patch("socket.socket") as mock_socket:
            # Mock successful connection (return code 0)
            mock_instance = Mock()
            mock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_instance

            result = check_mem0_endpoint("http://localhost:8000")

            assert result is True
            mock_instance.connect_ex.assert_called_once_with(("localhost", 8000))
            mock_instance.close.assert_called_once()

    def test_check_mem0_endpoint_failure(self):
        """Test endpoint check fails when connection fails."""
        with patch("socket.socket") as mock_socket:
            # Mock failed connection (non-zero return code)
            mock_instance = Mock()
            mock_instance.connect_ex.return_value = 1
            mock_socket.return_value = mock_instance

            result = check_mem0_endpoint("http://localhost:8000")

            assert result is False

    def test_check_mem0_endpoint_default_url(self):
        """Test endpoint check uses default URL when none provided."""
        with patch("socket.socket") as mock_socket:
            mock_instance = Mock()
            mock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_instance

            result = check_mem0_endpoint()

            assert result is True
            # Should default to localhost:8000
            mock_instance.connect_ex.assert_called_once_with(("localhost", 8000))

    def test_check_mem0_endpoint_custom_port(self):
        """Test endpoint check with custom port."""
        with patch("socket.socket") as mock_socket:
            mock_instance = Mock()
            mock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_instance

            result = check_mem0_endpoint("http://localhost:9000")

            assert result is True
            mock_instance.connect_ex.assert_called_once_with(("localhost", 9000))

    def test_check_mem0_endpoint_handles_exception(self):
        """Test endpoint check handles exceptions gracefully."""
        with patch("socket.socket") as mock_socket:
            mock_socket.side_effect = Exception("Connection error")

            result = check_mem0_endpoint("http://localhost:8000")

            # Should return False on exception, not raise
            assert result is False

    def test_get_mem0_client_self_hosted(self):
        """Test get_mem0_client creates self-hosted client."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_host="http://localhost:8000",
        )

        # Patch the import inside the function
        with patch("mem0.MemoryClient") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            client = get_mem0_client(config)

            assert client == mock_instance
            mock_client.assert_called_once_with(host="http://localhost:8000")

    def test_get_mem0_client_cloud(self):
        """Test get_mem0_client creates cloud client."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_api_key="test-key",
            mem0_org_id="test-org",
        )

        # Patch the import inside the function
        with patch("mem0.MemoryClient") as mock_client:
            mock_instance = Mock()
            mock_client.return_value = mock_instance

            client = get_mem0_client(config)

            assert client == mock_instance
            mock_client.assert_called_once_with(
                api_key="test-key",
                org_id="test-org"
            )

    def test_get_mem0_client_missing_config_raises(self):
        """Test get_mem0_client raises when config is incomplete."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            # No mem0_host or (mem0_api_key + mem0_org_id)
        )

        with pytest.raises(ValueError, match="Invalid mem0 configuration"):
            get_mem0_client(config)

    def test_get_mem0_client_missing_import_raises(self):
        """Test get_mem0_client raises clear error when mem0 not installed."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_host="http://localhost:8000",
        )

        # Mock ImportError when trying to import mem0
        with patch("builtins.__import__", side_effect=ImportError("No module named 'mem0'")):
            with pytest.raises(ImportError, match="mem0ai package not installed"):
                get_mem0_client(config)

    def test_get_mem0_client_self_hosted_failure(self):
        """Test get_mem0_client handles self-hosted client initialization failure."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_host="http://localhost:8000",
        )

        with patch("mem0.MemoryClient") as mock_client:
            mock_client.side_effect = Exception("Connection failed")

            with pytest.raises(ValueError, match="Failed to initialize mem0 self-hosted client"):
                get_mem0_client(config)

    def test_get_mem0_client_cloud_failure(self):
        """Test get_mem0_client handles cloud client initialization failure."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_api_key="test-key",
            mem0_org_id="test-org",
        )

        with patch("mem0.MemoryClient") as mock_client:
            mock_client.side_effect = Exception("Auth failed")

            with pytest.raises(ValueError, match="Failed to initialize mem0 cloud client"):
                get_mem0_client(config)
