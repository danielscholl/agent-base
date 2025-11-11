"""Unit tests for Gemini chat client."""

from unittest.mock import MagicMock, patch

import pytest
from agent_framework import ChatMessage, FunctionCallContent, Role, TextContent

from agent.providers.gemini import GeminiChatClient
from agent.providers.gemini.types import (
    _convert_parameters,
    extract_usage_metadata,
    from_gemini_message,
    to_gemini_message,
)

# Import fixtures from conftest
pytest_plugins = ["tests.fixtures.gemini"]


@pytest.mark.unit
@pytest.mark.providers
class TestGeminiChatClientInitialization:
    """Test GeminiChatClient initialization."""

    @patch("agent.providers.gemini.chat_client.genai.Client")
    def test_initialization_with_api_key(self, mock_client_class, gemini_api_key, gemini_model):
        """Test client initializes with API key."""
        client = GeminiChatClient(
            model_id=gemini_model,
            api_key=gemini_api_key,
        )

        assert client.model_id == gemini_model
        assert client.use_vertexai is False
        mock_client_class.assert_called_once_with(api_key=gemini_api_key)

    @patch("agent.providers.gemini.chat_client.genai.Client")
    def test_initialization_with_vertex_ai(
        self, mock_client_class, gemini_model, gemini_project_id, gemini_location
    ):
        """Test client initializes with Vertex AI credentials."""
        client = GeminiChatClient(
            model_id=gemini_model,
            project_id=gemini_project_id,
            location=gemini_location,
            use_vertexai=True,
        )

        assert client.model_id == gemini_model
        assert client.use_vertexai is True
        mock_client_class.assert_called_once_with(
            vertexai=True, project=gemini_project_id, location=gemini_location
        )

    def test_initialization_without_api_key_fails(self, gemini_model):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError, match="API key authentication requires api_key"):
            GeminiChatClient(model_id=gemini_model)

    def test_initialization_vertex_ai_without_project_fails(self, gemini_model):
        """Test Vertex AI initialization fails without project ID."""
        with pytest.raises(ValueError, match="requires both project_id and location"):
            GeminiChatClient(model_id=gemini_model, location="us-central1", use_vertexai=True)

    def test_initialization_vertex_ai_without_location_fails(self, gemini_model, gemini_project_id):
        """Test Vertex AI initialization fails without location."""
        with pytest.raises(ValueError, match="requires both project_id and location"):
            GeminiChatClient(model_id=gemini_model, project_id=gemini_project_id, use_vertexai=True)


@pytest.mark.unit
@pytest.mark.providers
class TestMessageConversion:
    """Test message conversion utilities."""

    def test_to_gemini_message_with_text_content(self):
        """Test converting ChatMessage with TextContent."""
        message = ChatMessage(role="user", contents=[TextContent(text="Hello")])

        result = to_gemini_message(message)

        assert result["role"] == "user"
        assert len(result["parts"]) == 1
        assert result["parts"][0] == {"text": "Hello"}

    def test_to_gemini_message_assistant_to_model_role(self):
        """Test assistant role maps to model role."""
        message = ChatMessage(role=Role.ASSISTANT, contents=[TextContent(text="Hi")])

        # Note: function calls should only appear in model turns, so we need call_id_to_name mapping
        result = to_gemini_message(message, call_id_to_name={})

        assert result["role"] == "model"

    def test_to_gemini_message_with_function_call(self):
        """Test converting ChatMessage with function call."""
        message = ChatMessage(
            role=Role.ASSISTANT,
            contents=[
                FunctionCallContent(
                    call_id="call_123", name="test_func", arguments={"arg": "value"}
                )
            ],
        )

        result = to_gemini_message(message, call_id_to_name={"call_123": "test_func"})

        assert result["role"] == "model"
        assert len(result["parts"]) == 1
        assert result["parts"][0] == {
            "function_call": {"name": "test_func", "args": {"arg": "value"}}
        }

    def test_to_gemini_message_empty_contents(self):
        """Test converting message with no contents."""
        message = ChatMessage(role="user", contents=[])

        result = to_gemini_message(message)

        # Should have at least one part (empty text)
        assert len(result["parts"]) >= 1

    def test_to_gemini_message_tool_result_in_user_turn(self):
        """Function results are emitted only in user/tool turns with resolved name."""
        from agent_framework import FunctionResultContent

        # Simulate a tool message with a function result
        msg = ChatMessage(
            role=Role.TOOL,
            contents=[FunctionResultContent(call_id="call_42", result={"ok": True})],
        )

        # Provide mapping so the function_response gets a name
        converted = to_gemini_message(msg, call_id_to_name={"call_42": "do_thing"})

        assert converted["role"] == "user"
        assert any(
            "function_response" in p and p["function_response"]["name"] == "do_thing"
            for p in converted["parts"]
        )

    def test_from_gemini_message_with_text(self):
        """Test converting Gemini response with text."""
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_content = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Hello from Gemini"
        mock_part.function_call = None
        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        result = from_gemini_message(mock_response)

        assert result.role == Role.ASSISTANT
        assert len(result.contents) == 1
        assert isinstance(result.contents[0], TextContent)
        assert result.contents[0].text == "Hello from Gemini"

    def test_from_gemini_message_with_function_call(self):
        """Test converting Gemini response with function call."""
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_content = MagicMock()
        mock_part = MagicMock()
        mock_part.text = None
        mock_fc = MagicMock()
        mock_fc.name = "test_function"
        mock_fc.args = {"param": "value"}
        mock_part.function_call = mock_fc
        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        result = from_gemini_message(mock_response)

        assert result.role == Role.ASSISTANT
        assert len(result.contents) == 1
        assert isinstance(result.contents[0], FunctionCallContent)
        assert result.contents[0].name == "test_function"
        assert result.contents[0].arguments == {"param": "value"}


@pytest.mark.unit
@pytest.mark.providers
class TestToolConversion:
    """Test tool conversion utilities."""

    def test_convert_parameters_with_properties(self):
        """Test parameter conversion with properties."""
        params = {
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        result = _convert_parameters(params)

        assert result["type"] == "object"
        assert result["properties"] == {"name": {"type": "string"}}
        assert result["required"] == ["name"]

    def test_convert_parameters_empty(self):
        """Test parameter conversion with empty schema."""
        params = {}

        result = _convert_parameters(params)

        assert result["type"] == "object"
        assert "properties" in result


@pytest.mark.unit
@pytest.mark.providers
class TestUsageExtraction:
    """Test usage metadata extraction."""

    def test_extract_usage_metadata(self):
        """Test extracting usage from Gemini response."""
        mock_response = MagicMock()
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 5
        mock_usage.total_token_count = 15
        mock_response.usage_metadata = mock_usage

        result = extract_usage_metadata(mock_response)

        assert result["prompt_tokens"] == 10
        assert result["completion_tokens"] == 5
        assert result["total_tokens"] == 15

    def test_extract_usage_metadata_missing(self):
        """Test extracting usage when metadata is missing."""
        mock_response = MagicMock()
        del mock_response.usage_metadata

        result = extract_usage_metadata(mock_response)

        assert result == {}


@pytest.mark.unit
@pytest.mark.providers
class TestGeminiChatClientResponse:
    """Test GeminiChatClient response handling."""

    @pytest.mark.asyncio
    @patch("agent.providers.gemini.chat_client.genai.Client")
    async def test_inner_get_response(self, mock_client_class, gemini_api_key, gemini_model):
        """Test _inner_get_response with mocked Gemini API."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Setup mock response
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_content = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "Test response"
        mock_part.function_call = None
        mock_content.parts = [mock_part]
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]
        mock_response.usage_metadata = None

        mock_client.models.generate_content.return_value = mock_response

        # Create client and test
        client = GeminiChatClient(model_id=gemini_model, api_key=gemini_api_key)
        message = ChatMessage(role="user", contents=[TextContent(text="Test")])

        response = await client._inner_get_response(messages=[message], chat_options=MagicMock())

        assert response is not None
        assert len(response.messages) == 1
        assert response.messages[0].role == Role.ASSISTANT
        mock_client.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    @patch("agent.providers.gemini.chat_client.genai.Client")
    async def test_inner_get_response_with_error(
        self, mock_client_class, gemini_api_key, gemini_model
    ):
        """Test _inner_get_response handles errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("API Error")

        client = GeminiChatClient(model_id=gemini_model, api_key=gemini_api_key)
        message = ChatMessage(role="user", contents=[TextContent(text="Test")])

        with pytest.raises(Exception, match="API Error"):
            await client._inner_get_response(messages=[message], chat_options=MagicMock())


@pytest.mark.unit
@pytest.mark.providers
class TestGeminiChatClientStreaming:
    """Test GeminiChatClient streaming."""

    @pytest.mark.asyncio
    @patch("agent.providers.gemini.chat_client.genai.Client")
    async def test_inner_get_streaming_response(
        self, mock_client_class, gemini_api_key, gemini_model
    ):
        """Test _inner_get_streaming_response with mocked stream."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create mock stream chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "world"

        mock_client.models.generate_content_stream.return_value = iter([mock_chunk1, mock_chunk2])

        client = GeminiChatClient(model_id=gemini_model, api_key=gemini_api_key)
        message = ChatMessage(role="user", contents=[TextContent(text="Test")])

        chunks = []
        async for update in client._inner_get_streaming_response(
            messages=[message], chat_options=MagicMock()
        ):
            chunks.append(update)

        assert len(chunks) == 2
        # ChatResponseUpdate has 'text' attribute
        assert chunks[0].text == "Hello "
        assert chunks[1].text == "world"


@pytest.mark.unit
@pytest.mark.providers
class TestGeminiOptionsMapping:
    """Tests around translating ChatOptions to Gemini config (tools and sampling)."""

    @patch("agent.providers.gemini.chat_client.genai.Client")
    def test_prepare_options_includes_tools_and_sampling(
        self, mock_client_class, gemini_api_key, gemini_model
    ):
        from agent_framework import ChatOptions, ai_function

        # Define a simple ai function tool
        @ai_function
        async def do_thing(name: str) -> dict:
            return {"done": True}

        client = GeminiChatClient(model_id=gemini_model, api_key=gemini_api_key)
        chat_options = ChatOptions(temperature=0.3, top_p=0.8, max_tokens=50, tools=[do_thing])

        # Single user message
        message = ChatMessage(role="user", contents=[TextContent(text="Hi")])

        config = client._prepare_options([message], chat_options)

        assert config["temperature"] == 0.3
        assert config["top_p"] == 0.8
        assert config["max_output_tokens"] == 50
        assert "tools" in config
        # tools should be in Gemini "function_declarations" format
        tools = config["tools"]
        assert isinstance(tools, list) and tools
        assert "function_declarations" in tools[0]
