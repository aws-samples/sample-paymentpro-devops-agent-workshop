"""Health check endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app import __version__

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "analytics-service",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
