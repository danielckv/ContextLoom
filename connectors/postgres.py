"""PostgreSQL Connector implementation."""

from typing import Dict, Any
from databases import Database
from connectors.base import BaseConnector

class PostgresConnector(BaseConnector):
    """Connector for PostgreSQL databases.

    Attributes:
        database: The Database instance.
    """

    def __init__(self, connection_string: str):
        """Initializes the PostgresConnector.

        Args:
            connection_string: The database connection string.
        """
        self.database = Database(connection_string)

    async def connect(self):
        """Establishes connection to the database."""
        await self.database.connect()

    async def disconnect(self):
        """Closes the connection to the database."""
        await self.database.disconnect()

    async def fetch(self, query: str, values: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fetches a single record based on the provided SQL query.

        Args:
            query: The SQL query to execute (supports :param_name style placeholders).
            values: Optional dictionary of parameter values for parameterized queries.

        Returns:
            Dict[str, Any]: The result as a dictionary. Returns an empty dict if no result found.
        """
        if values:
            record = await self.database.fetch_one(query=query, values=values)
        else:
            record = await self.database.fetch_one(query=query)
        if record:
            return dict(record)
        return {}
