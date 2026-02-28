"""Business exceptions for Dailymotion API Proxy."""


class VideoNotFoundError(Exception):
    """Raised when a video is not found according to business rules (not for upstream API 404s)."""

    def __init__(self, video_id: int):
        self.video_id = video_id
        super().__init__(f"Video {video_id} not found")


class DailymotionAPIError(Exception):
    """Raised when Dailymotion API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)
