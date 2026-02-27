"""Pytest configuration and fixtures for moderation-queue tests."""

import os
from typing import AsyncGenerator
from urllib.parse import urlparse

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Default test DB URL; override via env. Must be set before Settings() is loaded.
DEFAULT_TEST_DATABASE_URL = (
    "postgresql://moderation:moderation_secret@localhost:5432/moderation_db"
)
os.environ.setdefault("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

_ALLOWED_TEST_HOSTS = ("localhost", "127.0.0.1")


def _assert_test_database_url() -> None:
    """Raise if DATABASE_URL does not look like a local test DB (avoids wiping real data)."""
    url = os.environ.get("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    host = urlparse(url).hostname
    if host not in _ALLOWED_TEST_HOSTS:
        raise RuntimeError(
            f"Refusing to run tests: DATABASE_URL host is {host!r}, not in {_ALLOWED_TEST_HOSTS}. "
            "Point DATABASE_URL to localhost/127.0.0.1 to run tests."
        )


_assert_test_database_url()


@pytest_asyncio.fixture(scope="function")
async def ensure_migrations() -> AsyncGenerator[None, None]:
    """Create pool and run migrations so tables exist. Required by db_connection, clean_db, and client."""
    from src.database.connection import create_pool, close_pool
    from src.database.migrations import run_migrations

    await create_pool()
    await run_migrations()
    yield
    await close_pool()


@pytest_asyncio.fixture(scope="function")
async def db_connection(
    ensure_migrations: None,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Provide a database connection for tests. Migrations are applied first."""
    from src.config import settings

    conn = await asyncpg.connect(dsn=settings.database_url)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="function")
async def clean_db(db_connection: asyncpg.Connection) -> AsyncGenerator[None, None]:
    """Clean database tables before each test."""
    await db_connection.execute("DELETE FROM moderation_logs")
    await db_connection.execute("DELETE FROM videos")
    yield


@pytest_asyncio.fixture(scope="function")
async def client(
    ensure_migrations: None,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing FastAPI endpoints. Pool and migrations are handled by ensure_migrations."""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
