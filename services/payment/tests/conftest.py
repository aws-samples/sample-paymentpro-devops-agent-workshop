"""Test fixtures and configuration."""

import os

os.environ["SERVICE_SECRET"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///"
os.environ["FRAUD_SERVICE_URL"] = "http://fraud-mock"
os.environ["ROUTING_SERVICE_URL"] = "http://routing-mock"
os.environ["MERCHANT_SERVICE_URL"] = "http://merchant-mock"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models.db_models import Base

test_engine = create_async_engine("sqlite+aiosqlite:///", echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncSession:  # type: ignore[misc]
    async with test_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-Service-Key": "test-secret-key"}


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac  # type: ignore[misc]
