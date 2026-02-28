"""Tests for video service."""

import pytest

from src.database.connection import get_connection
from src.exceptions import NoVideoAvailableError, VideoAlreadyExistsError
from src.models.enums import VideoStatus
from src.services import video_service


class TestAddVideo:
    """Tests for add_video service function."""

    async def test_add_video_valid_id_creates_pending_video(
        self, ensure_migrations, clean_db
    ):
        """Test that add_video creates a video with pending status."""
        async with get_connection() as conn:
            result = await video_service.add_video(conn, video_id=999999)

        assert result["video_id"] == 999999
        assert result["status"] == VideoStatus.PENDING.value
        assert result["assigned_to"] is None

    async def test_add_video_duplicate_raises_already_exists(
        self, ensure_migrations, clean_db
    ):
        """Test that adding a duplicate video raises VideoAlreadyExistsError."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=888888)

        async with get_connection() as conn:
            with pytest.raises(VideoAlreadyExistsError) as exc_info:
                await video_service.add_video(conn, video_id=888888)

        assert exc_info.value.video_id == 888888


class TestGetVideoForModerator:
    """Tests for get_video_for_moderator service function."""

    async def test_empty_queue_raises_no_video_available(
        self, ensure_migrations, clean_db
    ):
        """Empty queue raises NoVideoAvailableError."""
        async with get_connection() as conn:
            with pytest.raises(NoVideoAvailableError):
                await video_service.get_video_for_moderator(conn, "alice")

    async def test_assigns_pending_video_to_moderator(
        self, ensure_migrations, clean_db
    ):
        """Available pending video is assigned to moderator."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=5001)
            result = await video_service.get_video_for_moderator(conn, "alice")

        assert result["video_id"] == 5001
        assert result["assigned_to"] == "alice"

    async def test_returns_same_video_on_repeated_calls(
        self, ensure_migrations, clean_db
    ):
        """Same moderator gets same video on repeated calls."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=5002)
            first_call = await video_service.get_video_for_moderator(conn, "bob")
            second_call = await video_service.get_video_for_moderator(conn, "bob")

        assert first_call["video_id"] == second_call["video_id"] == 5002

    async def test_different_moderators_get_different_videos(
        self, ensure_migrations, clean_db
    ):
        """Two different moderators get two different videos."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=5003)
            await video_service.add_video(conn, video_id=5004)
            alice_video = await video_service.get_video_for_moderator(conn, "alice")
            bob_video = await video_service.get_video_for_moderator(conn, "bob")

        assert alice_video["video_id"] != bob_video["video_id"]
        assert {alice_video["video_id"], bob_video["video_id"]} == {5003, 5004}

    async def test_second_moderator_no_video_if_all_assigned(
        self, ensure_migrations, clean_db
    ):
        """Second moderator gets NoVideoAvailableError if all videos are assigned."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=5005)
            await video_service.get_video_for_moderator(conn, "alice")

            with pytest.raises(NoVideoAvailableError):
                await video_service.get_video_for_moderator(conn, "bob")
