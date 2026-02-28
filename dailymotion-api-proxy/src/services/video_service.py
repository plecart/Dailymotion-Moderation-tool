"""Business logic for video information retrieval with caching."""

import json
import logging

import httpx

from src.cache.redis_client import cache_get, cache_set
from src.clients.dailymotion_client import fetch_video_info
from src.config import settings
from src.exceptions import DailymotionAPIError, VideoNotFoundError

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "video_info:"


def _is_video_id_404(video_id: int) -> bool:
    """Check if video_id matches the 404 rule.

    Args:
        video_id: Video identifier

    Returns:
        True if video_id ends with 404
    """
    return str(video_id).endswith("404")


def _get_cache_key(video_id: int | str) -> str:
    """Generate cache key for video info.

    Args:
        video_id: Video identifier (int or str)

    Returns:
        Cache key string
    """
    return f"{CACHE_KEY_PREFIX}{video_id}"


def _handle_api_error(error: Exception, video_id: int) -> DailymotionAPIError:
    """Handle API errors and convert to DailymotionAPIError.

    Args:
        error: Exception raised by fetch_video_info
        video_id: Video identifier for logging

    Returns:
        DailymotionAPIError with appropriate message
    """
    if isinstance(error, httpx.HTTPStatusError):
        logger.error("Dailymotion API error: %s", error)
        # Upstream 404 for fixed video ID indicates misconfiguration/outage,
        # not that the requested video_id doesn't exist
        return DailymotionAPIError(
            f"Dailymotion API error: {error.response.status_code}",
            status_code=error.response.status_code,
        )
    if isinstance(error, httpx.RequestError):
        logger.error("Dailymotion API request failed: %s", error)
        return DailymotionAPIError("Dailymotion API request failed")
    if isinstance(error, RuntimeError):
        logger.error("Dailymotion HTTP client not initialized: %s", error)
        return DailymotionAPIError("Dailymotion API client not initialized")
    # Fallback for unexpected exceptions
    logger.error("Unexpected error fetching video info for %d: %s", video_id, error)
    return DailymotionAPIError("Dailymotion API error")


async def get_video_info(video_id: int) -> dict:
    """Get video information with caching.

    Logic:
    1. Check 404 rule (video_id ending with 404)
    2. Check cache for existing data
    3. Fetch from Dailymotion API if not cached
    4. Cache the result

    Note: Per spec, always fetches a configured fixed video ID (settings.dailymotion_fixed_video_id)
    regardless of the requested video_id.

    Args:
        video_id: Video identifier from request

    Returns:
        Dict with video information

    Raises:
        VideoNotFoundError: If video_id matches 404 rule
        DailymotionAPIError: If Dailymotion API request fails
    """
    if _is_video_id_404(video_id):
        logger.info("Video %d matches 404 rule", video_id)
        raise VideoNotFoundError(video_id)

    # Use fixed video ID for cache key since we always fetch the same video
    # This avoids duplicate cache entries with identical data
    fixed_video_id = settings.dailymotion_fixed_video_id
    cache_key = _get_cache_key(fixed_video_id)
    cached = await cache_get(cache_key)
    if cached is not None:
        try:
            logger.info("Returning cached video info for %d", video_id)
            return json.loads(cached)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to decode cached video info for %d; treating as cache miss",
                video_id,
            )
            # Continue to fetch from API as if cache miss

    try:
        data = await fetch_video_info(fixed_video_id)
    except (httpx.HTTPStatusError, httpx.RequestError, RuntimeError) as e:
        raise _handle_api_error(e, video_id) from e

    await cache_set(cache_key, json.dumps(data))
    logger.info("Fetched and cached video info for %d", video_id)
    return data
