"""Test fixtures and configuration."""

import os

os.environ.setdefault("SERVICE_SECRET", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models.db_models import Base


# Use in-memory SQLite for tests
test_engine = create_async_engine("sqlite+aiosqlite:///", echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncSession:  # type: ignore[misc]
    """Override database dependency with test database."""
    async with test_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers with valid service authentication."""
    return {"X-Service-Key": "test-secret-key"}


@pytest.fixture
async def client() -> AsyncClient:
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac  # type: ignore[misc]


@pytest.fixture
async def db_session() -> AsyncSession:
    """Direct database session for test setup."""
    async with test_session_factory() as session:
        yield session  # type: ignore[misc]
