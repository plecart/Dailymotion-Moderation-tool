"""Tests for video routes."""

import base64

from httpx import AsyncClient


def encode_moderator(name: str) -> str:
    """Helper to base64 encode moderator name."""
    return base64.b64encode(name.encode()).decode()


class TestAddVideoEndpoint:
    """Tests for POST /add_video endpoint."""

    async def test_add_video_valid_request_returns_201(
        self, client: AsyncClient, clean_db
    ):
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


class TestGetVideoEndpoint:
    """Tests for GET /get_video endpoint."""

    async def test_missing_auth_header_returns_422(self, client: AsyncClient):
        """Request without Authorization header returns 422."""
        response = await client.get("/get_video")

        assert response.status_code == 422

    async def test_invalid_base64_returns_401(self, client: AsyncClient):
        """Invalid base64 Authorization header returns 401."""
        response = await client.get(
            "/get_video", headers={"Authorization": "not-valid-base64!!!"}
        )

        assert response.status_code == 401
        assert "Invalid Authorization" in response.json()["detail"]

    async def test_empty_queue_returns_404(self, client: AsyncClient, clean_db):
        """Empty queue returns 404 No video available."""
        response = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )

        assert response.status_code == 404
        assert "No video available" in response.json()["detail"]

    async def test_valid_request_returns_video(self, client: AsyncClient, clean_db):
        """Valid request with pending video returns 200 with video_id."""
        await client.post("/add_video", json={"video_id": 7001})

        response = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )

        assert response.status_code == 200
        assert response.json()["video_id"] == 7001

    async def test_same_moderator_gets_same_video(self, client: AsyncClient, clean_db):
        """Same moderator receives same video on repeated calls."""
        await client.post("/add_video", json={"video_id": 7002})

        first = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("bob")}
        )
        second = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("bob")}
        )

        assert first.json()["video_id"] == second.json()["video_id"] == 7002

    async def test_different_moderators_get_different_videos(
        self, client: AsyncClient, clean_db
    ):
        """Different moderators receive different videos."""
        await client.post("/add_video", json={"video_id": 7003})
        await client.post("/add_video", json={"video_id": 7004})

        alice = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )
        bob = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("bob")}
        )

        assert alice.json()["video_id"] != bob.json()["video_id"]
        video_ids = {alice.json()["video_id"], bob.json()["video_id"]}
        assert video_ids == {7003, 7004}

    async def test_second_moderator_no_video_if_all_assigned(
        self, client: AsyncClient, clean_db
    ):
        """Second moderator gets 404 if single video already assigned."""
        await client.post("/add_video", json={"video_id": 7005})
        await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )

        response = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("bob")}
        )

        assert response.status_code == 404


class TestFlagVideoEndpoint:
    """Tests for POST /flag_video endpoint."""

    async def test_missing_auth_header_returns_422(self, client: AsyncClient):
        """Request without Authorization header returns 422."""
        response = await client.post(
            "/flag_video", json={"video_id": 1, "status": "spam"}
        )

        assert response.status_code == 422

    async def test_invalid_status_returns_422(self, client: AsyncClient, clean_db):
        """Invalid status value returns 422 validation error."""
        response = await client.post(
            "/flag_video",
            json={"video_id": 1, "status": "invalid"},
            headers={"Authorization": encode_moderator("alice")},
        )

        assert response.status_code == 422

    async def test_nonexistent_video_returns_404(self, client: AsyncClient, clean_db):
        """Flag non-existent video returns 404."""
        response = await client.post(
            "/flag_video",
            json={"video_id": 9999, "status": "spam"},
            headers={"Authorization": encode_moderator("alice")},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_video_not_assigned_returns_403(self, client: AsyncClient, clean_db):
        """Flag video not assigned to moderator returns 403."""
        await client.post("/add_video", json={"video_id": 8001})
        await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )

        response = await client.post(
            "/flag_video",
            json={"video_id": 8001, "status": "spam"},
            headers={"Authorization": encode_moderator("bob")},
        )

        assert response.status_code == 403
        assert "not assigned to you" in response.json()["detail"]

    async def test_already_moderated_video_returns_409(self, client: AsyncClient, clean_db):
        """Flag already moderated video returns 409 Conflict."""
        await client.post("/add_video", json={"video_id": 8006})
        await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )
        await client.post(
            "/flag_video",
            json={"video_id": 8006, "status": "spam"},
            headers={"Authorization": encode_moderator("alice")},
        )

        response = await client.post(
            "/flag_video",
            json={"video_id": 8006, "status": "not spam"},
            headers={"Authorization": encode_moderator("alice")},
        )

        assert response.status_code == 409
        assert "already been moderated" in response.json()["detail"]

    async def test_flag_spam_returns_200(self, client: AsyncClient, clean_db):
        """Flag video as spam returns 200 with updated status."""
        await client.post("/add_video", json={"video_id": 8002})
        await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )

        response = await client.post(
            "/flag_video",
            json={"video_id": 8002, "status": "spam"},
            headers={"Authorization": encode_moderator("alice")},
        )

        assert response.status_code == 200
        assert response.json()["video_id"] == 8002
        assert response.json()["status"] == "spam"

    async def test_flag_not_spam_returns_200(self, client: AsyncClient, clean_db):
        """Flag video as not spam returns 200 with updated status."""
        await client.post("/add_video", json={"video_id": 8003})
        await client.get(
            "/get_video", headers={"Authorization": encode_moderator("bob")}
        )

        response = await client.post(
            "/flag_video",
            json={"video_id": 8003, "status": "not spam"},
            headers={"Authorization": encode_moderator("bob")},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "not spam"

    async def test_flag_frees_moderator_for_next_video(
        self, client: AsyncClient, clean_db
    ):
        """After flagging, moderator can get next video."""
        await client.post("/add_video", json={"video_id": 8004})
        await client.post("/add_video", json={"video_id": 8005})

        await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )
        await client.post(
            "/flag_video",
            json={"video_id": 8004, "status": "spam"},
            headers={"Authorization": encode_moderator("alice")},
        )

        response = await client.get(
            "/get_video", headers={"Authorization": encode_moderator("alice")}
        )

        assert response.status_code == 200
        assert response.json()["video_id"] == 8005
