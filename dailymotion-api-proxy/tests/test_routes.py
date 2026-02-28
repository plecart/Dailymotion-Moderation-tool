"""Tests for video routes."""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
from httpx import AsyncClient


class TestGetVideoInfoEndpoint:
    """Tests for GET /get_video_info/{video_id} endpoint."""

    async def test_video_id_404_rule_returns_404(self, client: AsyncClient):
        """Video ID ending with 404 returns 404."""
        response = await client.get("/get_video_info/1404")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_video_id_10404_returns_404(self, client: AsyncClient):
        """Video ID 10404 returns 404."""
        response = await client.get("/get_video_info/10404")

        assert response.status_code == 404

    async def test_valid_video_id_returns_video_info(
        self, client: AsyncClient, mock_http_client
    ):
        """Valid video ID returns video info from API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Video",
            "channel": "test",
            "owner": "test_owner",
            "filmstrip_60_url": "http://example.com/filmstrip.jpg",
            "embed_url": "http://example.com/embed",
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get = AsyncMock(return_value=mock_response)

        response = await client.get("/get_video_info/123456")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Video"
        assert data["channel"] == "test"
        assert data["owner"] == "test_owner"

    async def test_cached_response_does_not_call_api(
        self, client: AsyncClient, mock_redis, mock_http_client
    ):
        """Cached response returns without calling API."""
        cached_data = json.dumps(
            {
                "title": "Cached Video",
                "channel": "cached",
                "owner": "cached_owner",
                "filmstrip_60_url": None,
                "embed_url": "http://example.com/cached",
            }
        )
        await mock_redis.set("video_info:789", cached_data)

        response = await client.get("/get_video_info/789")

        assert response.status_code == 200
        assert response.json()["title"] == "Cached Video"
        mock_http_client.get.assert_not_called()

    async def test_api_error_returns_502(self, client: AsyncClient, mock_http_client):
        """API error returns 502 Bad Gateway."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        mock_response.raise_for_status = MagicMock(side_effect=error)
        mock_http_client.get = AsyncMock(return_value=mock_response)

        response = await client.get("/get_video_info/123")

        assert response.status_code == 502


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    async def test_health_returns_ok(self, client: AsyncClient):
        """Health endpoint returns ok status."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
