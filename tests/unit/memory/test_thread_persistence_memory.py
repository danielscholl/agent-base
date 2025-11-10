"""Unit tests for ThreadPersistence memory integration."""

import json

import pytest

from agent.persistence import ThreadPersistence


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.persistence
class TestThreadPersistenceMemory:
    """Tests for ThreadPersistence memory state management."""

    @pytest.fixture
    def thread_persistence(self, tmp_path):
        """Create ThreadPersistence with temporary storage."""
        storage_dir = tmp_path / "sessions"
        memory_dir = tmp_path / "memory"
        return ThreadPersistence(storage_dir=storage_dir, memory_dir=memory_dir)

    def test_thread_persistence_has_memory_dir(self, thread_persistence):
        """Test ThreadPersistence has memory_dir attribute."""
        assert hasattr(thread_persistence, "memory_dir")
        assert thread_persistence.memory_dir.exists()

    def test_thread_persistence_creates_memory_dir(self, tmp_path):
        """Test ThreadPersistence creates memory directory."""
        memory_dir = tmp_path / "custom_memory"
        assert not memory_dir.exists()

        persistence = ThreadPersistence(storage_dir=tmp_path / "sessions", memory_dir=memory_dir)

        assert memory_dir.exists()
        assert persistence.memory_dir == memory_dir

    def test_thread_persistence_default_memory_dir(self, tmp_path):
        """Test ThreadPersistence defaults memory_dir."""
        persistence = ThreadPersistence(storage_dir=tmp_path / "sessions")

        tmp_path.home() / ".agent" / "memory"
        # Note: In tests this will use the system home dir
        assert persistence.memory_dir is not None

    @pytest.mark.asyncio
    async def test_save_memory_state(self, thread_persistence):
        """Test saving memory state for a session."""
        memory_data = [
            {"id": 0, "role": "user", "content": "Hello"},
            {"id": 1, "role": "assistant", "content": "Hi there"},
        ]

        path = await thread_persistence.save_memory_state("test-session", memory_data)

        # Verify file was created
        assert path.exists()
        assert path.name == "test-session-memory.json"

        # Verify content
        with open(path) as f:
            data = json.load(f)

        assert data["memory_count"] == 2
        assert len(data["memories"]) == 2
        assert data["memories"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_save_memory_state_updates_metadata(self, thread_persistence, tmp_path):
        """Test save_memory_state updates session metadata."""
        # Create a session first
        from unittest.mock import Mock

        mock_thread = Mock()
        mock_thread.message_store = None
        await thread_persistence.save_thread(mock_thread, "test-session")

        # Save memory state
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        await thread_persistence.save_memory_state("test-session", memory_data)

        # Verify metadata was updated
        assert "test-session" in thread_persistence.metadata["conversations"]
        session_meta = thread_persistence.metadata["conversations"]["test-session"]
        assert session_meta.get("has_memory") is True
        assert session_meta.get("memory_count") == 1

    @pytest.mark.asyncio
    async def test_save_memory_state_empty_list(self, thread_persistence):
        """Test saving empty memory list."""
        memory_data = []
        path = await thread_persistence.save_memory_state("empty-session", memory_data)

        assert path.exists()

        with open(path) as f:
            data = json.load(f)

        assert data["memory_count"] == 0
        assert data["memories"] == []

    @pytest.mark.asyncio
    async def test_save_memory_state_sanitizes_name(self, thread_persistence):
        """Test save_memory_state sanitizes session name."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]

        # Valid name should work
        path = await thread_persistence.save_memory_state("valid-name", memory_data)
        assert path.exists()

        # Invalid name should raise error
        with pytest.raises(ValueError):
            await thread_persistence.save_memory_state("../invalid", memory_data)

    @pytest.mark.asyncio
    async def test_load_memory_state(self, thread_persistence):
        """Test loading memory state for a session."""
        # Save first
        memory_data = [
            {"id": 0, "role": "user", "content": "Hello"},
            {"id": 1, "role": "assistant", "content": "Hi"},
        ]
        await thread_persistence.save_memory_state("load-test", memory_data)

        # Load it back
        loaded = await thread_persistence.load_memory_state("load-test")

        assert loaded is not None
        assert len(loaded) == 2
        assert loaded[0]["content"] == "Hello"
        assert loaded[1]["content"] == "Hi"

    @pytest.mark.asyncio
    async def test_load_memory_state_nonexistent_returns_none(self, thread_persistence):
        """Test loading nonexistent memory state returns None."""
        loaded = await thread_persistence.load_memory_state("nonexistent-session")

        assert loaded is None

    @pytest.mark.asyncio
    async def test_load_memory_state_sanitizes_name(self, thread_persistence):
        """Test load_memory_state sanitizes session name."""
        # Valid name should work
        loaded = await thread_persistence.load_memory_state("valid-name")
        assert loaded is None  # Doesn't exist, but name is valid

        # Invalid name should raise error
        with pytest.raises(ValueError):
            await thread_persistence.load_memory_state("../invalid")

    @pytest.mark.asyncio
    async def test_save_and_load_memory_roundtrip(self, thread_persistence):
        """Test saving and loading memory preserves data."""
        original_data = [
            {
                "id": 0,
                "role": "user",
                "content": "My name is Alice",
                "timestamp": "2024-01-01T00:00:00",
                "metadata": {"source": "cli"},
            },
            {
                "id": 1,
                "role": "assistant",
                "content": "Nice to meet you, Alice!",
                "timestamp": "2024-01-01T00:00:01",
                "metadata": {},
            },
        ]

        # Save and load
        await thread_persistence.save_memory_state("roundtrip", original_data)
        loaded_data = await thread_persistence.load_memory_state("roundtrip")

        # Should be identical
        assert loaded_data == original_data

    @pytest.mark.asyncio
    async def test_multiple_sessions_have_separate_memory(self, thread_persistence):
        """Test multiple sessions have independent memory files."""
        memory1 = [{"id": 0, "role": "user", "content": "Session 1"}]
        memory2 = [{"id": 0, "role": "user", "content": "Session 2"}]

        await thread_persistence.save_memory_state("session-1", memory1)
        await thread_persistence.save_memory_state("session-2", memory2)

        # Load each one
        loaded1 = await thread_persistence.load_memory_state("session-1")
        loaded2 = await thread_persistence.load_memory_state("session-2")

        assert loaded1[0]["content"] == "Session 1"
        assert loaded2[0]["content"] == "Session 2"

    @pytest.mark.asyncio
    async def test_save_memory_overwrites_existing(self, thread_persistence):
        """Test saving memory overwrites existing memory file."""
        # Save first version
        memory1 = [{"id": 0, "role": "user", "content": "First"}]
        await thread_persistence.save_memory_state("overwrite-test", memory1)

        loaded1 = await thread_persistence.load_memory_state("overwrite-test")
        assert loaded1[0]["content"] == "First"

        # Save second version (overwrite)
        memory2 = [{"id": 0, "role": "user", "content": "Second"}]
        await thread_persistence.save_memory_state("overwrite-test", memory2)

        loaded2 = await thread_persistence.load_memory_state("overwrite-test")
        assert len(loaded2) == 1
        assert loaded2[0]["content"] == "Second"

    @pytest.mark.asyncio
    async def test_memory_file_path_format(self, thread_persistence):
        """Test memory files have correct naming format."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]

        path = await thread_persistence.save_memory_state("my-session", memory_data)

        assert path.name == "my-session-memory.json"
        assert path.parent == thread_persistence.memory_dir

    @pytest.mark.asyncio
    async def test_save_memory_creates_parent_directories(self, tmp_path):
        """Test save_memory_state creates parent directories."""
        nested_dir = tmp_path / "nested" / "memory"
        persistence = ThreadPersistence(storage_dir=tmp_path / "sessions", memory_dir=nested_dir)

        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        path = await persistence.save_memory_state("test", memory_data)

        assert path.exists()
        assert path.parent == nested_dir

    @pytest.mark.asyncio
    async def test_memory_state_includes_version(self, thread_persistence):
        """Test saved memory state includes version metadata."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        path = await thread_persistence.save_memory_state("version-test", memory_data)

        with open(path) as f:
            data = json.load(f)

        assert "version" in data
        assert data["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_memory_state_includes_timestamp(self, thread_persistence):
        """Test saved memory state includes timestamp."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        path = await thread_persistence.save_memory_state("timestamp-test", memory_data)

        with open(path) as f:
            data = json.load(f)

        assert "saved_at" in data
        # Verify it's an ISO format timestamp
        assert "T" in data["saved_at"]

    @pytest.mark.asyncio
    async def test_memory_persistence_integration(self, thread_persistence):
        """Test ThreadPersistence integrates with MemoryPersistence."""
        # This test verifies ThreadPersistence correctly uses MemoryPersistence
        memory_data = [{"id": 0, "role": "user", "content": "Integration test"}]

        # Save via ThreadPersistence
        path = await thread_persistence.save_memory_state("integration", memory_data)

        # Verify it uses MemoryPersistence format
        with open(path) as f:
            data = json.load(f)

        # MemoryPersistence format
        assert "version" in data
        assert "saved_at" in data
        assert "memory_count" in data
        assert "memories" in data
        assert data["memories"] == memory_data
