"""Application settings loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Moderation Queue configuration (env vars / .env)."""

    database_url: str = "postgresql://moderation:moderation_secret@localhost:5432/moderation_db"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    model_config = {"env_file": ".env"}


settings = Settings()
