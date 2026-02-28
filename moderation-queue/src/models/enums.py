"""Enumerations for the moderation queue domain."""

from enum import Enum


class VideoStatus(str, Enum):
    """Status of a video in the moderation queue."""

    PENDING = "pending"
    SPAM = "spam"
    NOT_SPAM = "not spam"
