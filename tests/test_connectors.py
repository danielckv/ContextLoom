"""Tests for connectors."""

import pytest
from unittest.mock import AsyncMock
from connectors.postgres import PostgresConnector

@pytest.mark.asyncio
async def test_postgres_connector_fetch():
    """Test fetching data using PostgresConnector."""
    connector = PostgresConnector("postgresql://user:pass@localhost/db")
    
    # Test connection
    mock_database = AsyncMock()
    # fetch_one returns a Record-like object (can be dict-like)
    mock_database.fetch_one.return_value = {"id": 1, "name": "Test"}
    connector.database = mock_database
    
    await connector.connect()
    mock_database.connect.assert_called_once()

    result = await connector.fetch("SELECT * FROM users")

    assert result == {"id": 1, "name": "Test"}
    mock_database.fetch_one.assert_called_with(query="SELECT * FROM users")

    await connector.disconnect()
    mock_database.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_postgres_connector_fetch_no_result():
    """Test fetching data when no result is found."""
    connector = PostgresConnector("postgresql://user:pass@localhost/db")
    connector.database = AsyncMock()
    connector.database.fetch_one.return_value = None

    await connector.connect()
    connector.database.connect.assert_called_once()

    result = await connector.fetch("SELECT * FROM users")

    assert result == {}
