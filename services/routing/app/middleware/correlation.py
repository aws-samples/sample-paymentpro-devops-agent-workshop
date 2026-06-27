"""Request correlation middleware — extracts or generates X-Request-ID."""

import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to manage request correlation IDs.

    Extracts X-Request-ID from incoming headers if present,
    otherwise generates a new UUID v4. Binds the ID to structlog
    context and includes it in the response headers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Extract or generate correlation ID and bind to logger."""
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Bind to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request state for access in route handlers
        request.state.request_id = request_id

        response = await call_next(request)

        # Include in response headers
        response.headers["X-Request-ID"] = request_id

        return response
