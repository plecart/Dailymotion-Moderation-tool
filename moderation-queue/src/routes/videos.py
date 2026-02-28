"""Video routes for the moderation queue API."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Path, status

from src.dependencies import get_db, get_moderator
from src.exceptions import (
    NoVideoAvailableError,
    VideoAlreadyExistsError,
    VideoAlreadyModeratedError,
    VideoNotAssignedError,
    VideoNotFoundError,
)
from src.models.schemas import (
    AddVideoRequest,
    AddVideoResponse,
    FlagVideoRequest,
    FlagVideoResponse,
    ModerationLogEntry,
    StatsResponse,
    VideoResponse,
)
from src.services import video_service

router = APIRouter(tags=["videos"])


@router.post(
    "/add_video",
    response_model=AddVideoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a video to the moderation queue",
    description="Server-to-server endpoint to add a new video with pending status.",
)
async def add_video_endpoint(
    request: AddVideoRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> AddVideoResponse:
    """Add a new video to the moderation queue.

    This endpoint is called server-to-server when a new video is uploaded.
    No authentication is required.
    """
    try:
        await video_service.add_video(conn, request.video_id)
        return AddVideoResponse(video_id=request.video_id)
    except VideoAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Video {request.video_id} already exists in the queue",
        )


@router.get(
    "/get_video",
    response_model=VideoResponse,
    summary="Get the next video to moderate",
    description="Returns the next pending video for the authenticated moderator.",
)
async def get_video_endpoint(
    moderator: str = Depends(get_moderator),
    conn: asyncpg.Connection = Depends(get_db),
) -> VideoResponse:
    """Get the next video to moderate for the authenticated moderator.

    - If the moderator already has an assigned video, returns that video
    - Otherwise, assigns and returns the next available pending video
    - Requires base64-encoded moderator name in Authorization header
    """
    try:
        video = await video_service.get_video_for_moderator(conn, moderator)
        return VideoResponse(video_id=video["video_id"])
    except NoVideoAvailableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No video available for moderation",
        )


@router.post(
    "/flag_video",
    response_model=FlagVideoResponse,
    summary="Flag a video as spam or not spam",
    description="Moderator endpoint to mark a video after review.",
)
async def flag_video_endpoint(
    request: FlagVideoRequest,
    moderator: str = Depends(get_moderator),
    conn: asyncpg.Connection = Depends(get_db),
) -> FlagVideoResponse:
    """Flag a video as spam or not spam.

    - Video must be assigned to the authenticated moderator
    - Creates a moderation log entry
    - Updates video status and releases assignment
    - Requires base64-encoded moderator name in Authorization header
    """
    try:
        updated = await video_service.flag_video(
            conn, request.video_id, request.status, moderator
        )
        return FlagVideoResponse(video_id=updated["video_id"], status=updated["status"])
    except VideoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {request.video_id} not found",
        )
    except VideoNotAssignedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Video {request.video_id} is not assigned to you",
        )
    except VideoAlreadyModeratedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get queue statistics",
    description="Returns counts of pending, spam, and not spam videos.",
)
async def stats_endpoint(
    conn: asyncpg.Connection = Depends(get_db),
) -> StatsResponse:
    """Get moderation queue statistics.

    No authentication required.
    """
    stats = await video_service.get_stats(conn)
    return StatsResponse(**stats)


@router.get(
    "/log_video/{video_id}",
    response_model=list[ModerationLogEntry],
    summary="Get moderation history for a video",
    description="Returns the moderation action history for a specific video.",
)
async def log_video_endpoint(
    video_id: int = Path(..., gt=0, description="Video identifier"),
    conn: asyncpg.Connection = Depends(get_db),
) -> list[ModerationLogEntry]:
    """Get moderation history for a video.

    No authentication required.
    """
    try:
        logs = await video_service.get_video_logs(conn, video_id)
        return [ModerationLogEntry(**log) for log in logs]
    except VideoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found",
        )
