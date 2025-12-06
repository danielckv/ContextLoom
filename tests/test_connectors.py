"""Tests for connectors."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from connectors.postgres import PostgresConnector

@pytest.mark.asyncio
async def test_postgres_connector_fetch():
    """Test fetching data using PostgresConnector."""
    connector = PostgresConnector("postgresql://user:pass@localhost/db")
    # Mock the database attribute
    connector.database = AsyncMock()
    # fetch_one returns a Record-like object (can be dict-like)
    connector.database.fetch_one.return_value = {"id": 1, "name": "Test"}

    await connector.connect()
    connector.database.connect.assert_called_once()

    result = await connector.fetch("SELECT * FROM users")

    assert result == {"id": 1, "name": "Test"}
    connector.database.fetch_one.assert_called_with(query="SELECT * FROM users")

    await connector.disconnect()
    connector.database.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_postgres_connector_fetch_no_result():
    """Test fetching data when no result is found."""
    connector = PostgresConnector("postgresql://user:pass@localhost/db")
    connector.database = AsyncMock()
    connector.database.fetch_one.return_value = None

    result = await connector.fetch("SELECT * FROM users")

    assert result == {}
