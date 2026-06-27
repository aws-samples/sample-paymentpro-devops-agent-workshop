"""Merchant registration, authentication, and API key management."""

import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.db_models import ApiKeyDB, MerchantDB, SessionDB
from app.models.schemas import (
    ApiKeyResponse,
    ApiKeyValidationResult,
    LoginRequest,
    MerchantProfile,
    MerchantRegisterRequest,
    SessionResponse,
)

logger = structlog.get_logger()
settings = get_settings()


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _generate_api_key() -> str:
    """Generate a random API key."""
    return secrets.token_hex(settings.api_key_length // 2)


async def register_merchant(
    data: MerchantRegisterRequest, db: AsyncSession
) -> MerchantProfile | None:
    """Register a new merchant. Returns None if email already exists."""
    # Check for existing email
    stmt = select(MerchantDB).where(MerchantDB.email == data.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return None  # Email already exists

    merchant = MerchantDB(
        id=str(uuid4()),
        business_name=data.business_name,
        email=data.email,
        password_hash=_hash_password(data.password),
        contact=data.contact,
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
    )
    db.add(merchant)
    await db.commit()
    await db.refresh(merchant)
    logger.info("merchant_registered", merchant_id=merchant.id)
    return MerchantProfile.model_validate(merchant)


async def login(credentials: LoginRequest, db: AsyncSession) -> SessionResponse | None:
    """Authenticate merchant and create session. Returns None if invalid."""
    stmt = select(MerchantDB).where(MerchantDB.email == credentials.email)
    result = await db.execute(stmt)
    merchant = result.scalar_one_or_none()

    if not merchant or not _verify_password(credentials.password, merchant.password_hash):
        return None

    # Create session
    session = SessionDB(
        id=str(uuid4()),
        merchant_id=merchant.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_duration_hours),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.commit()
    logger.info("merchant_login", merchant_id=merchant.id)

    return SessionResponse(
        session_id=session.id,
        merchant_id=merchant.id,
        expires_at=session.expires_at,
    )


async def logout(session_id: str, db: AsyncSession) -> bool:
    """Destroy a session. Returns False if not found."""
    stmt = select(SessionDB).where(SessionDB.id == session_id, SessionDB.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        return False

    session.is_active = False
    await db.commit()
    logger.info("merchant_logout", session_id=session_id)
    return True


async def generate_api_key(merchant_id: str, db: AsyncSession) -> ApiKeyResponse | None:
    """Generate a new API key for a merchant."""
    # Verify merchant exists
    stmt = select(MerchantDB).where(MerchantDB.id == merchant_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        return None

    api_key = ApiKeyDB(
        id=str(uuid4()),
        merchant_id=merchant_id,
        key_value=_generate_api_key(),
        label="primary",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    logger.info("api_key_generated", merchant_id=merchant_id, key_id=api_key.id)
    return ApiKeyResponse.model_validate(api_key)


async def revoke_api_key(merchant_id: str, key_id: str, db: AsyncSession) -> bool:
    """Revoke an API key. Returns False if not found."""
    stmt = select(ApiKeyDB).where(
        ApiKeyDB.id == key_id,
        ApiKeyDB.merchant_id == merchant_id,
        ApiKeyDB.status == "ACTIVE",
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        return False

    api_key.status = "REVOKED"
    await db.commit()
    logger.info("api_key_revoked", merchant_id=merchant_id, key_id=key_id)
    return True


async def validate_api_key(api_key_value: str, db: AsyncSession) -> ApiKeyValidationResult:
    """Validate an API key. Returns merchant_id if valid."""
    stmt = select(ApiKeyDB).where(
        ApiKeyDB.key_value == api_key_value,
        ApiKeyDB.status == "ACTIVE",
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        return ApiKeyValidationResult(valid=False, merchant_id=None)

    return ApiKeyValidationResult(valid=True, merchant_id=api_key.merchant_id)


async def get_merchant_profile(merchant_id: str, db: AsyncSession) -> MerchantProfile | None:
    """Get merchant profile by ID."""
    stmt = select(MerchantDB).where(MerchantDB.id == merchant_id)
    result = await db.execute(stmt)
    merchant = result.scalar_one_or_none()
    if not merchant:
        return None
    return MerchantProfile.model_validate(merchant)
