"""Tests for video service."""

import pytest

from src.database.connection import get_connection
from src.exceptions import VideoAlreadyExistsError
from src.models.enums import VideoStatus
from src.services import video_service


class TestAddVideo:
    """Tests for add_video service function."""

    async def test_add_video_valid_id_creates_pending_video(self, ensure_migrations, clean_db):
        """Test that add_video creates a video with pending status."""
        async with get_connection() as conn:
            result = await video_service.add_video(conn, video_id=999999)

        assert result["video_id"] == 999999
        assert result["status"] == VideoStatus.PENDING.value
        assert result["assigned_to"] is None

    async def test_add_video_duplicate_raises_already_exists(self, ensure_migrations, clean_db):
        """Test that adding a duplicate video raises VideoAlreadyExistsError."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=888888)

        async with get_connection() as conn:
            with pytest.raises(VideoAlreadyExistsError) as exc_info:
                await video_service.add_video(conn, video_id=888888)

        assert exc_info.value.video_id == 888888
