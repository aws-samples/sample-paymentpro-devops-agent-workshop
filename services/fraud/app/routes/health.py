"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for ECS ALB.

    Returns service status, version, and current timestamp.
    No authentication required.
    """
    return {
        "status": "healthy",
        "service": "fraud-service",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
