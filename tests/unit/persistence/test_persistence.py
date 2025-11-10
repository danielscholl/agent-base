"""Unit tests for agent.persistence module."""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from agent.persistence import ThreadPersistence, _sanitize_conversation_name


@pytest.mark.unit
@pytest.mark.persistence
class TestSanitizeConversationName:
    """Tests for conversation name sanitization."""

    def test_valid_name(self):
        """Test valid conversation names pass through."""
        assert _sanitize_conversation_name("my-session") == "my-session"
        assert _sanitize_conversation_name("Session_2024") == "Session_2024"
        assert _sanitize_conversation_name("test.session.1") == "test.session.1"

    def test_empty_name_raises_error(self):
        """Test empty name raises ValueError."""
        with pytest.raises(ValueError, match="must be between 1 and 64"):
            _sanitize_conversation_name("")

    def test_too_long_name_raises_error(self):
        """Test name longer than 64 characters raises ValueError."""
        long_name = "a" * 65
        with pytest.raises(ValueError, match="must be between 1 and 64"):
            _sanitize_conversation_name(long_name)

    def test_invalid_characters_raise_error(self):
        """Test names with invalid characters raise ValueError."""
        with pytest.raises(ValueError, match="can only contain"):
            _sanitize_conversation_name("session/path")

        with pytest.raises(ValueError, match="can only contain"):
            _sanitize_conversation_name("session name")  # space not allowed

    def test_path_traversal_raises_error(self):
        """Test path traversal attempts raise ValueError."""
        # Note: "../etc/passwd" fails on invalid characters first
        with pytest.raises(ValueError):
            _sanitize_conversation_name("../etc/passwd")

        # This one specifically tests the ".." check
        with pytest.raises(ValueError, match="path traversal"):
            _sanitize_conversation_name("session..backup")

    def test_reserved_names_raise_error(self):
        """Test reserved names raise ValueError."""
        with pytest.raises(ValueError, match="Reserved name"):
            _sanitize_conversation_name("index")

        with pytest.raises(ValueError, match="Reserved name"):
            _sanitize_conversation_name("CON")  # case insensitive


@pytest.mark.unit
@pytest.mark.persistence
class TestThreadPersistence:
    """Tests for ThreadPersistence class."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        storage_dir = tmp_path / "sessions"
        return storage_dir

    @pytest.fixture
    def persistence(self, temp_storage):
        """Create ThreadPersistence instance with temporary storage."""
        return ThreadPersistence(storage_dir=temp_storage)

    def test_initialization_creates_directory(self, temp_storage):
        """Test ThreadPersistence creates storage directory."""
        persistence = ThreadPersistence(storage_dir=temp_storage)

        assert temp_storage.exists()
        assert persistence.storage_dir == temp_storage

    def test_initialization_creates_metadata_file(self, persistence):
        """Test ThreadPersistence creates metadata index file."""
        assert persistence.metadata_file.exists()
        assert persistence.metadata == {"conversations": {}}

    def test_metadata_loads_existing_file(self, temp_storage):
        """Test ThreadPersistence loads existing metadata."""
        # Create metadata file
        metadata_file = temp_storage / "index.json"
        temp_storage.mkdir(parents=True, exist_ok=True)
        test_metadata = {"conversations": {"test": {"name": "test"}}}
        with open(metadata_file, "w") as f:
            json.dump(test_metadata, f)

        # Load persistence
        persistence = ThreadPersistence(storage_dir=temp_storage)

        assert persistence.metadata == test_metadata

    def test_metadata_handles_corrupted_file(self, temp_storage, caplog):
        """Test ThreadPersistence handles corrupted metadata gracefully."""
        # Create sessions directory
        sessions_dir = temp_storage / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Create corrupted metadata file
        metadata_file = sessions_dir / "index.json"
        with open(metadata_file, "w") as f:
            f.write("{ invalid json }")

        # Should start fresh instead of crashing
        persistence = ThreadPersistence(storage_dir=sessions_dir)

        assert persistence.metadata == {"conversations": {}}
        assert "Failed to load metadata" in caplog.text

    def test_save_metadata_handles_write_error(self, persistence, monkeypatch):
        """Test _save_metadata handles write errors."""
        import builtins

        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if "index.json" in str(args[0]) and "w" in str(
                kwargs.get("mode", args[1] if len(args) > 1 else "")
            ):
                raise PermissionError("Cannot write metadata")
            return original_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        # Should raise the exception
        with pytest.raises(PermissionError):
            persistence._save_metadata()

    def test_generate_context_summary_empty_messages(self, persistence):
        """Test context summary generation with empty messages."""
        summary = persistence._generate_context_summary([])

        assert "Empty session" in summary

    def test_generate_context_summary_with_messages(self, persistence):
        """Test context summary generation with messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]

        summary = persistence._generate_context_summary(messages)

        assert "resuming" in summary.lower()
        assert "User requests:" in summary
        assert "Hello" in summary
        assert "3 messages" in summary

    @pytest.mark.asyncio
    async def test_fallback_serialize_extracts_messages(self, persistence):
        """Test fallback serialization extracts messages from thread."""
        # Mock thread with message_store
        mock_thread = Mock()
        mock_message_store = Mock()

        # Mock messages
        mock_msg1 = Mock()
        mock_msg1.role = "user"
        mock_msg1.text = "Hello"
        mock_msg1.tool_calls = None

        mock_msg2 = Mock()
        mock_msg2.role = "assistant"
        mock_msg2.content = "Hi there"
        mock_msg2.tool_calls = None

        mock_message_store.list_messages = AsyncMock(return_value=[mock_msg1, mock_msg2])
        mock_thread.message_store = mock_message_store

        # Serialize
        result = await persistence._fallback_serialize(mock_thread)

        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"
        assert result["metadata"]["fallback"] is True

    @pytest.mark.asyncio
    async def test_save_thread_creates_file(self, persistence, temp_storage):
        """Test save_thread creates conversation file."""
        # Mock thread
        mock_thread = Mock()
        mock_message_store = Mock()

        mock_msg = Mock()
        mock_msg.role = "user"
        mock_msg.text = "Test message"
        mock_msg.tool_calls = None

        mock_message_store.list_messages = AsyncMock(return_value=[mock_msg])
        mock_thread.message_store = mock_message_store
        mock_thread.serialize = AsyncMock(return_value={"test": "data"})

        # Save thread
        path = await persistence.save_thread(mock_thread, "test-session")

        # Verify file was created
        assert path.exists()
        assert path.name == "test-session.json"

        # Verify content
        with open(path) as f:
            data = json.load(f)

        assert data["name"] == "test-session"
        assert data["message_count"] == 1
        assert "Test message" in data["first_message"]

    @pytest.mark.asyncio
    async def test_save_thread_updates_metadata(self, persistence):
        """Test save_thread updates metadata index."""
        # Mock thread
        mock_thread = Mock()
        mock_thread.message_store = Mock()
        mock_thread.message_store.list_messages = AsyncMock(return_value=[])
        mock_thread.serialize = AsyncMock(return_value={})

        # Save thread
        await persistence.save_thread(mock_thread, "test-session", description="Test description")

        # Verify metadata
        assert "test-session" in persistence.metadata["conversations"]
        assert (
            persistence.metadata["conversations"]["test-session"]["description"]
            == "Test description"
        )

    @pytest.mark.asyncio
    async def test_save_thread_with_invalid_name_raises_error(self, persistence):
        """Test save_thread with invalid name raises ValueError."""
        mock_thread = Mock()

        with pytest.raises(ValueError):
            await persistence.save_thread(mock_thread, "../invalid")

    @pytest.mark.asyncio
    async def test_load_thread_nonexistent_raises_error(self, persistence):
        """Test load_thread with nonexistent session raises FileNotFoundError."""
        mock_agent = Mock()

        with pytest.raises(FileNotFoundError):
            await persistence.load_thread(mock_agent, "nonexistent")

    @pytest.mark.asyncio
    async def test_load_thread_with_fallback_data(self, persistence, temp_storage):
        """Test load_thread with fallback-serialized data."""
        # Create fallback session file
        session_file = temp_storage / "fallback-session.json"
        session_data = {
            "name": "fallback-session",
            "description": "Test",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "message_count": 2,
            "first_message": "Hello",
            "thread": {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                ],
                "metadata": {"fallback": True, "version": "1.0"},
            },
        }

        with open(session_file, "w") as f:
            json.dump(session_data, f)

        # Mock agent
        mock_agent = Mock()
        mock_agent.chat_client = Mock()
        mock_agent.chat_client.create_thread = Mock(return_value="new_thread")

        # Load thread
        thread, context = await persistence.load_thread(mock_agent, "fallback-session")

        # Should return new thread and context summary
        assert thread is not None
        assert context is not None
        assert "resuming" in context.lower()

    def test_list_sessions_returns_all_sessions(self, persistence):
        """Test list_sessions returns all saved sessions."""
        # Add some sessions to metadata
        persistence.metadata["conversations"] = {
            "session1": {"name": "session1", "message_count": 5},
            "session2": {"name": "session2", "message_count": 10},
        }

        sessions = persistence.list_sessions()

        assert len(sessions) == 2
        assert any(s["name"] == "session1" for s in sessions)
        assert any(s["name"] == "session2" for s in sessions)

    def test_list_sessions_empty(self, persistence):
        """Test list_sessions returns empty list when no sessions."""
        sessions = persistence.list_sessions()

        assert sessions == []

    def test_delete_session_removes_file_and_metadata(self, persistence, temp_storage):
        """Test delete_session removes file and metadata entry."""
        # Create a session file
        session_file = temp_storage / "test-session.json"
        session_file.write_text(json.dumps({"name": "test-session"}))

        # Add to metadata
        persistence.metadata["conversations"]["test-session"] = {"name": "test-session"}

        # Delete session
        persistence.delete_session("test-session")

        # Verify file deleted
        assert not session_file.exists()

        # Verify metadata updated
        assert "test-session" not in persistence.metadata["conversations"]

    def test_delete_session_nonexistent_raises_error(self, persistence):
        """Test delete_session with nonexistent session raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            persistence.delete_session("nonexistent")
