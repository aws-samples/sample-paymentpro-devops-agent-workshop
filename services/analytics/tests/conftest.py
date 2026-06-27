"""Test fixtures."""

import os
from datetime import datetime, timezone
from decimal import Decimal

os.environ.setdefault("SERVICE_SECRET", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import get_db
from app.main import app
from app.models.db_models import Base, TransactionDB

test_engine = create_async_engine("sqlite+aiosqlite:///", echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncSession:  # type: ignore[misc]
    async with test_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-Service-Key": "test-secret-key"}


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac  # type: ignore[misc]


@pytest.fixture
async def seed_transactions():
    """Seed test transactions."""
    now = datetime.now(timezone.utc)
    async with test_session_factory() as session:
        transactions = [
            TransactionDB(id="txn-1", merchant_id="m1", payment_type="UPI", amount=Decimal("100.00"), currency="INR", status="SUCCESS", created_at=now, updated_at=now),
            TransactionDB(id="txn-2", merchant_id="m1", payment_type="CREDIT_CARD", amount=Decimal("500.00"), currency="INR", status="SUCCESS", created_at=now, updated_at=now),
            TransactionDB(id="txn-3", merchant_id="m1", payment_type="UPI", amount=Decimal("200.00"), currency="INR", status="FAILED", created_at=now, updated_at=now),
            TransactionDB(id="txn-4", merchant_id="m2", payment_type="WALLET", amount=Decimal("50.00"), currency="INR", status="SUCCESS", created_at=now, updated_at=now),
        ]
        session.add_all(transactions)
        await session.commit()
