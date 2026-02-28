"""Video routes for the moderation queue API."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from src.dependencies import get_db, get_moderator
from src.exceptions import NoVideoAvailableError, VideoAlreadyExistsError
from src.models.schemas import AddVideoRequest, AddVideoResponse, VideoResponse
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
