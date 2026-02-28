"""Redis client management for caching."""

import logging
from typing import Any

import redis.asyncio as redis
import redis.exceptions

from src.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def create_redis_client() -> redis.Redis:
    """Create and return Redis async client.

    Returns:
        Redis async client instance
    """
    global _redis_client
    _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Redis client created")
    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed")


def get_redis_client() -> redis.Redis:
    """Get current Redis client.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If Redis client not initialized
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return _redis_client


async def cache_get(key: str) -> str | None:
    """Get value from cache.

    Cache operations are best-effort: if Redis is unavailable or not initialized,
    returns None (cache miss) rather than raising an exception.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found or Redis error occurs
    """
    try:
        client = get_redis_client()
        value = await client.get(key)
        if value is not None:
            logger.debug("Cache hit for key: %s", key)
        else:
            logger.debug("Cache miss for key: %s", key)
        return value
    except (redis.exceptions.RedisError, RuntimeError) as exc:
        logger.warning("Redis error reading cache key '%s': %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    """Set value in cache with optional TTL.

    Cache operations are best-effort: if Redis is unavailable or not initialized,
    logs a warning but does not raise an exception to avoid failing the request.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (defaults to settings.cache_ttl_seconds)
    """
    try:
        client = get_redis_client()
        if ttl is None:
            ttl = settings.cache_ttl_seconds
        await client.set(key, value, ex=ttl)
        logger.debug("Cached key: %s with TTL: %d", key, ttl)
    except (redis.exceptions.RedisError, RuntimeError) as exc:
        logger.warning(
            "Failed to cache key '%s' with TTL %d due to Redis error: %s",
            key,
            ttl,
            exc,
        )
