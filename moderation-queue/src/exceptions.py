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

    def __init__(self, moderator: str):
        self.moderator = moderator
        super().__init__(f"No video available for moderator '{moderator}'")


class VideoNotAssignedError(Exception):
    """Raised when moderator tries to flag a video not assigned to them."""

    def __init__(self, video_id: int, moderator: str):
        self.video_id = video_id
        self.moderator = moderator
        super().__init__(f"Video {video_id} is not assigned to {moderator}")


class VideoAlreadyModeratedError(Exception):
    """Raised when trying to flag a video that has already been moderated."""

    def __init__(self, video_id: int, current_status: str):
        self.video_id = video_id
        self.current_status = current_status
        super().__init__(
            f"Video {video_id} has already been moderated (current status: {current_status})"
        )
