"""Repository for moderation log data access with raw SQL queries."""

import logging

import asyncpg

logger = logging.getLogger(__name__)


async def insert_log(
    conn: asyncpg.Connection,
    video_id: int,
    status: str,
    moderator: str,
) -> dict:
    """Insert a new moderation log entry.

    Args:
        conn: Database connection
        video_id: Video identifier
        status: Status set by moderator (spam/not spam)
        moderator: Name of the moderator

    Returns:
        Dict with the inserted log data
    """
    row = await conn.fetchrow(
        """
        INSERT INTO moderation_logs (video_id, status, moderator)
        VALUES ($1, $2, $3)
        RETURNING id, video_id, status, moderator, created_at
        """,
        video_id,
        status,
        moderator,
    )
    logger.info(
        "Created moderation log: video %d flagged as %s by %s",
        video_id,
        status,
        moderator,
    )
    return dict(row)


async def get_logs_by_video_id(
    conn: asyncpg.Connection,
    video_id: int,
) -> list[dict]:
    """Get all moderation logs for a video, ordered by creation date.

    Args:
        conn: Database connection
        video_id: Video identifier

    Returns:
        List of log entries as dicts
    """
    rows = await conn.fetch(
        """
        SELECT id, video_id, status, moderator, created_at
        FROM moderation_logs
        WHERE video_id = $1
        ORDER BY created_at ASC
        """,
        video_id,
    )
    return [dict(row) for row in rows]
