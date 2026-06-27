"""Merchant Service — FastAPI application entry point."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import get_settings
from app.middleware.auth import ServiceAuthMiddleware
from app.middleware.correlation import CorrelationMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.routes.health import router as health_router
from app.routes.merchants import router as merchants_router


def configure_logging(log_level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
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
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from app.db.session import engine
        from app.models.db_models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield

    application = FastAPI(
        title="Merchant Service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    application.add_middleware(MetricsMiddleware)
    application.add_middleware(ServiceAuthMiddleware, service_secret=settings.service_secret)
    application.add_middleware(CorrelationMiddleware)

    application.include_router(health_router)
    application.include_router(merchants_router)

    return application


app = create_app()
