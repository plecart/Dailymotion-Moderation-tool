"""FastAPI dependency injection for database connections."""

from typing import AsyncGenerator

import asyncpg

from src.database.connection import get_connection


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency to provide a database connection to route handlers."""
    async with get_connection() as conn:
        yield conn
