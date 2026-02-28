"""Dailymotion API Proxy: FastAPI app and lifespan."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.cache.redis_client import close_redis_client, create_redis_client
from src.clients.dailymotion_client import close_http_client, create_http_client
from src.routes import videos

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan: startup Redis and HTTP client, shutdown cleanup."""
    logger.info("Dailymotion API Proxy starting")
    try:
        await create_redis_client()
        await create_http_client()
        yield
    finally:
        logger.info("Dailymotion API Proxy shutting down")
        await close_http_client()
        await close_redis_client()


app = FastAPI(
    title="Dailymotion API Proxy",
    description="Proxy service for Dailymotion API with Redis caching",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(videos.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
