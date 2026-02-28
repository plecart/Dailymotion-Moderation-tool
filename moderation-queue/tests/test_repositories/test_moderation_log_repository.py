"""Tests for moderation log repository."""

from src.database.connection import get_connection
from src.repositories import moderation_log_repository, video_repository


class TestModerationLogRepository:
    """Tests for moderation log repository functions."""

    async def test_insert_log_creates_entry(self, ensure_migrations, clean_db):
        """Insert log creates entry with all fields."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=9001)
            result = await moderation_log_repository.insert_log(
                conn, video_id=9001, status="spam", moderator="alice"
            )

        assert result["video_id"] == 9001
        assert result["status"] == "spam"
        assert result["moderator"] == "alice"
        assert result["created_at"] is not None

    async def test_get_logs_by_video_id_returns_all_logs(
        self, ensure_migrations, clean_db
    ):
        """Get logs returns all entries for a video in order."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=9002)
            await moderation_log_repository.insert_log(
                conn, video_id=9002, status="spam", moderator="alice"
            )
            await moderation_log_repository.insert_log(
                conn, video_id=9002, status="not spam", moderator="bob"
            )
            logs = await moderation_log_repository.get_logs_by_video_id(
                conn, video_id=9002
            )

        assert len(logs) == 2
        assert logs[0]["moderator"] == "alice"
        assert logs[1]["moderator"] == "bob"

    async def test_get_logs_by_video_id_empty_returns_empty_list(
        self, ensure_migrations, clean_db
    ):
        """Get logs for video without logs returns empty list."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=9003)
            logs = await moderation_log_repository.get_logs_by_video_id(
                conn, video_id=9003
            )

        assert logs == []
