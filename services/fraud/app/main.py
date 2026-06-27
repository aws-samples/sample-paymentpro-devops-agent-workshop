"""Fraud Service — FastAPI application entry point."""

import structlog
from fastapi import FastAPI

from app.config import get_settings
from app.middleware.auth import ServiceAuthMiddleware
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.routes.health import router as health_router
from app.routes.validation import router as validation_router


def configure_logging(log_level: str) -> None:
    """Configure structlog for structured JSON logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.stdlib.NAME_TO_LEVEL.get(log_level.lower(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    configure_logging(settings.log_level)

    application = FastAPI(
        title="Fraud Service",
        description="Payment input validation microservice",
        version="1.0.0",
        docs_url="/docs" if settings.environment == "dev" else None,
        redoc_url="/redoc" if settings.environment == "dev" else None,
    )

    # Add middleware (order matters: outermost first)
    # Metrics wraps everything to capture full request time
    application.add_middleware(MetricsMiddleware)
    # Auth checks before reaching route handlers
    application.add_middleware(ServiceAuthMiddleware, service_secret=settings.service_secret)
    # Correlation ID extracted/generated first
    application.add_middleware(CorrelationMiddleware)

    # Register routes
    application.include_router(health_router)
    application.include_router(validation_router)

    return application


app = create_app()
