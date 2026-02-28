"""Business logic for video moderation operations."""

import logging

import asyncpg
from asyncpg import UniqueViolationError

from src.exceptions import NoVideoAvailableError, VideoAlreadyExistsError
from src.repositories import video_repository

logger = logging.getLogger(__name__)


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

    Args:
        conn: Database connection
        moderator: Moderator name

    Returns:
        Dict with video data

    Raises:
        NoVideoAvailableError: If no video is available for moderation
    """
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

    new_assignment = await video_repository.get_next_pending_video_and_assign(
        conn, moderator
    )
    if new_assignment:
        return new_assignment

    logger.info("No video available for moderator %s", moderator)
    raise NoVideoAvailableError()
