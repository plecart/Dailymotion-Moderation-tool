"""Application settings loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Dailymotion API Proxy configuration (env vars / .env)."""

    redis_url: str
    dailymotion_api_base_url: str
    cache_ttl_seconds: int

    model_config = {"env_file": ".env"}


settings = Settings()
