"""Tests for video repository."""

from src.database.connection import get_connection
from src.models.enums import VideoStatus
from src.repositories import video_repository


class TestVideoRepository:
    """Tests for video repository functions."""

    async def test_insert_video_valid_id_returns_complete_data(
        self, ensure_migrations, clean_db
    ):
        """Test that insert_video returns complete video data with all fields."""
        async with get_connection() as conn:
            result = await video_repository.insert_video(conn, video_id=111111)

        assert result["video_id"] == 111111
        assert result["status"] == VideoStatus.PENDING.value
        assert result["assigned_to"] is None
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    async def test_get_video_by_video_id_existing_returns_video(
        self, ensure_migrations, clean_db
    ):
        """Test that get_video_by_video_id returns the video when it exists."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=222222)
            result = await video_repository.get_video_by_video_id(conn, video_id=222222)

        assert result is not None
        assert result["video_id"] == 222222

    async def test_get_video_by_video_id_missing_returns_none(
        self, ensure_migrations, clean_db
    ):
        """Test that get_video_by_video_id returns None when video doesn't exist."""
        async with get_connection() as conn:
            result = await video_repository.get_video_by_video_id(conn, video_id=999)

        assert result is None

    async def test_video_exists_existing_returns_true(
        self, ensure_migrations, clean_db
    ):
        """Test that video_exists returns True when video exists."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=333333)
            exists = await video_repository.video_exists(conn, video_id=333333)

        assert exists is True

    async def test_video_exists_missing_returns_false(
        self, ensure_migrations, clean_db
    ):
        """Test that video_exists returns False when video doesn't exist."""
        async with get_connection() as conn:
            exists = await video_repository.video_exists(conn, video_id=999)

        assert exists is False


class TestVideoAssignment:
    """Tests for video assignment repository functions."""

    async def test_get_video_assigned_to_moderator_no_assignment_returns_none(
        self, ensure_migrations, clean_db
    ):
        """Moderator without assigned video returns None."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=1001)
            result = await video_repository.get_video_assigned_to_moderator(
                conn, "alice"
            )

        assert result is None

    async def test_get_next_pending_and_assign_empty_queue_returns_none(
        self, ensure_migrations, clean_db
    ):
        """Empty queue returns None when getting next pending video."""
        async with get_connection() as conn:
            result = await video_repository.get_next_pending_video_and_assign(
                conn, "alice"
            )

        assert result is None

    async def test_get_next_pending_and_assign_assigns_to_moderator(
        self, ensure_migrations, clean_db
    ):
        """Available video gets assigned to requesting moderator."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=1002)
            result = await video_repository.get_next_pending_video_and_assign(
                conn, "alice"
            )

        assert result is not None
        assert result["video_id"] == 1002
        assert result["assigned_to"] == "alice"

    async def test_get_video_assigned_to_moderator_returns_assigned(
        self, ensure_migrations, clean_db
    ):
        """Moderator with assigned video gets it returned."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=1003)
            await video_repository.get_next_pending_video_and_assign(conn, "bob")
            result = await video_repository.get_video_assigned_to_moderator(conn, "bob")

        assert result is not None
        assert result["video_id"] == 1003
        assert result["assigned_to"] == "bob"

    async def test_assignment_fifo_order(self, ensure_migrations, clean_db):
        """Videos are assigned in FIFO order (oldest first)."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=2001)
            await video_repository.insert_video(conn, video_id=2002)
            await video_repository.insert_video(conn, video_id=2003)

            first = await video_repository.get_next_pending_video_and_assign(
                conn, "alice"
            )
            second = await video_repository.get_next_pending_video_and_assign(
                conn, "bob"
            )
            third = await video_repository.get_next_pending_video_and_assign(
                conn, "charlie"
            )

        assert first["video_id"] == 2001
        assert second["video_id"] == 2002
        assert third["video_id"] == 2003


class TestUpdateVideoStatus:
    """Tests for video status update function."""

    async def test_update_status_sets_new_status(self, ensure_migrations, clean_db):
        """Update changes video status and clears assignment."""
        async with get_connection() as conn:
            await video_repository.insert_video(conn, video_id=3001)
            await video_repository.get_next_pending_video_and_assign(conn, "alice")
            result = await video_repository.update_video_status(
                conn, video_id=3001, new_status=VideoStatus.SPAM
            )

        assert result["status"] == VideoStatus.SPAM.value
        assert result["assigned_to"] is None

    async def test_update_status_nonexistent_video_returns_none(
        self, ensure_migrations, clean_db
    ):
        """Updating non-existent video returns None."""
        async with get_connection() as conn:
            result = await video_repository.update_video_status(
                conn, video_id=9999, new_status=VideoStatus.SPAM
            )

        assert result is None
