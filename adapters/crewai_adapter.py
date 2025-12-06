"""CrewAI Adapter for ContextLoom."""

import asyncio
import logging
from typing import Any, Dict, Optional
from core.memory_manager import RedisManager

logger = logging.getLogger(__name__)

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
            logger.error(f"ContextLoom Error in CrewAI Storage: {e}")

    def _run_async(self, coro):
        """Runs an async coroutine from a synchronous context, handling event loop state.

        This helper bridges synchronous and asynchronous code execution. If an event loop is
        already running (e.g., in an async environment), it schedules the coroutine as a background
        task using `asyncio.create_task` with proper error handling. If no event loop is running,
        it starts one and runs the coroutine to completion. If a `RuntimeError` occurs (e.g., no
        event loop in the current thread), it falls back to `asyncio.run`.

        Args:
            coro: The coroutine to execute.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we cannot block.
                # Create task with error handling callback
                task = asyncio.create_task(coro)
                task.add_done_callback(self._handle_task_exception)
            else:
                loop.run_until_complete(coro)
        except RuntimeError:
            asyncio.run(coro)
    
    def _handle_task_exception(self, task: asyncio.Task):
        """Handles exceptions from background tasks.
        
        Args:
            task: The completed task to check for exceptions.
        """
        try:
            task.result()
        except Exception as e:
            logger.error(f"Error in background task: {e}")
