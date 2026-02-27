"""FastAPI dependency injection: Redis client."""
from collections.abc import AsyncGenerator

# Placeholder until Redis connection is implemented
# from redis.asyncio import Redis  # get_redis will yield Redis


async def get_redis() -> AsyncGenerator[None, None]:
    """Yield Redis async client. To be wired when cache is implemented."""
    yield None  # TODO: yield Redis client when cache module is implemented
