"""DSPy Hook for ContextLoom."""

import dspy
import asyncio
import logging
import concurrent.futures
from typing import Type, Any, Optional
from core.memory_manager import RedisManager
from core.exceptions import CycleDetectedError
from models.schema import ContextState

logger = logging.getLogger(__name__)

def dspy_hook(signature: Type[dspy.Signature]) -> Type[dspy.Module]:
    """Creates a Context-Aware DSPy Predictor from a Signature.

    Args:
        signature: The DSPy signature to use.

    Returns:
        Type[dspy.Module]: A class inheriting from dspy.Predictor that injects context.
    """

    class ContextAwarePredictor(dspy.Predict):
        """Predictor that injects ContextLoom state."""

        def __init__(self, **kwargs):
            # Pass arguments to dspy.Predict (it takes signature as first arg)
            super().__init__(signature, **kwargs)

        def forward(self, **kwargs) -> Any:
            """Forward pass that injects context.
            
            Note: This method is synchronous to match dspy.Predict.forward,
            but it needs to load context from Redis asynchronously.
            We use _run_async helper to bridge sync/async boundary.
            """
            session_id = kwargs.get("session_id")

            if session_id:
                # Load context synchronously by running async code
                self._inject_context_sync(session_id, kwargs)

            # Call super().forward - this is synchronous
            return super().forward(**kwargs)
        
        def _inject_context_sync(self, session_id: str, kwargs: dict) -> None:
            """Helper to inject context by running async code synchronously."""
            try:
                self._run_async(self._inject_context_async(session_id, kwargs))
            except Exception as e:
                # Log error but don't crash
                logger.error(f"ContextLoom Error in dspy_hook: {e}", exc_info=True)
        
        async def _inject_context_async(self, session_id: str, kwargs: dict) -> None:
            """Async implementation of context injection."""
            manager = await RedisManager.get_instance()
            state = await manager.load_context(session_id)

            if state:
                # Check for cycles
                cycle_warning = ""
                if state.is_cycle_detected():
                    cycle_warning = "\nWARNING: Cycle detected! You are repeating a previous state. Pivot your strategy."

                # Inject context
                if 'context' in self.signature.input_fields:
                    context_str = f"Static Data: {state.static_data}\nDynamic State: {state.dynamic_state}"
                    if cycle_warning:
                        context_str += cycle_warning

                    # Prepend/Append to existing context if any
                    current_context = kwargs.get('context', "")
                    kwargs['context'] = f"{context_str}\n{current_context}".strip()
        
        def _run_async(self, coro):
            """Helper to run async code from sync context.
            
            Note: This is a necessary bridge between the synchronous dspy.Predict.forward
            and our async Redis operations. While using ThreadPoolExecutor for running
            async code is not ideal, it's required when the event loop is already running
            (which can happen in async test contexts or when DSPy is called from async code).
            """
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Event loop is running, we need to run async code in a separate thread
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, coro)
                        return future.result()
                else:
                    return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)

    return ContextAwarePredictor
