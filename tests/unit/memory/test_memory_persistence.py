"""Unit tests for agent.memory.persistence module."""

import json
from pathlib import Path

import pytest

from agent.memory.persistence import MemoryPersistence


@pytest.mark.unit
@pytest.mark.memory
@pytest.mark.persistence
class TestMemoryPersistence:
    """Tests for MemoryPersistence class."""

    def test_initialization_default_directory(self):
        """Test MemoryPersistence initializes with default directory."""
        persistence = MemoryPersistence()

        expected_dir = Path.home() / ".agent" / "memory"
        assert persistence.storage_dir == expected_dir
        assert persistence.storage_dir.exists()

    def test_initialization_custom_directory(self, tmp_path):
        """Test MemoryPersistence initializes with custom directory."""
        custom_dir = tmp_path / "custom_memory"
        persistence = MemoryPersistence(storage_dir=custom_dir)

        assert persistence.storage_dir == custom_dir
        assert persistence.storage_dir.exists()

    def test_initialization_creates_directory(self, tmp_path):
        """Test MemoryPersistence creates storage directory."""
        storage_dir = tmp_path / "memory_test"
        assert not storage_dir.exists()

        persistence = MemoryPersistence(storage_dir=storage_dir)

        assert storage_dir.exists()
        assert persistence.storage_dir == storage_dir

    def test_version_attribute(self):
        """Test MemoryPersistence has VERSION attribute."""
        assert hasattr(MemoryPersistence, "VERSION")
        assert MemoryPersistence.VERSION == "1.0"

    @pytest.mark.asyncio
    async def test_save_memory_state(self, memory_persistence, tmp_path):
        """Test saving memory state to file."""
        memory_data = [
            {"id": 0, "role": "user", "content": "Hello"},
            {"id": 1, "role": "assistant", "content": "Hi there"},
        ]

        file_path = tmp_path / "memory" / "test-memory.json"

        await memory_persistence.save(memory_data, file_path)

        # Verify file was created
        assert file_path.exists()

        # Verify content
        with open(file_path) as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert data["memory_count"] == 2
        assert len(data["memories"]) == 2
        assert data["memories"][0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_save_includes_metadata(self, memory_persistence, tmp_path):
        """Test save includes metadata in saved state."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        file_path = tmp_path / "memory" / "test.json"

        await memory_persistence.save(memory_data, file_path)

        with open(file_path) as f:
            data = json.load(f)

        assert "version" in data
        assert "saved_at" in data
        assert "memory_count" in data
        assert "memories" in data

        # Verify saved_at is ISO format timestamp
        assert "T" in data["saved_at"]

    @pytest.mark.asyncio
    async def test_save_empty_memory_list(self, memory_persistence, tmp_path):
        """Test saving empty memory list."""
        memory_data = []
        file_path = tmp_path / "memory" / "empty.json"

        await memory_persistence.save(memory_data, file_path)

        with open(file_path) as f:
            data = json.load(f)

        assert data["memory_count"] == 0
        assert data["memories"] == []

    @pytest.mark.asyncio
    async def test_save_creates_parent_directories(self, memory_persistence, tmp_path):
        """Test save creates parent directories if they don't exist."""
        file_path = tmp_path / "memory" / "nested" / "dir" / "test.json"
        assert not file_path.parent.exists()

        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        await memory_persistence.save(memory_data, file_path)

        assert file_path.exists()
        assert file_path.parent.exists()

    @pytest.mark.asyncio
    async def test_load_memory_state(self, memory_persistence, tmp_path):
        """Test loading memory state from file."""
        # Create a memory file
        file_path = tmp_path / "memory" / "load-test.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        memory_state = {
            "version": "1.0",
            "saved_at": "2024-01-01T00:00:00",
            "memory_count": 2,
            "memories": [
                {"id": 0, "role": "user", "content": "Hello"},
                {"id": 1, "role": "assistant", "content": "Hi"},
            ],
        }

        with open(file_path, "w") as f:
            json.dump(memory_state, f)

        # Load it
        loaded_memories = await memory_persistence.load(file_path)

        assert loaded_memories is not None
        assert len(loaded_memories) == 2
        assert loaded_memories[0]["content"] == "Hello"
        assert loaded_memories[1]["content"] == "Hi"

    @pytest.mark.asyncio
    async def test_load_nonexistent_file_returns_none(self, memory_persistence, tmp_path):
        """Test loading nonexistent file returns None."""
        file_path = tmp_path / "memory" / "nonexistent.json"

        loaded_memories = await memory_persistence.load(file_path)

        assert loaded_memories is None

    @pytest.mark.asyncio
    async def test_load_empty_memory_list(self, memory_persistence, tmp_path):
        """Test loading file with empty memory list."""
        file_path = tmp_path / "memory" / "empty.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        memory_state = {
            "version": "1.0",
            "saved_at": "2024-01-01T00:00:00",
            "memory_count": 0,
            "memories": [],
        }

        with open(file_path, "w") as f:
            json.dump(memory_state, f)

        loaded_memories = await memory_persistence.load(file_path)

        assert loaded_memories == []

    @pytest.mark.asyncio
    async def test_load_handles_version_mismatch(self, memory_persistence, tmp_path):
        """Test load handles version mismatch gracefully."""
        file_path = tmp_path / "memory" / "old-version.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        memory_state = {
            "version": "0.5",  # Different version
            "saved_at": "2024-01-01T00:00:00",
            "memory_count": 1,
            "memories": [{"id": 0, "role": "user", "content": "Test"}],
        }

        with open(file_path, "w") as f:
            json.dump(memory_state, f)

        # Should still load despite version mismatch
        loaded_memories = await memory_persistence.load(file_path)

        assert loaded_memories is not None
        assert len(loaded_memories) == 1

    @pytest.mark.asyncio
    async def test_load_handles_missing_version(self, memory_persistence, tmp_path):
        """Test load handles missing version field."""
        file_path = tmp_path / "memory" / "no-version.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        memory_state = {
            # No version field
            "saved_at": "2024-01-01T00:00:00",
            "memory_count": 1,
            "memories": [{"id": 0, "role": "user", "content": "Test"}],
        }

        with open(file_path, "w") as f:
            json.dump(memory_state, f)

        # Should still load
        loaded_memories = await memory_persistence.load(file_path)

        assert loaded_memories is not None
        assert len(loaded_memories) == 1

    @pytest.mark.asyncio
    async def test_load_corrupted_file_raises_error(self, memory_persistence, tmp_path):
        """Test loading corrupted JSON file raises error."""
        file_path = tmp_path / "memory" / "corrupted.json"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        with open(file_path, "w") as f:
            f.write("{ invalid json content")

        # Should raise exception
        with pytest.raises(Exception):
            await memory_persistence.load(file_path)

    @pytest.mark.asyncio
    async def test_save_and_load_roundtrip(self, memory_persistence, tmp_path):
        """Test saving and loading memories preserves data."""
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

        file_path = tmp_path / "memory" / "roundtrip.json"

        # Save and load
        await memory_persistence.save(original_data, file_path)
        loaded_data = await memory_persistence.load(file_path)

        # Should be identical
        assert loaded_data == original_data

    def test_get_memory_path_returns_correct_path(self, memory_persistence):
        """Test get_memory_path returns correct file path."""
        path = memory_persistence.get_memory_path("session-1")

        assert path == memory_persistence.storage_dir / "session-1-memory.json"
        assert path.name == "session-1-memory.json"

    def test_get_memory_path_different_sessions(self, memory_persistence):
        """Test get_memory_path returns different paths for different sessions."""
        path1 = memory_persistence.get_memory_path("session-1")
        path2 = memory_persistence.get_memory_path("session-2")

        assert path1 != path2
        assert path1.name == "session-1-memory.json"
        assert path2.name == "session-2-memory.json"

    @pytest.mark.asyncio
    async def test_save_with_get_memory_path(self, memory_persistence):
        """Test using get_memory_path for saving."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        file_path = memory_persistence.get_memory_path("test-session")

        await memory_persistence.save(memory_data, file_path)

        assert file_path.exists()

        # Verify we can load it back
        loaded = await memory_persistence.load(file_path)
        assert loaded == memory_data

    def test_storage_dir_attribute(self, memory_persistence, tmp_path):
        """Test persistence has storage_dir attribute."""
        assert hasattr(memory_persistence, "storage_dir")
        assert isinstance(memory_persistence.storage_dir, Path)

    @pytest.mark.asyncio
    async def test_save_overwrites_existing_file(self, memory_persistence, tmp_path):
        """Test save overwrites existing file."""
        file_path = tmp_path / "memory" / "overwrite.json"

        # Save first version
        data1 = [{"id": 0, "role": "user", "content": "First"}]
        await memory_persistence.save(data1, file_path)

        loaded1 = await memory_persistence.load(file_path)
        assert len(loaded1) == 1
        assert loaded1[0]["content"] == "First"

        # Save second version (overwrite)
        data2 = [{"id": 0, "role": "user", "content": "Second"}]
        await memory_persistence.save(data2, file_path)

        loaded2 = await memory_persistence.load(file_path)
        assert len(loaded2) == 1
        assert loaded2[0]["content"] == "Second"

    @pytest.mark.asyncio
    async def test_save_preserves_complex_metadata(self, memory_persistence, tmp_path):
        """Test save preserves complex metadata structures."""
        memory_data = [
            {
                "id": 0,
                "role": "user",
                "content": "Test",
                "metadata": {
                    "source": "cli",
                    "session": "test-1",
                    "user_info": {"name": "Alice", "preferences": ["Python", "AI"]},
                },
            }
        ]

        file_path = tmp_path / "memory" / "complex.json"

        await memory_persistence.save(memory_data, file_path)
        loaded = await memory_persistence.load(file_path)

        assert loaded[0]["metadata"]["user_info"]["name"] == "Alice"
        assert loaded[0]["metadata"]["user_info"]["preferences"] == ["Python", "AI"]

    @pytest.mark.asyncio
    async def test_save_handles_write_error(self, memory_persistence, tmp_path, monkeypatch):
        """Test save handles file write errors gracefully."""
        memory_data = [{"id": 0, "role": "user", "content": "Test"}]
        file_path = tmp_path / "memory" / "error.json"

        # Mock open to raise an error
        import builtins

        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if str(file_path) in str(args[0]):
                raise PermissionError("Cannot write to file")
            return original_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        # Should raise exception (not catch and ignore)
        with pytest.raises(PermissionError):
            await memory_persistence.save(memory_data, file_path)
