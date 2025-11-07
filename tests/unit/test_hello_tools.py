"""Unit tests for agent.tools.hello module."""

import pytest

from agent.config import AgentConfig
from agent.tools.hello import HelloTools


@pytest.fixture
def mock_config():
    """Create mock AgentConfig for testing."""
    return AgentConfig(llm_provider="openai", openai_api_key="test-key")


@pytest.fixture
def hello_tools(mock_config):
    """Create HelloTools instance for testing."""
    return HelloTools(mock_config)


class TestHelloTools:
    """Tests for HelloTools class."""

    def test_initialization(self, mock_config):
        """Test HelloTools initializes with config."""
        tools = HelloTools(mock_config)

        assert tools.config == mock_config

    def test_get_tools_returns_two_functions(self, hello_tools):
        """Test get_tools returns both tool functions."""
        tools_list = hello_tools.get_tools()

        assert len(tools_list) == 2
        assert hello_tools.hello_world in tools_list
        assert hello_tools.greet_user in tools_list

    @pytest.mark.asyncio
    async def test_hello_world_default_name(self, hello_tools):
        """Test hello_world with default name 'World'."""
        result = await hello_tools.hello_world()

        assert result["success"] is True
        assert result["result"] == "Hello, World!"
        assert result["message"] == "Greeted World"

    @pytest.mark.asyncio
    async def test_hello_world_custom_name(self, hello_tools):
        """Test hello_world with custom name."""
        result = await hello_tools.hello_world("Alice")

        assert result["success"] is True
        assert result["result"] == "Hello, Alice!"
        assert result["message"] == "Greeted Alice"

    @pytest.mark.asyncio
    async def test_hello_world_empty_string(self, hello_tools):
        """Test hello_world with empty string name."""
        result = await hello_tools.hello_world("")

        assert result["success"] is True
        assert result["result"] == "Hello, !"
        assert result["message"] == "Greeted "

    @pytest.mark.asyncio
    async def test_greet_user_english_default(self, hello_tools):
        """Test greet_user defaults to English."""
        result = await hello_tools.greet_user("Bob")

        assert result["success"] is True
        assert result["result"] == "Hello, Bob!"
        assert result["message"] == "Greeted Bob in en"

    @pytest.mark.asyncio
    async def test_greet_user_english_explicit(self, hello_tools):
        """Test greet_user with explicit English."""
        result = await hello_tools.greet_user("Bob", "en")

        assert result["success"] is True
        assert result["result"] == "Hello, Bob!"
        assert result["message"] == "Greeted Bob in en"

    @pytest.mark.asyncio
    async def test_greet_user_spanish(self, hello_tools):
        """Test greet_user in Spanish."""
        result = await hello_tools.greet_user("Carlos", "es")

        assert result["success"] is True
        assert result["result"] == "¡Hola, Carlos!"
        assert result["message"] == "Greeted Carlos in es"

    @pytest.mark.asyncio
    async def test_greet_user_french(self, hello_tools):
        """Test greet_user in French."""
        result = await hello_tools.greet_user("Marie", "fr")

        assert result["success"] is True
        assert result["result"] == "Bonjour, Marie!"
        assert result["message"] == "Greeted Marie in fr"

    @pytest.mark.asyncio
    async def test_greet_user_unsupported_language(self, hello_tools):
        """Test greet_user with unsupported language returns error."""
        result = await hello_tools.greet_user("Hans", "de")

        assert result["success"] is False
        assert result["error"] == "unsupported_language"
        assert "de" in result["message"]
        assert "en, es, fr" in result["message"]

    @pytest.mark.asyncio
    async def test_greet_user_invalid_language_code(self, hello_tools):
        """Test greet_user with invalid language code."""
        result = await hello_tools.greet_user("Alice", "invalid")

        assert result["success"] is False
        assert result["error"] == "unsupported_language"
        assert "invalid" in result["message"]

    @pytest.mark.asyncio
    async def test_greet_user_empty_name_english(self, hello_tools):
        """Test greet_user with empty name in English."""
        result = await hello_tools.greet_user("", "en")

        assert result["success"] is True
        assert result["result"] == "Hello, !"

    @pytest.mark.asyncio
    async def test_greet_user_empty_name_spanish(self, hello_tools):
        """Test greet_user with empty name in Spanish."""
        result = await hello_tools.greet_user("", "es")

        assert result["success"] is True
        assert result["result"] == "¡Hola, !"

    @pytest.mark.asyncio
    async def test_greet_user_empty_name_french(self, hello_tools):
        """Test greet_user with empty name in French."""
        result = await hello_tools.greet_user("", "fr")

        assert result["success"] is True
        assert result["result"] == "Bonjour, !"

    def test_hello_tools_has_correct_docstrings(self, hello_tools):
        """Test tool functions have docstrings for LLM."""
        assert hello_tools.hello_world.__doc__ is not None
        assert "Say hello" in hello_tools.hello_world.__doc__

        assert hello_tools.greet_user.__doc__ is not None
        assert "different languages" in hello_tools.greet_user.__doc__

    def test_response_format_consistency(self, hello_tools):
        """Test all responses follow consistent format."""
        # Success responses have: success, result, message
        success = hello_tools._create_success_response("test", "msg")
        assert "success" in success
        assert "result" in success
        assert "message" in success
        assert success["success"] is True

        # Error responses have: success, error, message
        error = hello_tools._create_error_response("code", "msg")
        assert "success" in error
        assert "error" in error
        assert "message" in error
        assert error["success"] is False
