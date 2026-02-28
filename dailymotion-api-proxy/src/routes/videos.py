"""Video routes for Dailymotion API Proxy."""

from fastapi import APIRouter, HTTPException, status

from src.exceptions import DailymotionAPIError, VideoNotFoundError
from src.models.schemas import VideoInfoResponse
from src.services import video_service

router = APIRouter(tags=["videos"])


@router.get(
    "/get_video_info/{video_id}",
    response_model=VideoInfoResponse,
    summary="Get video information",
    description="Proxy endpoint to fetch video info from Dailymotion API with caching.",
)
async def get_video_info_endpoint(video_id: int) -> VideoInfoResponse:
    """Get video information from Dailymotion API.

    - Uses Redis cache to avoid redundant API calls
    - Returns 404 if video_id ends with 404 (per spec)
    - Always fetches fixed video x2m8jpp (per spec)
    """
    try:
        data = await video_service.get_video_info(video_id)
        return VideoInfoResponse(**data)
    except VideoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video {video_id} not found",
        )
    except DailymotionAPIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Dailymotion API unavailable",
        )
