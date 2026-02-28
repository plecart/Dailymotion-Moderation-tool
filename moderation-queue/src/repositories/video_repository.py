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


async def get_video_assigned_to_moderator(
    conn: asyncpg.Connection, moderator: str
) -> dict | None:
    """Get a pending video already assigned to a specific moderator.

    Args:
        conn: Database connection
        moderator: Moderator name

    Returns:
        Dict with video data or None if no video assigned to this moderator
    """
    row = await conn.fetchrow(
        """
        SELECT id, video_id, status, assigned_to, created_at, updated_at
        FROM videos
        WHERE status = $1 AND assigned_to = $2
        ORDER BY created_at ASC
        LIMIT 1
        """,
        VideoStatus.PENDING.value,
        moderator,
    )
    return dict(row) if row else None


async def get_next_pending_video_and_assign(
    conn: asyncpg.Connection, moderator: str
) -> dict | None:
    """Get the next unassigned pending video and assign it to the moderator.

    Uses SELECT FOR UPDATE SKIP LOCKED to handle concurrent access:
    - Multiple moderators won't get the same video
    - If a video is locked by another transaction, it's skipped

    Args:
        conn: Database connection
        moderator: Moderator name to assign the video to

    Returns:
        Dict with video data or None if no pending video available
    """
    row = await conn.fetchrow(
        """
        UPDATE videos
        SET assigned_to = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = (
            SELECT id FROM videos
            WHERE status = $2 AND assigned_to IS NULL
            ORDER BY created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        RETURNING id, video_id, status, assigned_to, created_at, updated_at
        """,
        moderator,
        VideoStatus.PENDING.value,
    )
    if row:
        logger.info("Assigned video %d to moderator %s", row["video_id"], moderator)
    return dict(row) if row else None


async def update_video_status(
    conn: asyncpg.Connection,
    video_id: int,
    new_status: VideoStatus,
) -> dict | None:
    """Update the status of a video.

    Args:
        conn: Database connection
        video_id: Video identifier
        new_status: New status to set

    Returns:
        Dict with updated video data or None if video not found
    """
    row = await conn.fetchrow(
        """
        UPDATE videos
        SET status = $1, assigned_to = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE video_id = $2
        RETURNING id, video_id, status, assigned_to, created_at, updated_at
        """,
        new_status.value,
        video_id,
    )
    if row:
        logger.info("Updated video %d to status %s", video_id, new_status.value)
    return dict(row) if row else None
