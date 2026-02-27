"""SQL migration runner for numbered .sql files."""

import logging
from pathlib import Path

import asyncpg

from src.database.connection import get_connection

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations() -> None:
    """Execute all pending SQL migrations in order.

    Migrations are .sql files named with a numeric prefix (e.g., 001_create_table.sql).
    A migrations tracking table records which migrations have been applied.
    Uses a single connection for the whole run.
    """
    async with get_connection() as conn:
        await _ensure_migrations_table(conn)
        applied = await _get_applied_migrations(conn)
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        for migration_file in migration_files:
            migration_name = migration_file.name
            if migration_name in applied:
                logger.debug("Migration %s already applied, skipping", migration_name)
                continue

            logger.info("Applying migration: %s", migration_name)
            sql = migration_file.read_text(encoding="utf-8")

            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO _migrations (name) VALUES ($1)",
                    migration_name,
                )

            applied.add(migration_name)
            logger.info("Migration %s applied successfully", migration_name)


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
