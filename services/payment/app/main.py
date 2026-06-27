"""Payment Service — FastAPI application entry point."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import get_settings
from app.middleware.auth import ServiceAuthMiddleware
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.routes.health import router as health_router, api_health_router
from app.routes.payments import router as payments_router
from app.routes.proxy import router as proxy_router
from app.routes.simulate import router as simulate_router


def configure_logging(log_level: str) -> None:
    """Configure structlog."""
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

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Create tables on startup, then run any idempotent forward-migrations.
        # `Base.metadata.create_all` only creates tables that don't yet exist;
        # it never adds columns to existing tables. The ALTER statements below
        # cover the case where an older schema was created by an earlier
        # deploy or by a peer service with a stale model. Each statement uses
        # `IF NOT EXISTS` (PostgreSQL 9.6+) so it's safe to run on every boot.
        from sqlalchemy import text
        from app.db.session import engine
        from app.models.db_models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text(
                "ALTER TABLE transactions "
                "ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(500)"
            ))
        yield

    application = FastAPI(
        title="Payment Service",
        description="Payment processing orchestrator",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )

    application.add_middleware(MetricsMiddleware)
    application.add_middleware(ServiceAuthMiddleware, service_secret=settings.service_secret)
    application.add_middleware(CorrelationMiddleware)

    application.include_router(health_router)
    application.include_router(api_health_router)
    application.include_router(payments_router)
    application.include_router(simulate_router)
    application.include_router(proxy_router)

    return application


app = create_app()
