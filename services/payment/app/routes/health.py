"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "service": "payment-service",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/all")
async def health_check_all() -> dict:
    """Check health of all services (for admin dashboard)."""
    import httpx
    from app.config import get_settings
    settings = get_settings()

    services = {
        "payment": {"url": "http://localhost:8001/health", "status": "healthy", "latency_ms": 0},
        "fraud": {"url": f"{settings.fraud_service_url}/health", "status": "unknown", "latency_ms": None},
        "routing": {"url": f"{settings.routing_service_url}/health", "status": "unknown", "latency_ms": None},
        "merchant": {"url": f"{settings.merchant_service_url}/health", "status": "unknown", "latency_ms": None},
        "analytics": {"url": f"{settings.analytics_service_url}/health", "status": "unknown", "latency_ms": None},
    }

    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, svc in services.items():
            if name == "payment":
                continue
            try:
                resp = await client.get(svc["url"])
                services[name]["status"] = "healthy" if resp.status_code == 200 else "unhealthy"
                services[name]["latency_ms"] = resp.elapsed.total_seconds() * 1000
            except Exception:
                services[name]["status"] = "unreachable"
                services[name]["latency_ms"] = None

    return {"services": services, "timestamp": datetime.now(timezone.utc).isoformat()}


# Also expose under /api/v1 for CloudFront routing
from fastapi import APIRouter as _AR
api_health_router = _AR()

@api_health_router.get("/api/v1/services/health")
async def api_health_check_all() -> dict:
    """Same as /health/all but under /api/v1 path for CloudFront."""
    return await health_check_all()
