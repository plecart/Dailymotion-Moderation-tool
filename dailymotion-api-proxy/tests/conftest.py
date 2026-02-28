"""Test configuration and fixtures."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    cache_store = {}

    async def mock_get(key):
        return cache_store.get(key)

    async def mock_set(key, value, ex=None):
        cache_store[key] = value

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.set = mock_set

    with patch("src.cache.redis_client._redis_client", mock_client):
        yield mock_client
        cache_store.clear()


@pytest.fixture
async def mock_http_client():
    """Mock HTTP client for testing."""
    mock_client = AsyncMock()
    with patch("src.clients.dailymotion_client._http_client", mock_client):
        yield mock_client


@pytest.fixture
async def client(mock_redis, mock_http_client) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with mocked dependencies.

    Patches create_redis_client and create_http_client in src.main (where they are
    imported) with AsyncMock to prevent lifespan from overwriting mocked clients if
    lifespan executes. Uses AsyncMock explicitly to ensure awaitable return values.
    Also patches close functions to prevent cleanup issues.
    """
    with patch(
        "src.main.create_redis_client", new=AsyncMock()
    ), patch(
        "src.main.create_http_client", new=AsyncMock()
    ), patch(
        "src.main.close_redis_client", new=AsyncMock()
    ), patch(
        "src.main.close_http_client", new=AsyncMock()
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
