"""Tests for video repository."""

import pytest

from src.database.connection import get_connection
from src.models.enums import VideoStatus
from src.repositories import video_repository


class TestVideoRepository:
    """Tests for video repository functions."""

    @pytest.mark.asyncio
    async def test_insert_video_valid_id_returns_complete_data(self, ensure_migrations, clean_db):
        """Test that insert_video returns complete video data with all fields."""
        async with get_connection() as conn:
            result = await video_repository.insert_video(conn, video_id=111111)

        assert result["video_id"] == 111111
        assert result["status"] == VideoStatus.PENDING.value
        assert result["assigned_to"] is None
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_get_video_by_video_id_existing_returns_video(self, ensure_migrations, clean_db):
        """Test that get_video_by_video_id returns the video when it exists."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=222222)
            result = await video_repository.get_video_by_video_id(conn, video_id=222222)

        assert result is not None
        assert result["video_id"] == 222222

    @pytest.mark.asyncio
    async def test_get_video_by_video_id_missing_returns_none(self, ensure_migrations, clean_db):
        """Test that get_video_by_video_id returns None when video doesn't exist."""
        async with get_connection() as conn:
            result = await video_repository.get_video_by_video_id(conn, video_id=999)

        assert result is None

    @pytest.mark.asyncio
    async def test_video_exists_existing_returns_true(self, ensure_migrations, clean_db):
        """Test that video_exists returns True when video exists."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=333333)
            exists = await video_repository.video_exists(conn, video_id=333333)

        assert exists is True

    @pytest.mark.asyncio
    async def test_video_exists_missing_returns_false(self, ensure_migrations, clean_db):
        """Test that video_exists returns False when video doesn't exist."""
        async with get_connection() as conn:
            exists = await video_repository.video_exists(conn, video_id=999)

        assert exists is False
