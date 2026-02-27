"""FastAPI dependency injection: database and auth."""
from collections.abc import AsyncGenerator

# Placeholder types until database/connection and auth are implemented
# from asyncpg import Pool  # get_db will yield Pool
# get_auth will decode Authorization header and yield moderator name (str)


async def get_db() -> AsyncGenerator[None, None]:
    """Yield database pool. To be wired to database/connection.py."""
    yield None  # TODO: yield pool when database module is implemented


async def get_auth() -> AsyncGenerator[str | None, None]:
    """Yield moderator id from Authorization header (base64). To be implemented."""
    yield None  # TODO: decode Authorization and yield moderator name
