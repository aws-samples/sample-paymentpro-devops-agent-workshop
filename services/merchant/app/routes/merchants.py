"""Merchant API endpoints — registration, auth, API keys."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import (
    ApiKeyResponse,
    ApiKeyValidationResult,
    LoginRequest,
    MerchantProfile,
    MerchantRegisterRequest,
    SessionResponse,
)
from app.services.merchant_service import (
    generate_api_key,
    get_merchant_profile,
    login,
    logout,
    register_merchant,
    revoke_api_key,
    validate_api_key,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])


# --- STATIC ROUTES FIRST (before {merchant_id} catch-all) ---

@router.post("/register", response_model=MerchantProfile, status_code=201)
async def register_endpoint(
    data: MerchantRegisterRequest, db: AsyncSession = Depends(get_db)
) -> MerchantProfile:
    """Register a new merchant."""
    result = await register_merchant(data, db)
    if not result:
        raise HTTPException(status_code=409, detail="Email already registered")
    return result


@router.post("/login", response_model=SessionResponse)
async def login_endpoint(
    credentials: LoginRequest, db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    """Authenticate merchant and create session."""
    result = await login(credentials, db)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


@router.post("/logout")
async def logout_endpoint(session_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Destroy a merchant session."""
    success = await logout(session_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Logged out successfully"}


@router.post("/validate-key", response_model=ApiKeyValidationResult)
async def validate_api_key_endpoint(
    api_key: str, db: AsyncSession = Depends(get_db)
) -> ApiKeyValidationResult:
    """Validate an API key (called by Payment Service)."""
    return await validate_api_key(api_key, db)


@router.get("/stats/summary")
async def merchant_stats_endpoint(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get merchant statistics for admin dashboard."""
    from sqlalchemy import select, func
    from app.models.db_models import MerchantDB
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    total_result = await db.execute(select(func.count()).select_from(MerchantDB))
    total = total_result.scalar() or 0

    active_result = await db.execute(select(func.count()).select_from(MerchantDB).where(MerchantDB.status == "ACTIVE"))
    active = active_result.scalar() or 0

    hour_ago = now - timedelta(hours=1)
    recent_result = await db.execute(select(func.count()).select_from(MerchantDB).where(MerchantDB.created_at >= hour_ago))
    last_hour = recent_result.scalar() or 0

    day_ago = now - timedelta(hours=24)
    day_result = await db.execute(select(func.count()).select_from(MerchantDB).where(MerchantDB.created_at >= day_ago))
    last_24h = day_result.scalar() or 0

    week_ago = now - timedelta(days=7)
    daily_stmt = select(
        func.date(MerchantDB.created_at).label("date"),
        func.count().label("count"),
    ).where(MerchantDB.created_at >= week_ago).group_by(func.date(MerchantDB.created_at)).order_by("date")
    daily_result = await db.execute(daily_stmt)
    daily_signups = [{"date": str(r.date), "count": r.count} for r in daily_result.all()]

    return {
        "total_merchants": total,
        "active_merchants": active,
        "last_hour": last_hour,
        "last_24h": last_24h,
        "daily_signups": daily_signups,
    }


@router.get("/list", response_model=list[MerchantProfile])
async def list_merchants_endpoint(
    db: AsyncSession = Depends(get_db),
) -> list[MerchantProfile]:
    """List all merchants."""
    from sqlalchemy import select
    from app.models.db_models import MerchantDB
    stmt = select(MerchantDB).order_by(MerchantDB.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    merchants = result.scalars().all()
    return [MerchantProfile.model_validate(m) for m in merchants]


# --- DYNAMIC ROUTES (with {merchant_id} path param) ---

@router.get("/{merchant_id}", response_model=MerchantProfile)
async def get_profile_endpoint(
    merchant_id: str, db: AsyncSession = Depends(get_db)
) -> MerchantProfile:
    """Get merchant profile."""
    result = await get_merchant_profile(merchant_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.post("/{merchant_id}/api-keys", response_model=ApiKeyResponse, status_code=201)
async def generate_api_key_endpoint(
    merchant_id: str, db: AsyncSession = Depends(get_db)
) -> ApiKeyResponse:
    """Generate a new API key for a merchant."""
    result = await generate_api_key(merchant_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.get("/{merchant_id}/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys_endpoint(
    merchant_id: str, db: AsyncSession = Depends(get_db)
) -> list[ApiKeyResponse]:
    """List active API keys for a merchant."""
    from sqlalchemy import select
    from app.models.db_models import ApiKeyDB
    stmt = select(ApiKeyDB).where(ApiKeyDB.merchant_id == merchant_id, ApiKeyDB.status == "ACTIVE")
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/{merchant_id}/api-keys/{key_id}", status_code=204)
async def revoke_api_key_endpoint(
    merchant_id: str, key_id: str, db: AsyncSession = Depends(get_db)
) -> None:
    """Revoke an API key."""
    success = await revoke_api_key(merchant_id, key_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
