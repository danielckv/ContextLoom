"""Tests for Adapters."""

import pytest
import asyncio
import dspy
from unittest.mock import AsyncMock, patch
from adapters.dspy_hook import dspy_hook
from adapters.crewai_adapter import ContextLoomCrewStorage
from models.schema import ContextState

class TestSig(dspy.Signature):
    """Test Signature."""
    query = dspy.InputField()
    context = dspy.InputField()
    answer = dspy.OutputField()

@pytest.fixture
def mock_redis_manager():
    manager = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_dspy_hook_injection(mock_redis_manager):
    """Test that context is injected into DSPy signature."""
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        # Setup state
        state = ContextState(
            session_id="test_dspy",
            static_data={"user": "bob"},
            dynamic_state={"last_action": "search"}
        )
        mock_redis_manager.load_context.return_value = state

        # Create predictor
        AdaptedPredictor = dspy_hook(TestSig)
        predictor = AdaptedPredictor()

        # Mock super().forward using patch on dspy.Predict
        # Since AdaptedPredictor inherits from dspy.Predict, we patch dspy.Predict.forward
        with patch("dspy.Predict.forward", return_value="mock_answer") as mock_forward:
            predictor.forward(query="hello", session_id="test_dspy")

            # Verify kwargs passed to super().forward
            args, kwargs = mock_forward.call_args
            assert 'context' in kwargs
            assert "Static Data: {'user': 'bob'}" in kwargs['context']
            assert "Dynamic State: {'last_action': 'search'}" in kwargs['context']

@pytest.mark.asyncio
async def test_dspy_hook_cycle_warning(mock_redis_manager):
    """Test that cycle warning is appended when cycle detected."""
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        # Setup state with cycle
        state = ContextState(session_id="test_cycle", dynamic_state={"a": 1})
        # Add current hash to history to simulate cycle (must appear >1 times)
        h = state.calculate_hash()
        state.cycle_history.append(h)
        state.cycle_history.append(h)

        mock_redis_manager.load_context.return_value = state

        AdaptedPredictor = dspy_hook(TestSig)
        predictor = AdaptedPredictor()

        with patch("dspy.Predict.forward", return_value="mock_answer") as mock_forward:
            predictor.forward(query="hello", session_id="test_cycle")

            args, kwargs = mock_forward.call_args
            assert "WARNING: Cycle detected!" in kwargs['context']

@pytest.mark.asyncio
async def test_crewai_storage(mock_redis_manager):
    """Test CrewAI storage adapter."""
    with patch("core.memory_manager.RedisManager.get_instance", new=AsyncMock(return_value=mock_redis_manager)):
        state = ContextState(session_id="test_crew", dynamic_state={})
        mock_redis_manager.load_context.return_value = state

        storage = ContextLoomCrewStorage(session_id="test_crew")

        # Test save
        # Since we are in an async test loop, storage.save will allow the task to be scheduled.
        storage.save("Task Result")

        # Allow background task to run
        await asyncio.sleep(0.1)

        mock_redis_manager.save_context.assert_called_once()
        saved_state = mock_redis_manager.save_context.call_args[0][0]
        assert saved_state.dynamic_state['task_outputs'] == ["Task Result"]
