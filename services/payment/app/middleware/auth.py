"""Service authentication middleware — validates X-Service-Key header."""

import hmac

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

# Endpoints that don't require service authentication (public-facing)
PUBLIC_PATHS = {
    "/health",
    "/api/v1/payments",
    "/api/v1/merchants/register",
    "/api/v1/merchants/login",
    "/api/v1/merchants/logout",
}


def _is_public_path(path: str) -> bool:
    """Check if the request path is public (no auth required)."""
    if path in PUBLIC_PATHS:
        return True
    # Health endpoints
    if path.startswith("/health"):
        return True
    if path == "/api/v1/services/health":
        return True
    # Allow simulate endpoint
    if path.startswith("/api/v1/simulate"):
        return True
    # Allow GET on /api/v1/payments/* (transaction lookup)
    if path.startswith("/api/v1/payments/") or path.startswith("/api/v1/payments?"):
        return True
    # Allow GET on /api/v1/analytics/* (dashboard)
    if path.startswith("/api/v1/analytics"):
        return True
    # Allow GET on merchant profile and POST for api-keys via session
    if path.startswith("/api/v1/merchants/"):
        return True
    return False


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate service-to-service authentication.

    Checks the X-Service-Key header against the configured service secret.
    Public-facing endpoints and /health are excluded from authentication.
    """

    def __init__(self, app: object, service_secret: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.service_secret = service_secret

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Check authentication for protected routes."""
        # Skip auth for health check and public endpoints
        if request.url.path == "/health" or _is_public_path(request.url.path):
            return await call_next(request)

        # Validate X-Service-Key header
        provided_key = request.headers.get("X-Service-Key", "")

        if not provided_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-Service-Key header."},
            )

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_key, self.service_secret):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid service key."},
            )

        return await call_next(request)
