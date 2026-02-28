"""Tests for video service."""

import pytest

from src.database.connection import get_connection
from src.exceptions import (
    NoVideoAvailableError,
    VideoAlreadyExistsError,
    VideoAlreadyModeratedError,
    VideoNotAssignedError,
    VideoNotFoundError,
)
from src.models.enums import VideoStatus
from src.repositories import moderation_log_repository
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


class TestFlagVideo:
    """Tests for flag_video service function."""

    async def test_flag_video_updates_status_to_spam(self, ensure_migrations, clean_db):
        """Flag video as spam updates status correctly and creates moderation log."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=6001)
            await video_service.get_video_for_moderator(conn, "alice")
            result = await video_service.flag_video(conn, 6001, "spam", "alice")

        assert result["video_id"] == 6001
        assert result["status"] == VideoStatus.SPAM.value
        assert result["assigned_to"] is None

        # Verify moderation log was created
        async with get_connection() as conn:
            logs = await moderation_log_repository.get_logs_by_video_id(conn, 6001)
        assert len(logs) == 1
        assert logs[0]["video_id"] == 6001
        assert logs[0]["status"] == VideoStatus.SPAM.value
        assert logs[0]["moderator"] == "alice"

    async def test_flag_video_updates_status_to_not_spam(
        self, ensure_migrations, clean_db
    ):
        """Flag video as not spam updates status correctly and creates moderation log."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=6002)
            await video_service.get_video_for_moderator(conn, "bob")
            result = await video_service.flag_video(conn, 6002, "not spam", "bob")

        assert result["video_id"] == 6002
        assert result["status"] == VideoStatus.NOT_SPAM.value

        # Verify moderation log was created
        async with get_connection() as conn:
            logs = await moderation_log_repository.get_logs_by_video_id(conn, 6002)
        assert len(logs) == 1
        assert logs[0]["video_id"] == 6002
        assert logs[0]["status"] == VideoStatus.NOT_SPAM.value
        assert logs[0]["moderator"] == "bob"

    async def test_flag_video_nonexistent_raises_not_found(
        self, ensure_migrations, clean_db
    ):
        """Flag non-existent video raises VideoNotFoundError."""
        async with get_connection() as conn:
            with pytest.raises(VideoNotFoundError) as exc_info:
                await video_service.flag_video(conn, 9999, "spam", "alice")

        assert exc_info.value.video_id == 9999

    async def test_flag_video_not_assigned_raises_error(
        self, ensure_migrations, clean_db
    ):
        """Flag video assigned to another moderator raises VideoNotAssignedError."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=6003)
            await video_service.get_video_for_moderator(conn, "alice")

            with pytest.raises(VideoNotAssignedError) as exc_info:
                await video_service.flag_video(conn, 6003, "spam", "bob")

        assert exc_info.value.video_id == 6003
        assert exc_info.value.moderator == "bob"

    async def test_flag_video_unassigned_raises_error(
        self, ensure_migrations, clean_db
    ):
        """Flag unassigned video raises VideoNotAssignedError."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=6004)

            with pytest.raises(VideoNotAssignedError):
                await video_service.flag_video(conn, 6004, "spam", "alice")

    async def test_flag_video_already_moderated_raises_error(
        self, ensure_migrations, clean_db
    ):
        """Flag already moderated video raises VideoAlreadyModeratedError."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=6005)
            await video_service.get_video_for_moderator(conn, "alice")
            await video_service.flag_video(conn, 6005, "spam", "alice")

            with pytest.raises(VideoAlreadyModeratedError) as exc_info:
                await video_service.flag_video(conn, 6005, "not spam", "alice")

        assert exc_info.value.video_id == 6005
        assert exc_info.value.current_status == VideoStatus.SPAM.value


class TestGetStats:
    """Tests for get_stats service function."""

    async def test_empty_queue_returns_all_zeros(self, ensure_migrations, clean_db):
        """Empty queue returns all zeros."""
        async with get_connection() as conn:
            result = await video_service.get_stats(conn)

        assert result["total_pending_videos"] == 0
        assert result["total_spam_videos"] == 0
        assert result["total_not_spam_videos"] == 0

    async def test_counts_all_statuses_correctly(self, ensure_migrations, clean_db):
        """Stats counts all statuses correctly."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=7001)
            await video_service.add_video(conn, video_id=7002)
            await video_service.add_video(conn, video_id=7003)
            await video_service.add_video(conn, video_id=7004)

            await video_service.get_video_for_moderator(conn, "alice")
            await video_service.flag_video(conn, 7001, "spam", "alice")

            await video_service.get_video_for_moderator(conn, "bob")
            await video_service.flag_video(conn, 7002, "not spam", "bob")

            result = await video_service.get_stats(conn)

        assert result["total_pending_videos"] == 2
        assert result["total_spam_videos"] == 1
        assert result["total_not_spam_videos"] == 1


class TestGetVideoLogs:
    """Tests for get_video_logs service function."""

    async def test_nonexistent_video_raises_not_found(
        self, ensure_migrations, clean_db
    ):
        """Logs request for non-existent video raises VideoNotFoundError."""
        async with get_connection() as conn:
            with pytest.raises(VideoNotFoundError):
                await video_service.get_video_logs(conn, 9999)

    async def test_video_without_logs_returns_empty_list(
        self, ensure_migrations, clean_db
    ):
        """Video without moderation logs returns empty list."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=8001)
            result = await video_service.get_video_logs(conn, 8001)

        assert result == []

    async def test_returns_moderation_history(self, ensure_migrations, clean_db):
        """Returns moderation history with correct format."""
        async with get_connection() as conn:
            await video_service.add_video(conn, video_id=8002)
            await video_service.get_video_for_moderator(conn, "alice")
            await video_service.flag_video(conn, 8002, "spam", "alice")

            result = await video_service.get_video_logs(conn, 8002)

        assert len(result) == 1
        assert result[0]["status"] == "spam"
        assert result[0]["moderator"] == "alice"
        assert "date" in result[0]
