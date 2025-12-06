"""Schema definitions for ContextLoom.

This module defines the core data models used throughout the application,
specifically the ContextState model which holds the session state.
"""

import hashlib
import json
from typing import Dict, List, Any
from pydantic import BaseModel, Field

class ContextState(BaseModel):
    """Represents the state of a context session.

    Attributes:
        session_id: Unique identifier for the session.
        static_data: Data that does not change frequently (e.g., user profile).
        dynamic_state: The evolving state of the conversation or task.
        cycle_history: A list of recent state hashes to detect loops.
    """
    session_id: str
    static_data: Dict[str, Any] = Field(default_factory=dict)
    dynamic_state: Dict[str, Any] = Field(default_factory=dict)
    cycle_history: List[str] = Field(default_factory=list)

    def calculate_hash(self) -> str:
        """Computes a SHA256 hash of the current dynamic_state.

        The dynamic_state is serialized using Pydantic's model_dump(mode='json')
        to handle complex types, and then to a JSON string with sorted keys
        to ensure consistent hashing for identical states.

        Returns:
            str: The hexadecimal SHA256 hash of the dynamic_state.
        """
        # Get a JSON-safe dictionary representation of dynamic_state
        # using model_dump to handle complex types (e.g. datetime)
        data = self.model_dump(mode='json', include={'dynamic_state'})['dynamic_state']

        # Serialize to JSON with sorted keys for consistency
        state_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(state_str.encode("utf-8")).hexdigest()
