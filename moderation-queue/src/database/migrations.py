"""SQL migration runner for numbered .sql files."""

import asyncio
import logging
from pathlib import Path

import asyncpg

from src.config import settings
from src.database.connection import get_connection

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class MigrationLockTimeoutError(RuntimeError):
    """Raised when the migration advisory lock cannot be acquired within the configured timeout."""


async def run_migrations() -> None:
    """Execute all pending SQL migrations in order.

    Migrations are .sql files named with a numeric prefix (e.g., 001_create_table.sql).
    A migrations tracking table records which migrations have been applied.
    Uses a single connection for the whole run.
    Holds a PostgreSQL advisory lock for the duration so only one runner applies migrations at a time.
    Fails with MigrationLockTimeoutError if the lock cannot be acquired within migration_lock_timeout_seconds.
    """
    async with get_connection() as conn:
        await _ensure_migrations_table(conn)
        await _acquire_migration_lock(conn)
        try:
            applied = await _get_applied_migrations(conn)
            migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

            for migration_file in migration_files:
                migration_name = migration_file.name
                if migration_name in applied:
                    logger.debug("Migration %s already applied, skipping", migration_name)
                    continue

                logger.info("Applying migration: %s", migration_name)
                await _apply_migration(conn, migration_file, migration_name)
                applied.add(migration_name)
                logger.info("Migration %s applied successfully", migration_name)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", settings.migration_lock_key)


async def _acquire_migration_lock(conn: asyncpg.Connection) -> None:
    """Acquire the migration advisory lock with retries; raise MigrationLockTimeoutError if timeout."""
    loop = asyncio.get_running_loop()
    timeout_seconds = settings.migration_lock_timeout_seconds
    deadline = loop.time() + timeout_seconds
    while True:
        acquired = await conn.fetchval(
            "SELECT pg_try_advisory_lock($1)",
            settings.migration_lock_key,
        )
        if acquired:
            return
        if loop.time() >= deadline:
            raise MigrationLockTimeoutError(
                f"Could not acquire migration lock within {timeout_seconds}s. "
                "Another process may be running or stuck on migrations."
            )
        await asyncio.sleep(1)


async def _ensure_migrations_table(conn: asyncpg.Connection) -> None:
    """Create the migrations tracking table if it doesn't exist."""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


async def _get_applied_migrations(conn: asyncpg.Connection) -> set[str]:
    """Return set of migration names that have already been applied."""
    rows = await conn.fetch("SELECT name FROM _migrations")
    return {row["name"] for row in rows}


async def _apply_migration(
    conn: asyncpg.Connection,
    migration_file: Path,
    migration_name: str,
) -> None:
    """Execute a single migration file and record it in _migrations."""
    sql = migration_file.read_text(encoding="utf-8")
    async with conn.transaction():
        await conn.execute(sql)
        await conn.execute(
            "INSERT INTO _migrations (name) VALUES ($1)",
            migration_name,
        )
