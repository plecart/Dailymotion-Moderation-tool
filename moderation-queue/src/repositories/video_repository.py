"""Repository for video data access with raw SQL queries."""

import logging

import asyncpg

from src.models.enums import VideoStatus

logger = logging.getLogger(__name__)


async def insert_video(conn: asyncpg.Connection, video_id: int) -> dict:
    """Insert a new video into the queue with pending status.

    Args:
        conn: Database connection
        video_id: Unique video identifier

    Returns:
        Dict with the inserted video data

    Raises:
        asyncpg.UniqueViolationError: If video_id already exists
    """
    row = await conn.fetchrow(
        """
        INSERT INTO videos (video_id, status)
        VALUES ($1, $2)
        RETURNING id, video_id, status, assigned_to, created_at, updated_at
        """,
        video_id,
        VideoStatus.PENDING.value,
    )
    logger.info("Inserted video %d with status pending", video_id)
    return dict(row)


async def get_video_by_video_id(conn: asyncpg.Connection, video_id: int) -> dict | None:
    """Get a video by its video_id.

    Args:
        conn: Database connection
        video_id: Video identifier to look up

    Returns:
        Dict with video data or None if not found
    """
    row = await conn.fetchrow(
        """
        SELECT id, video_id, status, assigned_to, created_at, updated_at
        FROM videos
        WHERE video_id = $1
        """,
        video_id,
    )
    return dict(row) if row else None


async def video_exists(conn: asyncpg.Connection, video_id: int) -> bool:
    """Check if a video exists in the queue.

    Args:
        conn: Database connection
        video_id: Video identifier to check

    Returns:
        True if video exists, False otherwise
    """
    result = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM videos WHERE video_id = $1)",
        video_id,
    )
    return result
