"""Database connection pool management using asyncpg."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from src.config import settings

logger = logging.getLogger(__name__)

# Per-event-loop state so the same module works with pytest (new loop per test) and the app.
_pools: dict[asyncio.AbstractEventLoop, asyncpg.Pool] = {}
_locks: dict[asyncio.AbstractEventLoop, asyncio.Lock] = {}


def _get_lock(loop: asyncio.AbstractEventLoop) -> asyncio.Lock:
    """Return the lock for the given loop, creating it if needed."""
    if loop not in _locks:
        _locks[loop] = asyncio.Lock()
    return _locks[loop]


async def create_pool() -> asyncpg.Pool:
    """Create and return the database connection pool. Safe to call concurrently and across event loops (e.g. pytest)."""
    loop = asyncio.get_running_loop()
    if loop in _pools:
        return _pools[loop]
    lock = _get_lock(loop)
    async with lock:
        if loop in _pools:
            return _pools[loop]
        logger.info("Creating database connection pool")
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
        _pools[loop] = pool
        logger.info("Database connection pool created")
        return pool


async def close_pool() -> None:
    """Close the database connection pool for the current event loop. Safe to call concurrently with create_pool."""
    loop = asyncio.get_running_loop()
    lock = _get_lock(loop)
    async with lock:
        if loop in _pools:
            logger.info("Closing database connection pool")
            await _pools[loop].close()
            del _pools[loop]
            del _locks[loop]
            logger.info("Database connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Get the current connection pool for the running event loop. Raises if not initialized."""
    loop = asyncio.get_running_loop()
    if loop not in _pools:
        raise RuntimeError("Database pool not initialized. Call create_pool() first.")
    return _pools[loop]


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool as an async context manager."""
    pool = get_pool()
    async with pool.acquire() as connection:
        yield connection
