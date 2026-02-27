"""Application settings loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Moderation Queue configuration (env vars / .env)."""

    database_url: str

    model_config = {"env_file": ".env"}


settings = Settings()
