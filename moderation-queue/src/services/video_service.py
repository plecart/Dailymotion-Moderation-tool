"""Business logic for video moderation operations."""

import hashlib
import logging

import asyncpg
from asyncpg import UniqueViolationError

from src.config import settings
from src.exceptions import NoVideoAvailableError, VideoAlreadyExistsError
from src.repositories import video_repository

logger = logging.getLogger(__name__)


def _get_moderator_lock_key(moderator: str) -> int:
    """Generate a unique advisory lock key for a moderator.

    Uses MD5 hash of moderator name combined with base key from settings to ensure
    consistent, unique lock keys per moderator while avoiding conflicts
    with other advisory lock namespaces.

    Args:
        moderator: Moderator name

    Returns:
        Integer lock key (fits in int64)
    """
    hash_bytes = hashlib.md5(moderator.encode()).digest()
    hash_part = int.from_bytes(hash_bytes[:4], byteorder="big", signed=False)
    return settings.moderator_lock_base_key ^ hash_part


async def _get_video_with_moderator_lock(
    conn: asyncpg.Connection, moderator: str
) -> dict | None:
    """Get video for moderator within a transaction with advisory lock.

    This ensures atomicity: concurrent requests from the same moderator
    are serialized to prevent race conditions.

    Args:
        conn: Database connection
        moderator: Moderator name

    Returns:
        Dict with video data or None if no video available
    """
    lock_key = _get_moderator_lock_key(moderator)
    async with conn.transaction():
        # Acquire moderator-scoped advisory lock (released automatically at end of transaction)
        await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

        # Check for existing assignment first
        already_assigned = await video_repository.get_video_assigned_to_moderator(
            conn, moderator
        )
        if already_assigned:
            logger.info(
                "Returning already assigned video %d to %s",
                already_assigned["video_id"],
                moderator,
            )
            return already_assigned

        # Assign new video if available
        return await video_repository.get_next_pending_video_and_assign(conn, moderator)


async def add_video(conn: asyncpg.Connection, video_id: int) -> dict:
    """Add a new video to the moderation queue.

    Args:
        conn: Database connection
        video_id: Unique video identifier

    Returns:
        Dict with the inserted video data

    Raises:
        VideoAlreadyExistsError: If video already exists in queue
    """
    try:
        return await video_repository.insert_video(conn, video_id)
    except UniqueViolationError:
        logger.warning("Attempted to add duplicate video: %d", video_id)
        raise VideoAlreadyExistsError(video_id)


async def get_video_for_moderator(conn: asyncpg.Connection, moderator: str) -> dict:
    """Get the next video to moderate for a specific moderator.

    Logic:
    1. If the moderator already has an assigned pending video, return it
    2. Otherwise, assign the next unassigned pending video to them
    3. If no video is available, raise NoVideoAvailableError

    Uses a PostgreSQL advisory lock scoped to the moderator to ensure atomicity:
    concurrent requests from the same moderator are serialized to prevent race conditions.

    Args:
        conn: Database connection
        moderator: Moderator name

    Returns:
        Dict with video data

    Raises:
        NoVideoAvailableError: If no video is available for moderation
    """
    video = await _get_video_with_moderator_lock(conn, moderator)
    if video:
        return video

    logger.info("No video available for moderator %s", moderator)
    raise NoVideoAvailableError()
