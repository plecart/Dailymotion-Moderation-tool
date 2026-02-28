"""Business exceptions for the moderation queue domain."""


class VideoAlreadyExistsError(Exception):
    """Raised when trying to add a video that already exists."""

    def __init__(self, video_id: int):
        self.video_id = video_id
        super().__init__(f"Video {video_id} already exists in the queue")


class VideoNotFoundError(Exception):
    """Raised when a video is not found in the queue."""

    def __init__(self, video_id: int):
        self.video_id = video_id
        super().__init__(f"Video {video_id} not found")


class NoVideoAvailableError(Exception):
    """Raised when no video is available for moderation."""

    def __init__(self):
        super().__init__("No video available for moderation")
