"""Tests for database connection and migrations."""

import asyncpg
import pytest
import pytest_asyncio

from src.database.connection import create_pool, close_pool, get_pool, get_connection
from src.database.migrations import run_migrations

# Tables created by migrations; drop in this order (FK: moderation_logs -> videos).
_MIGRATION_TABLES_DROP_ORDER = ("moderation_logs", "videos", "_migrations")


async def _table_exists(conn: asyncpg.Connection, table_name: str) -> bool:
    """Return True if a table exists in the public schema."""
    return await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = $1
        )
        """,
        table_name,
    )


class TestDatabaseConnection:
    """Tests for database connection pool management."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_and_teardown(self):
        """Ensure pool is closed before and after each test."""
        await close_pool()
        yield
        await close_pool()

    async def test_create_pool_returns_pool(self):
        """Test that create_pool creates and returns a connection pool."""
        pool = await create_pool()

        assert pool is not None
        assert isinstance(pool, asyncpg.Pool)

    async def test_get_pool_returns_same_pool(self):
        """Test that get_pool returns the same pool instance."""
        pool1 = await create_pool()
        pool2 = get_pool()

        assert pool1 is pool2

    async def test_get_pool_raises_when_not_initialized(self):
        """Test that get_pool raises RuntimeError when pool not created."""
        with pytest.raises(RuntimeError, match="Database pool not initialized"):
            get_pool()

    async def test_get_connection_provides_working_connection(self):
        """Test that get_connection provides a working database connection."""
        await create_pool()

        async with get_connection() as conn:
            result = await conn.fetchval("SELECT 1")

        assert result == 1

    async def test_close_pool_closes_connection(self):
        """Test that close_pool properly closes the pool."""
        await create_pool()
        await close_pool()

        with pytest.raises(RuntimeError):
            get_pool()


class TestMigrations:
    """Tests for SQL migration system."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_pool(self):
        """Create pool before tests and clean up after."""
        await create_pool()
        yield
        await close_pool()

    @pytest_asyncio.fixture(autouse=True)
    async def reset_migration_tables(self, setup_pool):
        """Drop migration-related tables before each test so run_migrations() runs from scratch."""
        async with get_connection() as conn:
            for table in _MIGRATION_TABLES_DROP_ORDER:
                await conn.execute(f"DROP TABLE IF EXISTS {table}")
        yield

    async def test_run_migrations_creates_tables(self):
        """Test that migrations create the expected tables."""
        await run_migrations()

        async with get_connection() as conn:
            assert await _table_exists(conn, "videos") is True
            assert await _table_exists(conn, "moderation_logs") is True

    async def test_run_migrations_is_idempotent(self):
        """Test that running migrations multiple times is safe."""
        await run_migrations()
        await run_migrations()  # Should not raise

        async with get_connection() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM _migrations")

        assert count >= 2  # At least our two migrations

    async def test_migrations_tracking_table_exists(self):
        """Test that the migrations tracking table is created."""
        await run_migrations()

        async with get_connection() as conn:
            assert await _table_exists(conn, "_migrations") is True
