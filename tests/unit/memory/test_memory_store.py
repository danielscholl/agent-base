"""Unit tests for agent.memory.store module."""

import pytest

from agent.memory.store import InMemoryStore


@pytest.mark.unit
@pytest.mark.memory
class TestInMemoryStore:
    """Tests for InMemoryStore class."""

    def test_initialization(self, memory_config):
        """Test InMemoryStore initializes with config."""
        store = InMemoryStore(memory_config)

        assert store.config == memory_config
        assert store.memories == []

    @pytest.mark.asyncio
    async def test_add_messages_success(self, memory_store, sample_messages):
        """Test adding messages to memory store."""
        result = await memory_store.add(sample_messages)

        assert result["success"] is True
        assert len(result["result"]) == 4
        assert "Added 4 messages" in result["message"]
        assert len(memory_store.memories) == 4

    @pytest.mark.asyncio
    async def test_add_messages_with_metadata(self, memory_store):
        """Test adding messages with custom metadata."""
        messages = [
            {
                "role": "user",
                "content": "Test message",
                "metadata": {"source": "cli", "session": "test-1"},
            }
        ]

        result = await memory_store.add(messages)

        assert result["success"] is True
        assert len(memory_store.memories) == 1
        assert memory_store.memories[0]["metadata"]["source"] == "cli"
        assert memory_store.memories[0]["metadata"]["session"] == "test-1"

    @pytest.mark.asyncio
    async def test_add_empty_messages_returns_error(self, memory_store):
        """Test adding empty message list returns error."""
        result = await memory_store.add([])

        assert result["success"] is False
        assert result["error"] == "invalid_input"
        assert "No messages provided" in result["message"]

    @pytest.mark.asyncio
    async def test_add_invalid_messages_skips_them(self, memory_store):
        """Test adding invalid messages skips them and adds valid ones."""
        messages = [
            {"role": "user", "content": "Valid message"},
            {"invalid": "message"},  # Missing role and content
            "not a dict",  # Not a dict
            {"role": "user"},  # Missing content
        ]

        result = await memory_store.add(messages)

        # Only 1 valid message should be added
        assert result["success"] is True
        assert len(result["result"]) == 1
        assert len(memory_store.memories) == 1

    @pytest.mark.asyncio
    async def test_add_assigns_incrementing_ids(self, memory_store, sample_messages):
        """Test that added messages get incrementing IDs."""
        await memory_store.add(sample_messages[:2])
        await memory_store.add(sample_messages[2:])

        assert memory_store.memories[0]["id"] == 0
        assert memory_store.memories[1]["id"] == 1
        assert memory_store.memories[2]["id"] == 2
        assert memory_store.memories[3]["id"] == 3

    @pytest.mark.asyncio
    async def test_add_includes_timestamp(self, memory_store):
        """Test that added messages include timestamp."""
        messages = [{"role": "user", "content": "Test"}]
        await memory_store.add(messages)

        assert "timestamp" in memory_store.memories[0]
        # Verify it's an ISO format timestamp
        assert "T" in memory_store.memories[0]["timestamp"]

    @pytest.mark.asyncio
    async def test_search_by_keyword(self, memory_store, sample_messages):
        """Test searching memories by keyword."""
        await memory_store.add(sample_messages)

        result = await memory_store.search("Alice", limit=5)

        assert result["success"] is True
        assert len(result["result"]) == 2  # Two messages mention Alice
        assert "Alice" in result["result"][0]["content"]

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, memory_store, sample_messages):
        """Test search is case-insensitive."""
        await memory_store.add(sample_messages)

        result = await memory_store.search("python", limit=5)

        assert result["success"] is True
        assert len(result["result"]) == 2  # Two messages mention Python
        # Original content has "Python" with capital P
        assert any("Python" in m["content"] for m in result["result"])

    @pytest.mark.asyncio
    async def test_search_multiple_keywords(self, memory_store, sample_messages):
        """Test searching with multiple keywords."""
        await memory_store.add(sample_messages)

        result = await memory_store.search("Alice name", limit=5)

        assert result["success"] is True
        # Should find message with both keywords ranked higher
        assert len(result["result"]) >= 1
        assert "name" in result["result"][0]["content"].lower()

    @pytest.mark.asyncio
    async def test_search_ranks_by_relevance(self, memory_store):
        """Test search results are ranked by keyword match count."""
        messages = [
            {"role": "user", "content": "I like Python"},
            {"role": "user", "content": "Python and Java"},  # Matches 2 keywords
            {"role": "user", "content": "Learning"},  # Matches 0 keywords
        ]
        await memory_store.add(messages)

        # Search with multiple keywords
        result = await memory_store.search("Python Java", limit=5)

        assert result["success"] is True
        # Message matching both keywords should be first
        assert result["result"][0]["content"] == "Python and Java"
        # Message matching one keyword should be second
        assert result["result"][1]["content"] == "I like Python"

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, memory_store):
        """Test search respects limit parameter."""
        messages = [{"role": "user", "content": f"Python message {i}"} for i in range(10)]
        await memory_store.add(messages)

        result = await memory_store.search("Python", limit=3)

        assert result["success"] is True
        assert len(result["result"]) == 3

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_error(self, memory_store):
        """Test searching with empty query returns error."""
        result = await memory_store.search("", limit=5)

        assert result["success"] is False
        assert result["error"] == "invalid_query"
        assert "cannot be empty" in result["message"]

    @pytest.mark.asyncio
    async def test_search_whitespace_query_returns_error(self, memory_store):
        """Test searching with whitespace-only query returns error."""
        result = await memory_store.search("   ", limit=5)

        assert result["success"] is False
        assert result["error"] == "invalid_query"

    @pytest.mark.asyncio
    async def test_search_no_matches(self, memory_store, sample_messages):
        """Test searching returns empty results when no matches."""
        await memory_store.add(sample_messages)

        result = await memory_store.search("nonexistent", limit=5)

        assert result["success"] is True
        assert len(result["result"]) == 0
        assert "Found 0 matching memories" in result["message"]

    @pytest.mark.asyncio
    async def test_get_all_returns_all_memories(self, memory_store, sample_messages):
        """Test get_all returns all stored memories."""
        await memory_store.add(sample_messages)

        result = await memory_store.get_all()

        assert result["success"] is True
        assert len(result["result"]) == 4
        assert result["result"] == memory_store.memories

    @pytest.mark.asyncio
    async def test_get_all_empty_store(self, memory_store):
        """Test get_all returns empty list when no memories."""
        result = await memory_store.get_all()

        assert result["success"] is True
        assert result["result"] == []

    @pytest.mark.asyncio
    async def test_get_recent_returns_recent_memories(self, memory_store, sample_messages):
        """Test get_recent returns most recent memories."""
        await memory_store.add(sample_messages)

        result = await memory_store.get_recent(limit=2)

        assert result["success"] is True
        assert len(result["result"]) == 2
        # Should return last 2 messages
        assert result["result"][0] == memory_store.memories[-2]
        assert result["result"][1] == memory_store.memories[-1]

    @pytest.mark.asyncio
    async def test_get_recent_respects_limit(self, memory_store):
        """Test get_recent respects limit parameter."""
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(20)]
        await memory_store.add(messages)

        result = await memory_store.get_recent(limit=5)

        assert result["success"] is True
        assert len(result["result"]) == 5

    @pytest.mark.asyncio
    async def test_get_recent_with_fewer_memories_than_limit(self, memory_store):
        """Test get_recent when store has fewer memories than limit."""
        messages = [{"role": "user", "content": "Message 1"}]
        await memory_store.add(messages)

        result = await memory_store.get_recent(limit=10)

        assert result["success"] is True
        assert len(result["result"]) == 1

    @pytest.mark.asyncio
    async def test_get_recent_empty_store(self, memory_store):
        """Test get_recent returns empty list when no memories."""
        result = await memory_store.get_recent(limit=10)

        assert result["success"] is True
        assert result["result"] == []

    @pytest.mark.asyncio
    async def test_clear_removes_all_memories(self, memory_store, sample_messages):
        """Test clear removes all memories from storage."""
        await memory_store.add(sample_messages)
        assert len(memory_store.memories) == 4

        result = await memory_store.clear()

        assert result["success"] is True
        assert "Cleared 4 memories" in result["message"]
        assert len(memory_store.memories) == 0

    @pytest.mark.asyncio
    async def test_clear_empty_store(self, memory_store):
        """Test clearing empty store."""
        result = await memory_store.clear()

        assert result["success"] is True
        assert "Cleared 0 memories" in result["message"]
        assert len(memory_store.memories) == 0

    @pytest.mark.asyncio
    async def test_memory_entry_structure(self, memory_store):
        """Test memory entry has expected structure."""
        messages = [{"role": "user", "content": "Test message"}]
        await memory_store.add(messages)

        memory = memory_store.memories[0]

        # Verify all expected fields are present
        assert "id" in memory
        assert "role" in memory
        assert "content" in memory
        assert "timestamp" in memory
        assert "metadata" in memory

        # Verify field types
        assert isinstance(memory["id"], int)
        assert isinstance(memory["role"], str)
        assert isinstance(memory["content"], str)
        assert isinstance(memory["timestamp"], str)
        assert isinstance(memory["metadata"], dict)

    @pytest.mark.asyncio
    async def test_memory_preserves_role_and_content(self, memory_store):
        """Test memory preserves original role and content."""
        messages = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
        ]
        await memory_store.add(messages)

        assert memory_store.memories[0]["role"] == "user"
        assert memory_store.memories[0]["content"] == "User message"
        assert memory_store.memories[1]["role"] == "assistant"
        assert memory_store.memories[1]["content"] == "Assistant response"

    @pytest.mark.asyncio
    async def test_response_structure(self, memory_store):
        """Test all operations return properly structured responses."""
        messages = [{"role": "user", "content": "Test"}]

        # Test add response
        add_result = await memory_store.add(messages)
        assert "success" in add_result
        assert "result" in add_result
        assert "message" in add_result

        # Test search response
        search_result = await memory_store.search("test")
        assert "success" in search_result
        assert "result" in search_result
        assert "message" in search_result

        # Test get_all response
        get_all_result = await memory_store.get_all()
        assert "success" in get_all_result
        assert "result" in get_all_result
        assert "message" in get_all_result

        # Test get_recent response
        get_recent_result = await memory_store.get_recent()
        assert "success" in get_recent_result
        assert "result" in get_recent_result
        assert "message" in get_recent_result

        # Test clear response
        clear_result = await memory_store.clear()
        assert "success" in clear_result
        assert "message" in clear_result
