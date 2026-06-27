"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for ECS ALB."""
    return {
        "status": "healthy",
        "service": "merchant-service",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
