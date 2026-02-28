"""Moderation Queue API: FastAPI app and lifespan."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database.connection import close_pool, create_pool
from src.database.migrations import run_migrations
from src.routes import videos

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan: DB pool creation, migrations, and cleanup."""
    logger.info("Moderation Queue API starting")
    try:
        await create_pool()
        await run_migrations()
        yield
    finally:
        logger.info("Moderation Queue API shutting down")
        await close_pool()


app = FastAPI(
    title="Moderation Queue API",
    description="Backend service for video moderation queue management",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(videos.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}
