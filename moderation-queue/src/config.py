"""Application settings loaded from environment."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Moderation Queue configuration (env vars / .env)."""

    database_url: str
    # PostgreSQL connection pool settings
    # min_size: Minimum number of connections kept open at all times (default: 2)
    database_pool_min_size: int = 2
    # max_size: Maximum number of concurrent connections allowed (default: 10)
    database_pool_max_size: int = 10
    # PostgreSQL advisory lock key for migration runner (must fit int64). Override in .env if multiple apps share the same DB.
    migration_lock_key: int = 0x646D5F6D69677261
    # Max seconds to wait for the migration lock before failing startup (avoids indefinite hang).
    migration_lock_timeout_seconds: int = 60
    # Base key for moderator-scoped advisory locks (must fit int64). Override in .env if multiple apps share the same DB.
    moderator_lock_base_key: int = 0x6D6F645F6C6F636B  # "mod_lock" in hex

    model_config = {"env_file": ".env"}


settings = Settings()
