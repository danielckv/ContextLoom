"""DSPy Hook for ContextLoom."""

import dspy
import asyncio
from typing import Type, Any, Optional
from core.memory_manager import RedisManager
from core.exceptions import CycleDetectedError
from models.schema import ContextState

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

        async def forward(self, **kwargs) -> Any:
            """Async forward pass that injects context."""
            session_id = kwargs.get("session_id")

            if session_id:
                try:
                    manager = await RedisManager.get_instance()
                    state = await manager.load_context(session_id)

                    if state:
                        # Check for cycles
                        cycle_warning = ""
                        if state.is_cycle_detected():
                            # "Ensure it handles the CycleDetectedError gracefully by appending a warning string to the prompt."
                            cycle_warning = "\nWARNING: Cycle detected! You are repeating a previous state. Pivot your strategy."

                        # Inject context
                        # We look for a field named 'context' in the signature.
                        if 'context' in self.signature.input_fields:
                            # Format context from static and dynamic state
                            # We use model_dump_json or similar for clean output?
                            # Using str() for now as per simple requirement.
                            context_str = f"Static Data: {state.static_data}\nDynamic State: {state.dynamic_state}"
                            if cycle_warning:
                                context_str += cycle_warning

                            # Prepend/Append to existing context if any
                            current_context = kwargs.get('context', "")
                            kwargs['context'] = f"{context_str}\n{current_context}".strip()

                except Exception as e:
                    # Log error but don't crash
                    print(f"ContextLoom Error in dspy_hook: {e}")

            # Call super().forward.
            # We assume the user awaits this method.
            return super().forward(**kwargs)

    return ContextAwarePredictor
