"""Base class for Connectors.

This module defines the abstract base class for all data connectors.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseConnector(ABC):
    """Abstract base class for data connectors."""

    @abstractmethod
    async def connect(self):
        """Establishes connection to the data source."""
        pass

    @abstractmethod
    async def disconnect(self):
        """Closes the connection to the data source."""
        pass

    @abstractmethod
    async def fetch(self, query: str) -> Dict[str, Any]:
        """Fetches data based on the provided query.

        Args:
            query: The query string (e.g., SQL or entity ID) used to fetch data.

        Returns:
            Dict[str, Any]: A dictionary containing the fetched results.
        """
        pass
