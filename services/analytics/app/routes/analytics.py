"""Analytics API endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import (
    AnalyticsFilters,
    DashboardSummary,
    PaymentDistributionResponse,
    SuccessRateResponse,
    TransactionVolumeResponse,
)
from app.services.analytics_engine import (
    get_dashboard_summary,
    get_payment_distribution,
    get_success_rates,
    get_transaction_volume,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _build_filters(
    merchant_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> AnalyticsFilters:
    return AnalyticsFilters(merchant_id=merchant_id, date_from=date_from, date_to=date_to)


@router.get("/volume", response_model=TransactionVolumeResponse)
async def get_volume_endpoint(
    merchant_id: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> TransactionVolumeResponse:
    """Get transaction volume over time."""
    filters = _build_filters(merchant_id, date_from, date_to)
    return await get_transaction_volume(filters, db)


@router.get("/success-rates", response_model=SuccessRateResponse)
async def get_success_rates_endpoint(
    merchant_id: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> SuccessRateResponse:
    """Get success/failure rate breakdown."""
    filters = _build_filters(merchant_id, date_from, date_to)
    return await get_success_rates(filters, db)


@router.get("/distribution", response_model=PaymentDistributionResponse)
async def get_distribution_endpoint(
    merchant_id: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> PaymentDistributionResponse:
    """Get payment method distribution."""
    filters = _build_filters(merchant_id, date_from, date_to)
    return await get_payment_distribution(filters, db)


@router.get("/summary", response_model=DashboardSummary)
async def get_summary_endpoint(
    merchant_id: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    """Get aggregated dashboard metrics."""
    filters = _build_filters(merchant_id, date_from, date_to)
    return await get_dashboard_summary(filters, db)
