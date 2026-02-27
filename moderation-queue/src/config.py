"""Application settings loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Moderation Queue configuration (env vars / .env)."""

    database_url: str
    # PostgreSQL advisory lock key for migration runner (must fit int64). Override in .env if multiple apps share the same DB.
    migration_lock_key: int = 0x646D5F6D69677261
    # Max seconds to wait for the migration lock before failing startup (avoids indefinite hang).
    migration_lock_timeout_seconds: int = 60

    model_config = {"env_file": ".env"}


settings = Settings()
