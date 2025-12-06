"""DSPy Hook for ContextLoom."""

import logging
import dspy
from typing import Type, Any
from core.memory_manager import RedisManager

logger = logging.getLogger(__name__)

def dspy_hook(signature: Type[dspy.Signature]) -> Type[dspy.Predict]:
    """Creates a Context-Aware DSPy Predictor from a Signature.

    Args:
        signature: The DSPy signature to use.

    Returns:
        Type[dspy.Predict]: A class inheriting from dspy.Predict that injects context.
    """

    class ContextAwarePredictor(dspy.Predict):
        """Predictor that injects ContextLoom state."""

        def __init__(self, **kwargs):
            # Pass arguments to dspy.Predict (it takes signature as first arg)
            super().__init__(signature, **kwargs)

        def forward(self, **kwargs) -> Any:
            """Forward pass that injects context synchronously.
            
            Note: This method is synchronous because dspy.Predict.forward is synchronous.
            Context fetching is handled asynchronously but we can't await here.
            """
            session_id = kwargs.get("session_id")

            if session_id:
                try:
                    # Since we can't use async/await in a sync context, we would need
                    # to handle this differently in production. For now, we maintain
                    # the sync signature to match dspy.Predict.forward()
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Can't run async code in a running loop synchronously
                            logger.warning("Cannot fetch context in running event loop")
                        else:
                            state = loop.run_until_complete(self._fetch_context(session_id))
                            if state:
                                self._inject_context(state, kwargs)
                    except RuntimeError:
                        # No event loop
                        state = asyncio.run(self._fetch_context(session_id))
                        if state:
                            self._inject_context(state, kwargs)

                except Exception as e:
                    # Log error but don't crash
                    logger.error(f"ContextLoom Error in dspy_hook: {e}")

            # Call super().forward (synchronous)
            return super().forward(**kwargs)
        
        async def _fetch_context(self, session_id: str):
            """Fetches context state from Redis.
            
            Args:
                session_id: The session identifier.
                
            Returns:
                The context state or None.
            """
            manager = await RedisManager.get_instance()
            return await manager.load_context(session_id)
        
        def _inject_context(self, state, kwargs: dict):
            """Injects context into kwargs.
            
            Args:
                state: The context state.
                kwargs: The keyword arguments to inject context into.
            """
            # Check for cycles
            cycle_warning = ""
            if state.is_cycle_detected():
                # Append a warning string to handle cycles gracefully
                cycle_warning = "\nWARNING: Cycle detected! You are repeating a previous state. Pivot your strategy."

            # Inject context - check if 'context' field exists in signature
            if hasattr(self.signature, 'input_fields') and 'context' in self.signature.input_fields:
                # Format context from static and dynamic state
                context_str = f"Static Data: {state.static_data}\nDynamic State: {state.dynamic_state}"
                if cycle_warning:
                    context_str += cycle_warning

                # Prepend/Append to existing context if any
                current_context = kwargs.get('context', "")
                kwargs['context'] = f"{context_str}\n{current_context}".strip()

    return ContextAwarePredictor
