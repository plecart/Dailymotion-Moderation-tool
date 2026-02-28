"""FastAPI dependency injection for database connections and authentication."""

import base64
import binascii
import logging
from typing import AsyncGenerator

import asyncpg
from fastapi import Header, HTTPException, status

from src.database.connection import get_connection

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency to provide a database connection to route handlers."""
    async with get_connection() as conn:
        yield conn


def get_moderator(authorization: str = Header(...)) -> str:
    """Extract and decode moderator name from base64 Authorization header.

    Args:
        authorization: Base64-encoded moderator name from Authorization header
            (required by FastAPI validation)

    Returns:
        Decoded moderator name as string

    Raises:
        HTTPException: If authorization header is invalid (returns 401).
            Note: Missing header triggers FastAPI validation error (422) before
            this function is called.
    """
    try:
        decoded_bytes = base64.b64decode(authorization, validate=True)
        decoded = decoded_bytes.decode("utf-8")
        if not decoded.strip():
            raise ValueError("Empty moderator name")
        return decoded
    except (binascii.Error, UnicodeDecodeError, ValueError) as e:
        logger.warning("Invalid Authorization header: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header. Expected base64-encoded moderator name.",
        )
