"""Tests for the Memory Manager."""

import pytest
import pytest_asyncio
from core.memory_manager import RedisManager
from models.schema import ContextState
from fakeredis import aioredis

@pytest_asyncio.fixture
async def redis_manager():
    """Fixture to provide a RedisManager with a fake redis client."""
    # Reset singleton
    RedisManager._instance = None

    # Create an instance (doesn't matter what URL we pass if we replace client immediately)
    # But get_instance tries to create a client.
    # We can mock redis.from_url or just let it fail/create and then overwrite.
    # Better to just instantiate manually to avoid side effects?
    # But we want to test get_instance logic too?
    # Let's just manually construct for the test to ensure isolation.

    manager = RedisManager() # calls __new__
    # Manually init client
    manager._client = aioredis.FakeRedis(decode_responses=True)
    RedisManager._instance = manager

    yield manager

    # Cleanup
    if manager._client:
        await manager._client.aclose()
    RedisManager._instance = None

@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that RedisManager behaves as a singleton."""
    RedisManager._instance = None # Ensure clean start

    m1 = await RedisManager.get_instance()
    m2 = await RedisManager.get_instance()

    assert m1 is m2

    # Clean up
    await RedisManager.close()

@pytest.mark.asyncio
async def test_save_and_load_context(redis_manager):
    """Test saving and loading context."""
    session_id = "test_session_1"
    state = ContextState(
        session_id=session_id,
        dynamic_state={"step": 1},
        static_data={"user": "alice"}
    )

    await redis_manager.save_context(state)

    loaded_state = await redis_manager.load_context(session_id)

    assert loaded_state is not None
    assert loaded_state.session_id == session_id
    assert loaded_state.dynamic_state == {"step": 1}
    assert loaded_state.static_data == {"user": "alice"}

    # Verify cycle history updated
    assert len(loaded_state.cycle_history) == 1
    assert loaded_state.cycle_history[0] == state.calculate_hash()

@pytest.mark.asyncio
async def test_cycle_history_limit(redis_manager):
    """Test that cycle history is limited to 5 entries."""
    session_id = "test_session_loop"
    state = ContextState(session_id=session_id)

    # Save 6 times
    for i in range(6):
        state.dynamic_state = {"step": i}
        await redis_manager.save_context(state)

    loaded_state = await redis_manager.load_context(session_id)

    # History should be capped at 5
    assert len(loaded_state.cycle_history) == 5
    # The most recent hash should be first (LIFO/LPUSH)
    # The last state was step=5
    state.dynamic_state = {"step": 5}
    assert loaded_state.cycle_history[0] == state.calculate_hash()

@pytest.mark.asyncio
async def test_load_nonexistent_session(redis_manager):
    """Test loading a session that does not exist."""
    loaded_state = await redis_manager.load_context("nonexistent")
    assert loaded_state is None
