"""Tests for video routes."""

from httpx import AsyncClient


class TestAddVideoEndpoint:
    """Tests for POST /add_video endpoint."""

    async def test_add_video_valid_request_returns_201(self, client: AsyncClient, clean_db):
        """Test that a valid request returns 201 and the video_id."""
        response = await client.post("/add_video", json={"video_id": 123456})

        assert response.status_code == 201
        assert response.json()["video_id"] == 123456

    async def test_add_video_duplicate_returns_409(self, client: AsyncClient, clean_db):
        """Test that adding a duplicate video returns 409 Conflict."""
        await client.post("/add_video", json={"video_id": 123456})

        response = await client.post("/add_video", json={"video_id": 123456})

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_add_video_negative_id_returns_422(self, client: AsyncClient):
        """Test that a negative video_id returns 422 validation error."""
        response = await client.post("/add_video", json={"video_id": -1})

        assert response.status_code == 422

    async def test_add_video_missing_id_returns_422(self, client: AsyncClient):
        """Test that a missing video_id returns 422 validation error."""
        response = await client.post("/add_video", json={})

        assert response.status_code == 422

    async def test_add_video_string_id_returns_422(self, client: AsyncClient):
        """Test that a string video_id returns 422 validation error."""
        response = await client.post("/add_video", json={"video_id": "not_a_number"})

        assert response.status_code == 422
