"""Tests for ContextLoom."""

import pytest
from unittest.mock import AsyncMock, patch
from core.loom import ContextLoom
from models.schema import ContextState

@pytest.fixture
def mock_connector():
    connector = AsyncMock()
    connector.fetch.return_value = {"user": "alice"}
    return connector

@pytest.fixture
def mock_redis_manager():
    manager = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_loom_cold_start(mock_connector, mock_redis_manager):
    """Test cold start hydration (Redis miss)."""

    # Patch RedisManager.get_instance to return our mock
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        loom = ContextLoom(mock_connector, "SELECT * FROM users WHERE id = :session_id")

        # Mock Redis returning None (Cold Start)
        mock_redis_manager.load_context.return_value = None

        session_id = "user_123"
        state = await loom.sync(session_id)

        # Verify connector called with parameterized query
        mock_connector.fetch.assert_called_with(
            "SELECT * FROM users WHERE id = :session_id",
            values={'session_id': 'user_123'}
        )

        # Verify state created and returned
        assert state.session_id == session_id
        assert state.static_data == {"user": "alice"}

        # Verify saved to Redis
        mock_redis_manager.save_context.assert_called_once()
        saved_state = mock_redis_manager.save_context.call_args[0][0]
        assert saved_state.session_id == session_id
        assert saved_state.static_data == {"user": "alice"}

@pytest.mark.asyncio
async def test_loom_cache_hit(mock_connector, mock_redis_manager):
    """Test cache hit (Redis has data)."""

    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        loom = ContextLoom(mock_connector, "query")

        existing_state = ContextState(session_id="user_123", static_data={"existing": True})
        mock_redis_manager.load_context.return_value = existing_state

        state = await loom.sync("user_123")

        # Connector should NOT be called
        mock_connector.fetch.assert_not_called()
        assert state == existing_state

@pytest.mark.asyncio
async def test_loom_initialize(mock_connector, mock_redis_manager):
    """Test ContextLoom initialization."""
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        loom = ContextLoom(mock_connector, "SELECT * FROM users")
        
        assert loom.redis_manager is None
        
        await loom.initialize()
        
        assert loom.redis_manager is not None
        mock_connector.connect.assert_called_once()

@pytest.mark.asyncio
async def test_loom_shutdown(mock_connector, mock_redis_manager):
    """Test ContextLoom shutdown."""
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        with patch("core.memory_manager.RedisManager.close", new=AsyncMock()) as mock_close:
            loom = ContextLoom(mock_connector, "SELECT * FROM users")
            await loom.initialize()
            
            await loom.shutdown()
            
            mock_close.assert_called_once()
            mock_connector.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_loom_auto_initialize(mock_connector, mock_redis_manager):
    """Test ContextLoom auto-initialization on sync."""
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        loom = ContextLoom(mock_connector, "SELECT * FROM users WHERE id = :session_id")
        
        # Mock Redis returning None (Cold Start)
        mock_redis_manager.load_context.return_value = None
        mock_connector.fetch.return_value = {"user": "alice"}
        
        # Should auto-initialize on first sync call
        state = await loom.sync("user_123")
        
        assert loom.redis_manager is not None
        mock_connector.connect.assert_called_once()
        assert state.session_id == "user_123"
