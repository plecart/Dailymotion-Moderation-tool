"""HTTP client for Dailymotion API."""

import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


async def create_http_client() -> httpx.AsyncClient:
    """Create and return HTTP async client.

    Returns:
        httpx AsyncClient instance
    """
    global _http_client
    _http_client = httpx.AsyncClient(
        base_url=settings.dailymotion_api_base_url,
        timeout=10.0,
    )
    logger.info("HTTP client created")
    return _http_client


async def close_http_client() -> None:
    """Close HTTP client."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")


def get_http_client() -> httpx.AsyncClient:
    """Get current HTTP client.

    Returns:
        httpx AsyncClient instance

    Raises:
        RuntimeError: If HTTP client not initialized
    """
    if _http_client is None:
        raise RuntimeError("HTTP client not initialized")
    return _http_client


async def fetch_video_info(video_id: str) -> dict:
    """Fetch video information from Dailymotion API.

    Args:
        video_id: Dailymotion video ID

    Returns:
        Dict with video information

    Raises:
        httpx.HTTPStatusError: If API returns error status
        httpx.RequestError: If request fails
    """
    client = get_http_client()
    fields = "title,channel,owner,filmstrip_60_url,embed_url"
    response = await client.get(f"/video/{video_id}", params={"fields": fields})
    response.raise_for_status()
    logger.info("Fetched video info for %s from Dailymotion API", video_id)
    return response.json()
