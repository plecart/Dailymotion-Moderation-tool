"""Tests for dependency injection functions."""

import base64

import pytest
from fastapi import HTTPException

from src.dependencies import get_moderator


class TestGetModerator:
    """Tests for base64 authentication dependency."""

    def test_valid_base64_decodes_moderator_name(self):
        """Valid base64 input returns decoded moderator name."""
        moderator_name = "john.doe"
        encoded = base64.b64encode(moderator_name.encode()).decode()

        result = get_moderator(encoded)

        assert result == "john.doe"

    def test_unicode_moderator_name_decoded_correctly(self):
        """Unicode characters in moderator name are decoded correctly."""
        moderator_name = "modérateur_français"
        encoded = base64.b64encode(moderator_name.encode()).decode()

        result = get_moderator(encoded)

        assert result == "modérateur_français"

    def test_invalid_base64_raises_401(self):
        """Invalid base64 string raises HTTP 401."""
        with pytest.raises(HTTPException) as exc_info:
            get_moderator("not-valid-base64!!!")

        assert exc_info.value.status_code == 401
        assert "Invalid Authorization header" in exc_info.value.detail

    def test_empty_decoded_string_raises_401(self):
        """Empty string after decoding raises HTTP 401."""
        encoded = base64.b64encode(b"   ").decode()

        with pytest.raises(HTTPException) as exc_info:
            get_moderator(encoded)

        assert exc_info.value.status_code == 401
