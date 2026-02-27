"""Database connection pool management using asyncpg."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from src.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def create_pool() -> asyncpg.Pool:
    """Create and return the database connection pool. Safe to call concurrently."""
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is not None:
            return _pool
        logger.info("Creating database connection pool")
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
        logger.info("Database connection pool created")
        return _pool


async def close_pool() -> None:
    """Close the database connection pool. Safe to call concurrently with create_pool."""
    global _pool
    async with _pool_lock:
        if _pool is not None:
            logger.info("Closing database connection pool")
            await _pool.close()
            _pool = None
            logger.info("Database connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Get the current connection pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call create_pool() first.")
    return _pool


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool as an async context manager."""
    pool = get_pool()
    async with pool.acquire() as connection:
        yield connection
