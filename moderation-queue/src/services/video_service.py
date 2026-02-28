"""Business logic for video moderation operations."""

import logging

import asyncpg
from asyncpg import UniqueViolationError

from src.exceptions import VideoAlreadyExistsError
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
