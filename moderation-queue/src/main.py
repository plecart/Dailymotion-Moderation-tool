"""Moderation Queue API: FastAPI app and lifespan."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan: startup (e.g. DB pool) and shutdown."""
    logger.info("Moderation Queue API starting")
    yield
    logger.info("Moderation Queue API shutting down")


app = FastAPI(
    title="Moderation Queue API",
    description="Backend service for video moderation queue management",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
