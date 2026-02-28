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
_MAX_ERROR_BODY_LENGTH = 200


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


def _handle_http_status_error(error: httpx.HTTPStatusError, requested_video_id: int) -> DailymotionAPIError:
    """Convert an HTTP status error to DailymotionAPIError.

    Args:
        error: HTTP status error from upstream API
        requested_video_id: Video ID originally requested by client

    Returns:
        DailymotionAPIError with status code, URL, response body, and requested video_id
    """
    logger.error(
        "Dailymotion API HTTP error for requested video_id %d: %s",
        requested_video_id,
        error,
    )
    body = error.response.text[:_MAX_ERROR_BODY_LENGTH] if error.response.text else "no body"
    return DailymotionAPIError(
        f"Dailymotion API returned HTTP {error.response.status_code} "
        f"for {error.request.url} (requested video_id: {requested_video_id}): {body}",
        status_code=error.response.status_code,
    )


def _handle_request_error(error: httpx.RequestError, requested_video_id: int) -> DailymotionAPIError:
    """Convert a network/transport error to DailymotionAPIError.

    Args:
        error: Request error (timeout, DNS, connection refused, etc.)
        requested_video_id: Video ID originally requested by client

    Returns:
        DailymotionAPIError with transport error details and requested video_id
    """
    logger.error(
        "Dailymotion API request failed for requested video_id %d: %s",
        requested_video_id,
        error,
    )
    return DailymotionAPIError(
        f"Dailymotion API request failed (requested video_id: {requested_video_id}): {error}"
    )


def _handle_client_error(error: RuntimeError) -> DailymotionAPIError:
    """Convert a client initialization error to DailymotionAPIError.

    Args:
        error: RuntimeError from uninitialized HTTP client

    Returns:
        DailymotionAPIError with initialization error details
    """
    logger.error("Dailymotion HTTP client not initialized: %s", error)
    return DailymotionAPIError(f"Dailymotion API client not initialized: {error}")


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
    except httpx.HTTPStatusError as e:
        raise _handle_http_status_error(e, video_id) from e
    except httpx.RequestError as e:
        raise _handle_request_error(e, video_id) from e
    except RuntimeError as e:
        raise _handle_client_error(e) from e

    await cache_set(cache_key, json.dumps(data))
    logger.info("Fetched and cached video info for %d", video_id)
    return data
