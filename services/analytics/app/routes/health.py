"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app import __version__
from app.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint for ECS ALB — includes DB connectivity.

    Uses a disposable engine with a short connect timeout to detect
    network-level failures (e.g., removed security group rules) even
    when the main connection pool still has established connections.
    """
    settings = get_settings()
    try:
        health_engine = create_async_engine(
            settings.effective_database_url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=False,
            connect_args={"command_timeout": 3, "timeout": 3},
        )
        async with health_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await health_engine.dispose()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "analytics-service",
                "version": __version__,
                "reason": "database connection failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return JSONResponse(content={
        "status": "healthy",
        "service": "analytics-service",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
