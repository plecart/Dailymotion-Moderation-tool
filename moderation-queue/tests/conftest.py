"""Pytest configuration and fixtures for moderation-queue tests."""

import os
from typing import AsyncGenerator

# Default DATABASE_URL for tests (localhost when Postgres runs via Docker Compose).
# Override with env var if needed.
DEFAULT_TEST_DATABASE_URL = (
    "postgresql://moderation:moderation_secret@localhost:5432/moderation_db"
)
os.environ.setdefault("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

import pytest_asyncio
import asyncpg
from httpx import ASGITransport, AsyncClient

from src.config import settings


@pytest_asyncio.fixture(scope="function")
async def db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a database connection for tests."""
    conn = await asyncpg.connect(dsn=settings.database_url)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="function")
async def clean_db(db_connection: asyncpg.Connection):
    """Clean database tables before each test."""
    await db_connection.execute("DELETE FROM moderation_logs")
    await db_connection.execute("DELETE FROM videos")
    yield


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing FastAPI endpoints."""
    from src.main import app
    from src.database.connection import create_pool, close_pool
    from src.database.migrations import run_migrations

    await create_pool()
    await run_migrations()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    await close_pool()
