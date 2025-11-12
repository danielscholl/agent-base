"""Unit tests for agent.memory.manager module."""

from unittest.mock import Mock, patch

import pytest

from agent.config import AgentConfig
from agent.memory import InMemoryStore, MemoryManager, create_memory_manager


@pytest.mark.unit
@pytest.mark.memory
class TestMemoryManager:
    """Tests for MemoryManager ABC."""

    def test_memory_manager_is_abstract(self):
        """Test MemoryManager cannot be instantiated directly."""
        config = AgentConfig(llm_provider="openai", openai_api_key="test", memory_enabled=True)

        with pytest.raises(TypeError):
            # Should raise TypeError because MemoryManager is abstract
            MemoryManager(config)

    def test_in_memory_store_implements_memory_manager(self, memory_config):
        """Test InMemoryStore is a MemoryManager."""
        store = InMemoryStore(memory_config)

        assert isinstance(store, MemoryManager)

    def test_memory_manager_has_config(self, memory_store, memory_config):
        """Test MemoryManager stores config."""
        assert memory_store.config == memory_config

    def test_create_success_response_structure(self, memory_store):
        """Test _create_success_response creates proper structure."""
        response = memory_store._create_success_response(result={"data": "test"}, message="Success")

        assert response["success"] is True
        assert response["result"] == {"data": "test"}
        assert response["message"] == "Success"

    def test_create_success_response_empty_message(self, memory_store):
        """Test _create_success_response with empty message."""
        response = memory_store._create_success_response(result=[], message="")

        assert response["success"] is True
        assert response["result"] == []
        assert response["message"] == ""

    def test_create_error_response_structure(self, memory_store):
        """Test _create_error_response creates proper structure."""
        response = memory_store._create_error_response(
            error="test_error", message="Something went wrong"
        )

        assert response["success"] is False
        assert response["error"] == "test_error"
        assert response["message"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_memory_manager_interface_methods_exist(self, memory_store):
        """Test MemoryManager interface methods are implemented."""
        # Verify all abstract methods are implemented
        assert hasattr(memory_store, "add")
        assert callable(memory_store.add)

        assert hasattr(memory_store, "search")
        assert callable(memory_store.search)

        assert hasattr(memory_store, "get_all")
        assert callable(memory_store.get_all)

        assert hasattr(memory_store, "get_recent")
        assert callable(memory_store.get_recent)

        assert hasattr(memory_store, "clear")
        assert callable(memory_store.clear)


@pytest.mark.unit
@pytest.mark.memory
class TestCreateMemoryManager:
    """Tests for create_memory_manager factory function."""

    def test_create_memory_manager_returns_in_memory_store(self, memory_config):
        """Test factory creates InMemoryStore by default."""
        manager = create_memory_manager(memory_config)

        assert isinstance(manager, InMemoryStore)
        assert isinstance(manager, MemoryManager)

    def test_create_memory_manager_with_memory_type(self):
        """Test factory respects memory_type config."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_enabled=True,
            memory_type="in_memory",
        )

        manager = create_memory_manager(config)

        assert isinstance(manager, InMemoryStore)

    def test_create_memory_manager_passes_config(self, memory_config):
        """Test factory passes config to manager."""
        manager = create_memory_manager(memory_config)

        assert manager.config == memory_config

    def test_create_memory_manager_creates_new_instance(self, memory_config):
        """Test factory creates new instance each time."""
        manager1 = create_memory_manager(memory_config)
        manager2 = create_memory_manager(memory_config)

        assert manager1 is not manager2
        assert isinstance(manager1, InMemoryStore)
        assert isinstance(manager2, InMemoryStore)

    @pytest.mark.asyncio
    async def test_created_manager_is_functional(self, memory_config):
        """Test created manager is fully functional."""
        manager = create_memory_manager(memory_config)

        # Add a message
        add_result = await manager.add([{"role": "user", "content": "Test"}])
        assert add_result["success"] is True

        # Search for it
        search_result = await manager.search("Test")
        assert search_result["success"] is True
        assert len(search_result["result"]) == 1

        # Get all
        all_result = await manager.get_all()
        assert all_result["success"] is True
        assert len(all_result["result"]) == 1

        # Clear
        clear_result = await manager.clear()
        assert clear_result["success"] is True

    def test_create_memory_manager_mem0_type(self):
        """Test factory routes to Mem0Store when memory_type is mem0."""
        from agent.memory.mem0_store import Mem0Store

        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
        )

        with patch("agent.memory.mem0_store.create_memory_instance") as mock_create:
            mock_create.return_value = Mock()

            manager = create_memory_manager(config)

            assert isinstance(manager, Mem0Store)

    def test_create_memory_manager_mem0_fallback_on_error(self):
        """Test factory falls back to InMemoryStore when Mem0Store fails."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="mem0",
        )

        with patch("agent.memory.mem0_store.create_memory_instance") as mock_create:
            mock_create.side_effect = Exception("Connection failed")

            manager = create_memory_manager(config)

            # Should fall back to InMemoryStore
            assert isinstance(manager, InMemoryStore)

    def test_create_memory_manager_default_to_in_memory(self):
        """Test factory defaults to InMemoryStore for unknown types."""
        config = AgentConfig(
            llm_provider="openai",
            openai_api_key="test",
            memory_type="unknown_type",
        )

        manager = create_memory_manager(config)

        assert isinstance(manager, InMemoryStore)
