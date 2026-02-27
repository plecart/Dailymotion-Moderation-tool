"""Dailymotion API Proxy: FastAPI app and lifespan."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan: startup (e.g. Redis) and shutdown."""
    logger.info("Dailymotion API Proxy starting")
    yield
    logger.info("Dailymotion API Proxy shutting down")


app = FastAPI(
    title="Dailymotion API Proxy",
    description="Proxy service for Dailymotion API with Redis caching",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
