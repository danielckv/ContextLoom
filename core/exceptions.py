"""Exceptions for ContextLoom."""

class ContextLoomError(Exception):
    """Base exception for ContextLoom."""
    pass

class CycleDetectedError(ContextLoomError):
    """Raised when a state cycle is detected."""
    pass
