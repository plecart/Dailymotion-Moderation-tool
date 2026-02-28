"""Tests for video service."""

from src.config import settings
from src.services.video_service import _get_cache_key, _is_video_id_404


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
