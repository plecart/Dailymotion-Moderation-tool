"""Tests for video service."""

from unittest.mock import MagicMock

import httpx

from src.config import settings
from src.exceptions import DailymotionAPIError
from src.services.video_service import (
    _get_cache_key,
    _handle_client_error,
    _handle_http_status_error,
    _handle_request_error,
    _is_video_id_404,
)


class TestVideoId404Rule:
    """Tests for 404 rule helper function."""

    def test_video_id_ending_404_returns_true(self):
        """Video ID ending with 404 matches rule."""
        assert _is_video_id_404(404) is True
        assert _is_video_id_404(1404) is True
        assert _is_video_id_404(10404) is True
        assert _is_video_id_404(123404) is True

    def test_video_id_not_ending_404_returns_false(self):
        """Video ID not ending with 404 does not match rule."""
        assert _is_video_id_404(123) is False
        assert _is_video_id_404(4040) is False
        assert _is_video_id_404(40) is False
        assert _is_video_id_404(4) is False


class TestCacheKey:
    """Tests for cache key generation."""

    def test_cache_key_format(self):
        """Cache key has correct prefix and video_id."""
        key = _get_cache_key(123456)
        assert key == "video_info:123456"

    def test_cache_key_different_for_different_ids(self):
        """Different video IDs produce different cache keys."""
        assert _get_cache_key(123) != _get_cache_key(456)

    def test_cache_key_accepts_string_video_id(self):
        """Cache key generation works with string video IDs."""
        fixed_video_id = settings.dailymotion_fixed_video_id
        key = _get_cache_key(fixed_video_id)
        assert key == f"video_info:{fixed_video_id}"


class TestErrorHandlers:
    """Tests for error handling helper functions."""

    def test_handle_http_status_error_includes_requested_video_id(self):
        """HTTP status error handler includes requested video_id in message."""
        mock_request = MagicMock()
        mock_request.url = "https://api.dailymotion.com/video/x2m8jpp"
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.content = b"Internal Server Error"
        error = httpx.HTTPStatusError("Server Error", request=mock_request, response=mock_response)

        result = _handle_http_status_error(error, requested_video_id=12345)

        assert isinstance(result, DailymotionAPIError)
        assert result.status_code == 500
        assert "requested video_id: 12345" in str(result)
        assert "500" in str(result)
        assert "x2m8jpp" in str(result)

    def test_handle_http_status_error_truncates_large_body(self):
        """HTTP status error handler truncates large response bodies."""
        mock_request = MagicMock()
        mock_request.url = "https://api.dailymotion.com/video/x2m8jpp"
        mock_response = MagicMock()
        mock_response.status_code = 500
        # Create a body larger than _MAX_ERROR_BODY_LENGTH (200)
        large_body = b"x" * 500
        mock_response.content = large_body
        error = httpx.HTTPStatusError("Server Error", request=mock_request, response=mock_response)

        result = _handle_http_status_error(error, requested_video_id=12345)

        assert isinstance(result, DailymotionAPIError)
        # Body should be truncated to 200 characters
        assert len(result.args[0]) < len(large_body) + 100  # Account for message prefix

    def test_handle_http_status_error_handles_empty_body(self):
        """HTTP status error handler handles empty response body."""
        mock_request = MagicMock()
        mock_request.url = "https://api.dailymotion.com/video/x2m8jpp"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.content = b""
        error = httpx.HTTPStatusError("Not Found", request=mock_request, response=mock_response)

        result = _handle_http_status_error(error, requested_video_id=12345)

        assert isinstance(result, DailymotionAPIError)
        assert "no body" in str(result)

    def test_handle_request_error_includes_requested_video_id(self):
        """Request error handler includes requested video_id in message."""
        error = httpx.RequestError("Connection failed", request=MagicMock())

        result = _handle_request_error(error, requested_video_id=12345)

        assert isinstance(result, DailymotionAPIError)
        assert "requested video_id: 12345" in str(result)
        assert "Connection failed" in str(result)

    def test_handle_client_error_creates_dailymotion_api_error(self):
        """Client error handler converts RuntimeError to DailymotionAPIError."""
        error = RuntimeError("HTTP client not initialized")

        result = _handle_client_error(error)

        assert isinstance(result, DailymotionAPIError)
        assert "client not initialized" in str(result)
