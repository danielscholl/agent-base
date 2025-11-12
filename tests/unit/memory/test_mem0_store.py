"""Unit tests for Mem0Store class."""

from unittest.mock import Mock, patch

import pytest

from agent.config import AgentConfig
from agent.memory.mem0_store import Mem0Store


@pytest.fixture
def mem0_config():
    """Create test configuration for mem0."""
    return AgentConfig(
        llm_provider="openai",
        openai_api_key="test",
        memory_type="mem0",
        mem0_host="http://localhost:8000",
        mem0_user_id="test-user",
        mem0_project_id="test-project",
    )


@pytest.fixture
def mem0_store(mem0_config):
    """Create Mem0Store instance with mocked client."""
    with patch("agent.memory.mem0_store.get_mem0_client") as mock_get_client:
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        store = Mem0Store(mem0_config)
        store.client = mock_client  # Ensure we have access to mock

        yield store


@pytest.mark.unit
@pytest.mark.memory
class TestMem0Store:
    """Tests for Mem0Store class."""

    def test_initialization(self, mem0_config):
        """Test Mem0Store initializes with config."""
        with patch("agent.memory.mem0_store.get_mem0_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            store = Mem0Store(mem0_config)

            assert store.config == mem0_config
            assert store.user_id == "test-user"
            assert store.namespace == "test-user:test-project"
            mock_get_client.assert_called_once_with(mem0_config)

    def test_initialization_without_project_id(self):
        """Test namespace without project_id."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_host="http://localhost:8000",
            mem0_user_id="alice",
        )

        with patch("agent.memory.mem0_store.get_mem0_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            store = Mem0Store(config)

            assert store.namespace == "alice"  # No project suffix

    @pytest.mark.asyncio
    async def test_add_messages_success(self, mem0_store):
        """Test adding messages to mem0 store."""
        mem0_store.client.add.return_value = {"id": "mem-123"}

        messages = [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Nice to meet you, Alice!"}
        ]

        result = await mem0_store.add(messages)

        assert result["success"] is True
        assert len(result["result"]) == 2
        assert "mem-123" in result["result"]
        assert mem0_store.client.add.call_count == 2

    @pytest.mark.asyncio
    async def test_add_filters_system_messages(self, mem0_store):
        """Test that system messages are filtered out."""
        mem0_store.client.add.return_value = {"id": "mem-123"}

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "System message"},
            {"role": "tool", "content": "Tool output"},
        ]

        result = await mem0_store.add(messages)

        assert result["success"] is True
        # Only user message should be added
        assert mem0_store.client.add.call_count == 1

    @pytest.mark.asyncio
    async def test_add_respects_save_false_metadata(self, mem0_store):
        """Test that messages with save=false are not stored."""
        messages = [
            {"role": "user", "content": "Save this", "metadata": {}},
            {"role": "user", "content": "Don't save this", "metadata": {"save": False}},
        ]

        mem0_store.client.add.return_value = {"id": "mem-123"}

        result = await mem0_store.add(messages)

        assert result["success"] is True
        # Only one message should be added
        assert mem0_store.client.add.call_count == 1

    @pytest.mark.asyncio
    async def test_add_force_save_overrides_filters(self, mem0_store):
        """Test that force_save=true overrides default filters."""
        messages = [
            {"role": "system", "content": "System message", "metadata": {"force_save": True}},
        ]

        mem0_store.client.add.return_value = {"id": "mem-123"}

        result = await mem0_store.add(messages)

        assert result["success"] is True
        # System message should be saved due to force_save
        assert mem0_store.client.add.call_count == 1

    @pytest.mark.asyncio
    async def test_add_uses_namespace(self, mem0_store):
        """Test that add uses correct namespace for isolation."""
        mem0_store.client.add.return_value = {"id": "mem-123"}

        messages = [{"role": "user", "content": "Test"}]
        await mem0_store.add(messages)

        # Verify namespace is used in add call
        mem0_store.client.add.assert_called_with(
            messages="Test",
            user_id="test-user:test-project"
        )

    @pytest.mark.asyncio
    async def test_add_empty_messages_returns_error(self, mem0_store):
        """Test adding empty message list returns error."""
        result = await mem0_store.add([])

        assert result["success"] is False
        assert result["error"] == "invalid_input"

    @pytest.mark.asyncio
    async def test_add_handles_client_error(self, mem0_store):
        """Test add handles individual message errors gracefully."""
        mem0_store.client.add.side_effect = Exception("Connection failed")

        messages = [{"role": "user", "content": "Test"}]
        result = await mem0_store.add(messages)

        # Should succeed with 0 messages added (resilient to individual failures)
        assert result["success"] is True
        assert len(result["result"]) == 0
        assert "Added 0 messages" in result["message"]

    @pytest.mark.asyncio
    async def test_search_by_semantic_query(self, mem0_store):
        """Test searching memories by semantic similarity."""
        mem0_store.client.search.return_value = [
            {
                "id": "mem-123",
                "memory": "User authentication failed",
                "score": 0.95,
                "created_at": "2025-01-01T00:00:00Z",
                "metadata": {}
            }
        ]

        result = await mem0_store.search("login errors", limit=5)

        assert result["success"] is True
        assert len(result["result"]) == 1
        assert result["result"][0]["content"] == "User authentication failed"
        assert result["result"][0]["score"] == 0.95

        mem0_store.client.search.assert_called_once_with(
            query="login errors",
            filters={"user_id": "test-user:test-project"},
            limit=5
        )

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_error(self, mem0_store):
        """Test search with empty query returns error."""
        result = await mem0_store.search("", limit=5)

        assert result["success"] is False
        assert result["error"] == "invalid_query"

    @pytest.mark.asyncio
    async def test_search_handles_client_error(self, mem0_store):
        """Test search handles client errors gracefully."""
        mem0_store.client.search.side_effect = Exception("Search failed")

        result = await mem0_store.search("test query")

        assert result["success"] is False
        assert "search_error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_all_returns_all_memories(self, mem0_store):
        """Test get_all returns all stored memories."""
        mem0_store.client.get_all.return_value = [
            {"id": "mem-1", "memory": "First memory", "created_at": "2025-01-01", "metadata": {}},
            {"id": "mem-2", "memory": "Second memory", "created_at": "2025-01-02", "metadata": {}}
        ]

        result = await mem0_store.get_all()

        assert result["success"] is True
        assert len(result["result"]) == 2
        mem0_store.client.get_all.assert_called_once_with(user_id="test-user:test-project")

    @pytest.mark.asyncio
    async def test_get_recent_returns_sorted_memories(self, mem0_store):
        """Test get_recent returns most recent memories."""
        mem0_store.client.get_all.return_value = [
            {"id": "mem-1", "memory": "Oldest", "created_at": "2025-01-01", "metadata": {}},
            {"id": "mem-2", "memory": "Newest", "created_at": "2025-01-03", "metadata": {}},
            {"id": "mem-3", "memory": "Middle", "created_at": "2025-01-02", "metadata": {}}
        ]

        result = await mem0_store.get_recent(limit=2)

        assert result["success"] is True
        assert len(result["result"]) == 2
        # Should be sorted by timestamp, most recent first
        assert result["result"][0]["content"] == "Newest"
        assert result["result"][1]["content"] == "Middle"

    @pytest.mark.asyncio
    async def test_clear_removes_all_memories(self, mem0_store):
        """Test clear removes all memories from storage."""
        mem0_store.client.delete_all.return_value = None

        result = await mem0_store.clear()

        assert result["success"] is True
        assert "Cleared all memories" in result["message"]
        mem0_store.client.delete_all.assert_called_once_with(user_id="test-user:test-project")

    @pytest.mark.asyncio
    async def test_clear_handles_error(self, mem0_store):
        """Test clear handles errors gracefully."""
        mem0_store.client.delete_all.side_effect = Exception("Delete failed")

        result = await mem0_store.clear()

        assert result["success"] is False
        assert "clear_error" in result["error"]

    @pytest.mark.asyncio
    async def test_retrieve_for_context_uses_semantic_search(self, mem0_store):
        """Test retrieve_for_context uses semantic search."""
        mem0_store.client.search.return_value = [
            {"id": "mem-1", "memory": "Relevant memory", "score": 0.9, "created_at": "2025-01-01", "metadata": {}}
        ]

        messages = [
            {"role": "user", "content": "What is my name?"}
        ]

        result = await mem0_store.retrieve_for_context(messages, limit=5)

        assert result["success"] is True
        # Should have called search with the user's query
        mem0_store.client.search.assert_called_once()
        call_args = mem0_store.client.search.call_args
        assert "What is my name?" in call_args.kwargs["query"]

    @pytest.mark.asyncio
    async def test_retrieve_for_context_falls_back_to_recent(self, mem0_store):
        """Test retrieve_for_context falls back to recent when no query."""
        mem0_store.client.get_all.return_value = [
            {"id": "mem-1", "memory": "Recent memory", "created_at": "2025-01-01", "metadata": {}}
        ]

        messages = []  # No messages to extract query from

        result = await mem0_store.retrieve_for_context(messages, limit=5)

        assert result["success"] is True
        # Should have called get_all (for get_recent)
        mem0_store.client.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that different namespaces don't interfere."""
        config1 = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_host="http://localhost:8000",
            mem0_user_id="alice",
        )

        config2 = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_host="http://localhost:8000",
            mem0_user_id="bob",
        )

        with patch("agent.memory.mem0_store.get_mem0_client") as mock_get_client:
            mock_client1 = Mock()
            mock_client2 = Mock()
            mock_get_client.side_effect = [mock_client1, mock_client2]

            store1 = Mem0Store(config1)
            store2 = Mem0Store(config2)

            assert store1.namespace == "alice"
            assert store2.namespace == "bob"
            assert store1.namespace != store2.namespace
