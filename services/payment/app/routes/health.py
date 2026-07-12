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
        # Create a short-lived engine with a 3-second connect timeout
        # This ensures we actually test NEW connectivity, not reuse pooled conns
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
                "service": "payment-service",
                "version": __version__,
                "reason": "database connection failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return JSONResponse(content={
        "status": "healthy",
        "service": "payment-service",
        "version": __version__,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


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
