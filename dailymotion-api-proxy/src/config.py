"""Application settings loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Dailymotion API Proxy configuration (env vars / .env)."""

    redis_url: str = "redis://localhost:6379/0"
    dailymotion_api_base_url: str = "https://api.dailymotion.com"
    cache_ttl_seconds: int = 300
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
