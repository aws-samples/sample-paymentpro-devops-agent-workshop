"""Request metrics middleware — tracks latency and request counts."""

import time

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect request metrics.

    Records request duration and logs it with structured logging.
    In production, metrics would be published to CloudWatch.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Record request timing and status."""
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log request metrics
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        # Add timing header for debugging
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        return response
