"""Business logic for video moderation operations."""

import hashlib
import logging

import asyncpg
from asyncpg import UniqueViolationError

from src.config import settings
from src.exceptions import (
    NoVideoAvailableError,
    VideoAlreadyExistsError,
    VideoAlreadyModeratedError,
    VideoNotAssignedError,
    VideoNotFoundError,
)
from src.models.enums import VideoStatus
from src.repositories import moderation_log_repository, video_repository

logger = logging.getLogger(__name__)


def _get_moderator_lock_key(moderator: str) -> int:
    """Generate unique advisory lock key for a moderator.

    Uses SHA-256 hash of moderator name combined with base key from settings.
    Returns a 64-bit key for use with pg_advisory_xact_lock(bigint) to ensure
    FIPS compatibility and reduce collision risk.

    Args:
        moderator: Moderator name

    Returns:
        Integer lock key (fits in PostgreSQL signed bigint)
    """
    hash_bytes = hashlib.sha256(moderator.encode()).digest()
    key_part = int.from_bytes(hash_bytes[:8], byteorder="big", signed=True)
    return settings.moderator_lock_base_key ^ key_part


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
        await conn.execute("SELECT pg_advisory_xact_lock($1)", lock_key)

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

    Uses a PostgreSQL advisory lock scoped to the moderator to ensure atomicity.

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


async def flag_video(
    conn: asyncpg.Connection,
    video_id: int,
    status: str,
    moderator: str,
) -> dict:
    """Flag a video as spam or not spam.

    Validates that:
    1. The video exists
    2. The video is assigned to this moderator
    3. The video is still pending

    Creates a moderation log entry and updates the video status.

    Args:
        conn: Database connection
        video_id: Video identifier
        status: New status (spam/not spam)
        moderator: Name of the moderator

    Returns:
        Dict with updated video data

    Raises:
        VideoNotFoundError: If video does not exist
        VideoNotAssignedError: If video is not assigned to this moderator
        VideoAlreadyModeratedError: If video has already been moderated
    """
    video = await video_repository.get_video_by_video_id(conn, video_id)
    if not video:
        logger.warning("Flag attempt on non-existent video: %d", video_id)
        raise VideoNotFoundError(video_id)

    if video["assigned_to"] != moderator:
        logger.warning(
            "Moderator %s tried to flag video %d assigned to %s",
            moderator,
            video_id,
            video["assigned_to"],
        )
        raise VideoNotAssignedError(video_id, moderator)

    if video["status"] != VideoStatus.PENDING.value:
        logger.warning(
            "Flag attempt on already moderated video: %d (status: %s)",
            video_id,
            video["status"],
        )
        raise VideoAlreadyModeratedError(video_id, video["status"])

    new_status = VideoStatus(status)
    await moderation_log_repository.insert_log(conn, video_id, status, moderator)
    updated = await video_repository.update_video_status(conn, video_id, new_status)

    logger.info("Video %d flagged as %s by %s", video_id, status, moderator)
    return updated
