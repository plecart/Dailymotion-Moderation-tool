"""Pydantic schemas for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.enums import VideoStatus


class AddVideoRequest(BaseModel):
    """Request schema for adding a video to the moderation queue."""

    video_id: int = Field(..., gt=0, description="Unique video identifier")


class AddVideoResponse(BaseModel):
    """Response schema after adding a video."""

    video_id: int


class VideoResponse(BaseModel):
    """Response schema for a video in the queue."""

    video_id: int


class FlagVideoRequest(BaseModel):
    """Request schema for flagging a video."""

    video_id: int = Field(..., gt=0)
    status: VideoStatus = Field(..., description="New status: 'spam' or 'not spam'")


class FlagVideoResponse(BaseModel):
    """Response schema after flagging a video."""

    video_id: int
    status: str


class StatsResponse(BaseModel):
    """Response schema for queue statistics."""

    total_pending_videos: int
    total_spam_videos: int
    total_not_spam_videos: int


class ModerationLogEntry(BaseModel):
    """A single entry in the moderation history."""

    date: datetime
    status: str
    moderator: str | None


class VideoInDB(BaseModel):
    """Internal representation of a video record from database."""

    id: int
    video_id: int
    status: VideoStatus
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
