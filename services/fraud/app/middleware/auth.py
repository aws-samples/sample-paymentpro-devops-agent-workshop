"""Service authentication middleware — validates X-Service-Key header."""

import hmac

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate service-to-service authentication.

    Checks the X-Service-Key header against the configured service secret.
    The /health endpoint is excluded from authentication.
    """

    def __init__(self, app: object, service_secret: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.service_secret = service_secret

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Check authentication for protected routes."""
        # Skip auth for health check
        if request.url.path == "/health":
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
