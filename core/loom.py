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
        # Format the query with the session_id
        try:
            query = self.query_template.format(session_id=session_id)
        except KeyError:
            # Fallback if template doesn't use session_id or uses other keys
            # We assume the template is correct for the use case
            query = self.query_template

        # Fetch data
        static_data = await self.connector.fetch(query)

        # Create new state
        state = ContextState(
            session_id=session_id,
            static_data=static_data,
            dynamic_state={}
        )

        # 3. Save to Redis
        await self.redis_manager.save_context(state)

        return state
