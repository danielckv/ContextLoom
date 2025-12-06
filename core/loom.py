"""ContextLoom Main Class.

This module defines the ContextLoom middleware, which manages context synchronization
between Redis and external databases (Cold Start Hydration).
"""

from typing import Optional
from core.memory_manager import RedisManager
from connectors.base import BaseConnector
from models.schema import ContextState

class ContextLoom:
    """The main ContextLoom middleware.

    Attributes:
        connector: The data connector for hydration.
        query_template: The SQL query template used for hydration.
        redis_manager: The RedisManager instance.
    """

    def __init__(self, connector: BaseConnector, query_template: str):
        """Initializes ContextLoom.

        Args:
            connector: An instance of a BaseConnector subclass.
            query_template: A SQL query string with a {session_id} placeholder.
        """
        self.connector = connector
        self.query_template = query_template
        self.redis_manager: Optional[RedisManager] = None

    async def initialize(self):
        """Initializes the RedisManager and Connector."""
        self.redis_manager = await RedisManager.get_instance()
        await self.connector.connect()

    async def shutdown(self):
        """Closes connections."""
        if self.redis_manager:
            await RedisManager.close()
        await self.connector.disconnect()

    async def sync(self, session_id: str) -> ContextState:
        """Synchronizes the context state for a given session.

        Checks Redis for existing state. If missing (Cold Start),
        fetches data using the connector and hydrates Redis.

        Args:
            session_id: The unique session identifier.

        Returns:
            ContextState: The current context state.
        """
        if self.redis_manager is None:
            # Auto-initialize if not done explicitly
            await self.initialize()
            if self.redis_manager is None:
                raise RuntimeError("Failed to initialize RedisManager")

        # 1. Check Redis
        state = await self.redis_manager.load_context(session_id)
        if state:
            return state

        # 2. Cold Start Hydration
        # Use parameterized query to prevent SQL injection
        # Query template should use :session_id style placeholder
        try:
            # Check if the template contains the session_id placeholder
            if ':session_id' in self.query_template:
                # Use parameterized query
                static_data = await self.connector.fetch(
                    self.query_template,
                    values={'session_id': session_id}
                )
            elif '{session_id}' in self.query_template:
                # Template uses old format, raise error for security
                raise ValueError(
                    "Query template uses unsafe {session_id} placeholder. "
                    "Please use :session_id for parameterized queries instead."
                )
            else:
                # No placeholder, use query as-is
                static_data = await self.connector.fetch(self.query_template)
        except ValueError:
            # Re-raise ValueError for template issues
            raise

        # Create new state
        state = ContextState(
            session_id=session_id,
            static_data=static_data,
            dynamic_state={}
        )

        # 3. Save to Redis
        await self.redis_manager.save_context(state)

        return state
