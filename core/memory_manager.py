"""Memory Manager for ContextLoom.

This module handles interactions with Redis for state persistence.
It implements the Singleton pattern to manage connection pools efficiently.
"""

import asyncio
import json
from typing import Optional, List
import redis.asyncio as redis
from models.schema import ContextState

class RedisManager:
    """Async Redis Manager implementing Singleton pattern.

    Attributes:
        _instance: The singleton instance.
        _client: The Redis client.
    """
    _instance: Optional["RedisManager"] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def get_instance(cls, url: str = "redis://localhost:6379") -> "RedisManager":
        """Returns the singleton instance of RedisManager.

        Args:
            url: The Redis connection URL.

        Returns:
            RedisManager: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = cls()

        if cls._instance._client is None:
             # redis.from_url handles connection pooling automatically
            cls._instance._client = redis.from_url(url, decode_responses=True)

        return cls._instance

    @classmethod
    async def close(cls):
        """Closes the Redis connection."""
        if cls._instance and cls._instance._client:
            await cls._instance._client.aclose()
            cls._instance._client = None

    async def save_context(self, state: ContextState) -> None:
        """Saves the context state to Redis atomically using a pipeline.

        This method updates the state and the cycle history list.

        Args:
            state: The ContextState object to save.

        Raises:
            RuntimeError: If Redis client is not initialized.
        """
        if self._client is None:
            raise RuntimeError("Redis client is not initialized. Call get_instance first.")

        state_key = f"Loom:Context:{state.session_id}"
        history_key = f"Loom:CycleHistory:{state.session_id}"

        current_hash = state.calculate_hash()

        # Start pipeline for atomic operation
        async with self._client.pipeline(transaction=True) as pipe:
            # 1. Save the full state.
            await pipe.set(state_key, state.model_dump_json())

            # 2. Update Cycle History
            # Push new hash to the left
            await pipe.lpush(history_key, current_hash)
            # Trim to keep only last 5 entries
            await pipe.ltrim(history_key, 0, 4)

            await pipe.execute()

    async def load_context(self, session_id: str) -> Optional[ContextState]:
        """Loads the context state from Redis.

        Args:
            session_id: The session ID to load.

        Returns:
            Optional[ContextState]: The loaded ContextState or None if not found.

        Raises:
            RuntimeError: If Redis client is not initialized.
        """
        if self._client is None:
             raise RuntimeError("Redis client is not initialized. Call get_instance first.")

        state_key = f"Loom:Context:{session_id}"
        history_key = f"Loom:CycleHistory:{session_id}"

        data = await self._client.get(state_key)
        if not data:
            return None

        # Reconstruct the model
        state = ContextState.model_validate_json(data)

        # Populate cycle_history from the Redis List
        history = await self._client.lrange(history_key, 0, -1)
        state.cycle_history = history

        return state

    async def get_client(self) -> redis.Redis:
        """Returns the underlying Redis client."""
        if self._client is None:
            raise RuntimeError("Redis client is not initialized.")
        return self._client
