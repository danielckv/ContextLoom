"""Tests for the schema models."""

import pytest
from models.schema import ContextState

def test_context_state_calculate_hash():
    """Test that calculate_hash produces consistent hashes for identical states."""
    state1 = ContextState(
        session_id="test_session",
        dynamic_state={"a": 1, "b": 2}
    )

    state2 = ContextState(
        session_id="test_session",
        dynamic_state={"b": 2, "a": 1} # Different order
    )

    state3 = ContextState(
        session_id="test_session",
        dynamic_state={"a": 1, "b": 3} # Different value
    )

    # Hashes should be identical despite key order in definition
    assert state1.calculate_hash() == state2.calculate_hash()

    # Hashes should differ for different content
    assert state1.calculate_hash() != state3.calculate_hash()

def test_context_state_default_values():
    """Test default values for ContextState."""
    state = ContextState(session_id="new_session")
    assert state.static_data == {}
    assert state.dynamic_state == {}
    assert state.cycle_history == []
