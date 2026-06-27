"""Test fixtures and configuration."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set required env vars before importing app
os.environ["SERVICE_SECRET"] = "test-secret-key"
os.environ["METRICS_ENABLED"] = "false"
os.environ["ENVIRONMENT"] = "test"

from app.main import app  # noqa: E402


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Headers with valid service authentication."""
    return {"X-Service-Key": "test-secret-key"}


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac  # type: ignore[misc]
