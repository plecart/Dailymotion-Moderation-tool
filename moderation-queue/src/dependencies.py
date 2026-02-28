"""FastAPI dependency injection for database connections and authentication."""

import base64
from typing import AsyncGenerator

import asyncpg
from fastapi import Header, HTTPException, status

from src.database.connection import get_connection


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency to provide a database connection to route handlers."""
    async with get_connection() as conn:
        yield conn


def get_moderator(authorization: str = Header(...)) -> str:
    """Extract and decode moderator name from base64 Authorization header.

    Args:
        authorization: Base64-encoded moderator name from Authorization header

    Returns:
        Decoded moderator name as string

    Raises:
        HTTPException: If authorization header is missing or invalid
    """
    try:
        decoded = base64.b64decode(authorization).decode("utf-8")
        if not decoded.strip():
            raise ValueError("Empty moderator name")
        return decoded
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header. Expected base64-encoded moderator name.",
        )
