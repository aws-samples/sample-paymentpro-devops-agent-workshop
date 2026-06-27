"""Proxy routes — forwards merchant and analytics requests to internal services."""

import httpx
import structlog
from fastapi import APIRouter, Request, Response

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


async def _proxy_request(request: Request, target_base_url: str) -> Response:
    """Forward a request to an internal service."""
    # Build target URL
    path = request.url.path
    query = str(request.url.query)
    target_url = f"{target_base_url}{path}"
    if query:
        target_url += f"?{query}"

    # Forward the request
    async with httpx.AsyncClient(timeout=10.0) as client:
        body = await request.body()
        headers = {
            "Content-Type": request.headers.get("content-type", "application/json"),
            "X-Service-Key": settings.service_secret,
        }
        # Forward X-Request-ID if present
        if "x-request-id" in request.headers:
            headers["X-Request-ID"] = request.headers["x-request-id"]

        response = await client.request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.headers.get("content-type"),
    )


@router.api_route("/api/v1/merchants/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_merchants(request: Request, path: str) -> Response:
    """Proxy merchant requests to the Merchant Service."""
    return await _proxy_request(request, settings.merchant_service_url)


@router.api_route("/api/v1/analytics/{path:path}", methods=["GET"])
async def proxy_analytics(request: Request, path: str) -> Response:
    """Proxy analytics requests to the Analytics Service."""
    return await _proxy_request(request, settings.analytics_service_url)
