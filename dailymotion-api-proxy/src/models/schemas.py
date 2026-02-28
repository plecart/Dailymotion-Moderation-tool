"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel


class VideoInfoResponse(BaseModel):
    """Response schema for video information."""

    title: str
    channel: str
    owner: str
    filmstrip_60_url: str | None = None
    embed_url: str
