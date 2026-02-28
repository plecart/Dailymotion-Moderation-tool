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


def _check_video_flagging_conditions(
    video: dict, video_id: int, moderator: str, context: str = "Flag attempt"
) -> None:
    """Check if a video can be flagged by the moderator.

    Validates video status and assignment. Raises appropriate exception if conditions
    are not met.

    Args:
        video: Video data dict
        video_id: Video identifier (for error messages)
        moderator: Name of the moderator
        context: Context string for log messages (default: "Flag attempt")

    Raises:
        VideoAlreadyModeratedError: If video has already been moderated
        VideoNotAssignedError: If video is not assigned to this moderator
    """
    # Check status first, as assigned_to is NULL after moderation
    if video["status"] != VideoStatus.PENDING.value:
        logger.warning(
            "%s on already moderated video: %d (status: %s)",
            context,
            video_id,
            video["status"],
        )
        raise VideoAlreadyModeratedError(video_id, video["status"])

    if video["assigned_to"] != moderator:
        logger.warning(
            "%s: moderator %s tried to flag video %d assigned to %s",
            context,
            moderator,
            video_id,
            video["assigned_to"],
        )
        raise VideoNotAssignedError(video_id, moderator)


async def _validate_video_for_flagging(
    conn: asyncpg.Connection, video_id: int, moderator: str
) -> None:
    """Validate that a video exists and can be flagged by the moderator.

    Args:
        conn: Database connection
        video_id: Video identifier
        moderator: Name of the moderator

    Raises:
        VideoNotFoundError: If video does not exist
        VideoNotAssignedError: If video is not assigned to this moderator
        VideoAlreadyModeratedError: If video has already been moderated
    """
    video = await video_repository.get_video_by_video_id(conn, video_id)
    if not video:
        logger.warning("Flag attempt on non-existent video: %d", video_id)
        raise VideoNotFoundError(video_id)

    _check_video_flagging_conditions(video, video_id, moderator)


async def _handle_concurrent_flag_failure(
    conn: asyncpg.Connection, video_id: int, moderator: str
) -> None:
    """Handle failure of conditional update due to concurrent modification.

    Re-reads the video state and raises the appropriate exception based on current state.
    This handles the race condition where another request modified the video between
    the initial validation and the conditional update.

    Args:
        conn: Database connection
        video_id: Video identifier
        moderator: Name of the moderator

    Raises:
        VideoNotAssignedError: If video is not assigned to this moderator
        VideoAlreadyModeratedError: If video has already been moderated
        RuntimeError: If update failed despite all conditions being met (unexpected state)
    """
    current_video = await video_repository.get_video_by_video_id(conn, video_id)

    # Check conditions - raises exception if conditions not met (expected case)
    _check_video_flagging_conditions(
        current_video, video_id, moderator, context="Concurrent flag attempt"
    )

    # If we reach here, conditions are met but update failed - unexpected state
    # This indicates a system issue (e.g., database inconsistency, connection problem)
    # and should surface as 5xx error, not 4xx authorization error
    logger.error(
        "Unexpected failure updating video %d status (still pending, assigned to %s)",
        video_id,
        moderator,
    )
    raise RuntimeError(
        f"Concurrent flag failure: video {video_id} remains pending and assigned to "
        f"{moderator} despite failed conditional update"
    )


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

    Creates a moderation log entry and updates the video status atomically
    within a transaction to prevent race conditions from concurrent requests.

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
        RuntimeError: If conditional update failed despite all conditions being met
            (indicates a system issue)
    """
    # Pre-validate for better error messages (before transaction)
    await _validate_video_for_flagging(conn, video_id, moderator)

    new_status = VideoStatus(status)

    # Wrap status update + log insert in a transaction for atomicity
    # The conditional update prevents race conditions from concurrent flag requests
    async with conn.transaction():
        updated = await video_repository.update_video_status_if_pending_and_assigned(
            conn, video_id, new_status, moderator
        )
        # Only insert a moderation log entry if the status update succeeded
        if updated:
            await moderation_log_repository.insert_log(
                conn, video_id, status, moderator
            )

    # If update failed, handle concurrent modification
    if not updated:
        await _handle_concurrent_flag_failure(conn, video_id, moderator)

    logger.info("Video %d flagged as %s by %s", video_id, status, moderator)
    return updated


async def get_stats(conn: asyncpg.Connection) -> dict:
    """Get moderation queue statistics.

    Args:
        conn: Database connection

    Returns:
        Dict with total_pending_videos, total_spam_videos, total_not_spam_videos
    """
    counts = await video_repository.count_videos_by_status(conn)
    return {
        "total_pending_videos": counts.get(VideoStatus.PENDING.value, 0),
        "total_spam_videos": counts.get(VideoStatus.SPAM.value, 0),
        "total_not_spam_videos": counts.get(VideoStatus.NOT_SPAM.value, 0),
    }


async def get_video_logs(conn: asyncpg.Connection, video_id: int) -> list[dict]:
    """Get moderation history for a video.

    Args:
        conn: Database connection
        video_id: Video identifier

    Returns:
        List of moderation log entries

    Raises:
        VideoNotFoundError: If video does not exist
    """
    video = await video_repository.get_video_by_video_id(conn, video_id)
    if not video:
        logger.warning("Log request for non-existent video: %d", video_id)
        raise VideoNotFoundError(video_id)

    logs = await moderation_log_repository.get_logs_by_video_id(conn, video_id)
    return [
        {
            "date": log["created_at"],
            "status": log["status"],
            "moderator": log["moderator"],
        }
        for log in logs
    ]
