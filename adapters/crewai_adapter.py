"""CrewAI Adapter for ContextLoom."""

import asyncio
from typing import Any, Dict, Optional
from core.memory_manager import RedisManager

class ContextLoomCrewStorage:
    """Storage handler for CrewAI that pushes to Redis.

    This class is designed to replace standard CrewAI memory storage.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    def save(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Saves task output to Redis dynamic_state.

        Args:
            value: The data to save (Task Output).
            metadata: Optional metadata.
        """
        self._run_async(self._save_async(value))

    def add(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Alias for save, as some interfaces use add."""
        self.save(value, metadata)

    async def _save_async(self, value: Any):
        """Async implementation of save."""
        try:
            manager = await RedisManager.get_instance()
            state = await manager.load_context(self.session_id)
            if not state:
                # If state doesn't exist, we can't save to it.
                return

            # Update dynamic_state
            # We append to 'task_outputs' list in dynamic_state
            if 'task_outputs' not in state.dynamic_state:
                state.dynamic_state['task_outputs'] = []

            # Ensure it is a list
            if not isinstance(state.dynamic_state['task_outputs'], list):
                 state.dynamic_state['task_outputs'] = []

            state.dynamic_state['task_outputs'].append(str(value))

            await manager.save_context(state)
        except Exception as e:
            print(f"ContextLoom Error in CrewAI Storage: {e}")

    def _run_async(self, coro):
        """Helper to run async code from sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we cannot block.
                # Use create_task to run in background.
                asyncio.create_task(coro)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
             asyncio.run(coro)
