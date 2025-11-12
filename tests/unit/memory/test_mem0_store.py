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
        openai_api_key="sk-test",
        memory_type="mem0",
        mem0_user_id="test-user",
        mem0_project_id="test-project",
    )


@pytest.fixture
def mem0_store(mem0_config):
    """Create Mem0Store instance with mocked memory."""
    with patch("agent.memory.mem0_store.create_memory_instance") as mock_create:
        mock_memory = Mock()
        mock_create.return_value = mock_memory

        store = Mem0Store(mem0_config)
        store.memory = mock_memory  # Ensure we have access to mock

        yield store


@pytest.mark.unit
@pytest.mark.memory
class TestMem0Store:
    """Tests for Mem0Store class."""

    def test_initialization(self, mem0_config):
        """Test Mem0Store initializes with config."""
        with patch("agent.memory.mem0_store.create_memory_instance") as mock_create:
            mock_memory = Mock()
            mock_create.return_value = mock_memory

            store = Mem0Store(mem0_config)

            assert store.config == mem0_config
            assert store.user_id == "test-user"
            assert store.namespace == "test-user:test-project"
            mock_create.assert_called_once_with(mem0_config)

    def test_initialization_without_project_id(self):
        """Test namespace without project_id."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_user_id="alice",
        )

        with patch("agent.memory.mem0_store.create_memory_instance") as mock_create:
            mock_memory = Mock()
            mock_create.return_value = mock_memory

            store = Mem0Store(config)

            assert store.namespace == "alice"  # Just user, no project

    @pytest.mark.asyncio
    async def test_add_messages_success(self, mem0_store):
        """Test adding messages to mem0 store."""
        mem0_store.memory.add.return_value = None  # mem0.Memory.add() returns None

        messages = [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Nice to meet you, Alice!"},
        ]

        result = await mem0_store.add(messages)

        assert result["success"] is True
        # Verify memory.add was called with properly formatted messages
        mem0_store.memory.add.assert_called_once()
        call_args = mem0_store.memory.add.call_args
        assert call_args.kwargs["user_id"] == "test-user:test-project"
        assert len(call_args.kwargs["messages"]) == 2

    @pytest.mark.asyncio
    async def test_add_filters_system_messages(self, mem0_store):
        """Test that system messages are filtered out."""
        mem0_store.memory.add.return_value = None

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ]

        result = await mem0_store.add(messages)

        assert result["success"] is True
        # Only user message should be added
        call_args = mem0_store.memory.add.call_args
        assert len(call_args.kwargs["messages"]) == 1
        assert call_args.kwargs["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_add_respects_save_false_metadata(self, mem0_store):
        """Test that messages with save=false metadata are not stored."""
        mem0_store.memory.add.return_value = None

        messages = [
            {"role": "user", "content": "Public message"},
            {"role": "user", "content": "Secret message", "metadata": {"save": False}},
        ]

        await mem0_store.add(messages)

        # Only first message should be added
        call_args = mem0_store.memory.add.call_args
        assert len(call_args.kwargs["messages"]) == 1
        assert call_args.kwargs["messages"][0]["content"] == "Public message"

    @pytest.mark.asyncio
    async def test_add_force_save_overrides_filters(self, mem0_store):
        """Test that force_save=true overrides default filters."""
        mem0_store.memory.add.return_value = None

        messages = [
            {"role": "system", "content": "System message", "metadata": {"force_save": True}},
        ]

        await mem0_store.add(messages)

        # System message should be saved due to force_save
        call_args = mem0_store.memory.add.call_args
        assert len(call_args.kwargs["messages"]) == 1

    @pytest.mark.asyncio
    async def test_add_scrubs_api_keys(self, mem0_store):
        """Test that API keys are scrubbed before storage."""
        mem0_store.memory.add.return_value = None

        messages = [{"role": "user", "content": "My API key is sk_test_1234567890abcdefghij"}]
        await mem0_store.add(messages)

        # Verify the content was scrubbed
        call_args = mem0_store.memory.add.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "[REDACTED]" in content
        assert "sk_test_" not in content

    @pytest.mark.asyncio
    async def test_add_scrubs_bearer_tokens(self, mem0_store):
        """Test that Bearer tokens are scrubbed before storage."""
        mem0_store.memory.add.return_value = None

        messages = [{"role": "user", "content": "Use Bearer abc123xyz789 for auth"}]
        await mem0_store.add(messages)

        call_args = mem0_store.memory.add.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "[REDACTED]" in content
        assert "abc123xyz789" not in content

    @pytest.mark.asyncio
    async def test_add_scrubs_passwords(self, mem0_store):
        """Test that password assignments are scrubbed."""
        mem0_store.memory.add.return_value = None

        messages = [{"role": "user", "content": "password=super_secret_123"}]
        await mem0_store.add(messages)

        call_args = mem0_store.memory.add.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "[REDACTED]" in content
        assert "super_secret_123" not in content

    @pytest.mark.asyncio
    async def test_add_empty_messages_returns_error(self, mem0_store):
        """Test adding empty message list returns error."""
        result = await mem0_store.add([])

        assert result["success"] is False
        assert result["error"] == "invalid_input"

    @pytest.mark.asyncio
    async def test_add_handles_client_error(self, mem0_store):
        """Test add handles memory errors gracefully."""
        mem0_store.memory.add.side_effect = Exception("Storage failed")

        messages = [{"role": "user", "content": "Test"}]
        result = await mem0_store.add(messages)

        assert result["success"] is False
        assert "storage_error" in result["error"]

    @pytest.mark.asyncio
    async def test_search_by_semantic_query(self, mem0_store):
        """Test searching memories by semantic similarity."""
        mem0_store.memory.search.return_value = {
            "results": [
                {
                    "id": "mem-123",
                    "memory": "User authentication failed",
                    "score": 0.95,
                    "created_at": "2025-01-01T00:00:00Z",
                    "metadata": {},
                }
            ]
        }

        result = await mem0_store.search("login errors", limit=5)

        assert result["success"] is True
        assert len(result["result"]) == 1
        assert result["result"][0]["content"] == "User authentication failed"
        assert result["result"][0]["score"] == 0.95

        mem0_store.memory.search.assert_called_once_with(
            query="login errors", user_id="test-user:test-project", limit=5
        )

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_error(self, mem0_store):
        """Test search with empty query returns error."""
        result = await mem0_store.search("", limit=5)

        assert result["success"] is False
        assert "invalid_query" in result["error"]

    @pytest.mark.asyncio
    async def test_search_handles_client_error(self, mem0_store):
        """Test search handles errors gracefully."""
        mem0_store.memory.search.side_effect = Exception("Search failed")

        result = await mem0_store.search("test", limit=5)

        assert result["success"] is False
        assert "search_error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_all_returns_all_memories(self, mem0_store):
        """Test get_all returns all stored memories."""
        mem0_store.memory.get_all.return_value = {
            "results": [
                {
                    "id": "mem-1",
                    "memory": "First memory",
                    "created_at": "2025-01-01",
                    "metadata": {},
                },
                {
                    "id": "mem-2",
                    "memory": "Second memory",
                    "created_at": "2025-01-02",
                    "metadata": {},
                },
            ]
        }

        result = await mem0_store.get_all()

        assert result["success"] is True
        assert len(result["result"]) == 2
        mem0_store.memory.get_all.assert_called_once_with(user_id="test-user:test-project")

    @pytest.mark.asyncio
    async def test_get_recent_returns_sorted_memories(self, mem0_store):
        """Test get_recent returns most recent memories."""
        mem0_store.memory.get_all.return_value = {
            "results": [
                {"id": "mem-1", "memory": "Oldest", "created_at": "2025-01-01", "metadata": {}},
                {"id": "mem-2", "memory": "Newest", "created_at": "2025-01-03", "metadata": {}},
                {"id": "mem-3", "memory": "Middle", "created_at": "2025-01-02", "metadata": {}},
            ]
        }

        result = await mem0_store.get_recent(limit=2)

        assert result["success"] is True
        assert len(result["result"]) == 2
        # Should be sorted by timestamp, most recent first
        assert result["result"][0]["content"] == "Newest"
        assert result["result"][1]["content"] == "Middle"

    @pytest.mark.asyncio
    async def test_clear_removes_all_memories(self, mem0_store):
        """Test clear removes all memories from storage."""
        mem0_store.memory.delete_all.return_value = None

        result = await mem0_store.clear()

        assert result["success"] is True
        assert "Cleared all memories" in result["message"]
        mem0_store.memory.delete_all.assert_called_once_with(user_id="test-user:test-project")

    @pytest.mark.asyncio
    async def test_clear_handles_error(self, mem0_store):
        """Test clear handles errors gracefully."""
        mem0_store.memory.delete_all.side_effect = Exception("Delete failed")

        result = await mem0_store.clear()

        assert result["success"] is False
        assert "clear_error" in result["error"]

    @pytest.mark.asyncio
    async def test_retrieve_for_context_uses_semantic_search(self, mem0_store):
        """Test retrieve_for_context uses semantic search."""
        mem0_store.memory.search.return_value = {
            "results": [
                {
                    "id": "mem-1",
                    "memory": "Relevant memory",
                    "score": 0.9,
                    "created_at": "2025-01-01",
                    "metadata": {},
                }
            ]
        }

        messages = [{"role": "user", "content": "What is my name?"}]

        result = await mem0_store.retrieve_for_context(messages, limit=5)

        assert result["success"] is True
        # Should have called search with the user's query
        mem0_store.memory.search.assert_called_once()
        call_args = mem0_store.memory.search.call_args
        assert "What is my name?" in call_args.kwargs["query"]

    @pytest.mark.asyncio
    async def test_retrieve_for_context_falls_back_to_recent(self, mem0_store):
        """Test retrieve_for_context falls back to recent when no user query."""
        mem0_store.memory.get_all.return_value = {"results": []}

        messages = [{"role": "system", "content": "System message"}]

        await mem0_store.retrieve_for_context(messages, limit=5)

        # Should fall back to get_recent (which calls get_all)
        mem0_store.memory.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test that different users have isolated namespaces."""
        config1 = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_user_id="alice",
        )
        config2 = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
            mem0_user_id="bob",
        )

        with patch("agent.memory.mem0_store.create_memory_instance") as mock_create:
            mock_memory = Mock()
            mock_create.return_value = mock_memory

            store1 = Mem0Store(config1)
            store2 = Mem0Store(config2)

            assert store1.namespace == "alice"
            assert store2.namespace == "bob"
            assert store1.namespace != store2.namespace
