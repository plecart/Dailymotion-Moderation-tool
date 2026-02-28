"""Video routes for the moderation queue API."""

from fastapi import APIRouter, Depends, HTTPException, status
import asyncpg

from src.dependencies import get_db
from src.exceptions import VideoAlreadyExistsError
from src.models.schemas import AddVideoRequest, AddVideoResponse
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
