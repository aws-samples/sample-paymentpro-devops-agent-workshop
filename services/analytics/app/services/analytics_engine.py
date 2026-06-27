"""Analytics engine — queries transaction data for dashboard metrics."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import TransactionDB
from app.models.schemas import (
    AnalyticsFilters,
    DashboardSummary,
    PaymentDistributionItem,
    PaymentDistributionResponse,
    SuccessRateResponse,
    TimeSeriesPoint,
    TransactionVolumeResponse,
)


def _apply_filters(stmt, filters: AnalyticsFilters):  # type: ignore[no-untyped-def]
    """Apply common filters to a query."""
    if filters.merchant_id:
        stmt = stmt.where(TransactionDB.merchant_id == filters.merchant_id)
    if filters.date_from:
        stmt = stmt.where(TransactionDB.created_at >= datetime.combine(filters.date_from, datetime.min.time(), tzinfo=timezone.utc))
    if filters.date_to:
        stmt = stmt.where(TransactionDB.created_at <= datetime.combine(filters.date_to, datetime.max.time(), tzinfo=timezone.utc))
    return stmt


async def get_transaction_volume(
    filters: AnalyticsFilters, db: AsyncSession
) -> TransactionVolumeResponse:
    """Get transaction count grouped by date."""
    # Use func.date() which works across SQLite and PostgreSQL
    stmt = select(
        func.date(TransactionDB.created_at).label("date"),
        func.count().label("count"),
    )
    stmt = _apply_filters(stmt, filters)
    stmt = stmt.group_by(func.date(TransactionDB.created_at)).order_by("date")

    result = await db.execute(stmt)
    rows = result.all()

    data = [TimeSeriesPoint(date=str(row.date), count=row.count) for row in rows]
    total = sum(p.count for p in data)

    return TransactionVolumeResponse(data=data, total=total)


async def get_success_rates(
    filters: AnalyticsFilters, db: AsyncSession
) -> SuccessRateResponse:
    """Get success/failure/pending counts and rate."""
    base_stmt = select(TransactionDB.status, func.count().label("count"))
    base_stmt = _apply_filters(base_stmt, filters)
    base_stmt = base_stmt.group_by(TransactionDB.status)

    result = await db.execute(base_stmt)
    rows = result.all()

    counts = {row.status: row.count for row in rows}
    success = counts.get("SUCCESS", 0)
    failure = counts.get("FAILED", 0)
    pending = counts.get("PENDING", 0)
    total = success + failure + pending

    return SuccessRateResponse(
        success_count=success,
        failure_count=failure,
        pending_count=pending,
        total=total,
        success_rate=round(success / total * 100, 2) if total > 0 else 0.0,
    )


async def get_payment_distribution(
    filters: AnalyticsFilters, db: AsyncSession
) -> PaymentDistributionResponse:
    """Get payment method distribution."""
    stmt = select(TransactionDB.payment_type, func.count().label("count"))
    stmt = _apply_filters(stmt, filters)
    stmt = stmt.group_by(TransactionDB.payment_type)

    result = await db.execute(stmt)
    rows = result.all()

    total = sum(row.count for row in rows)
    data = [
        PaymentDistributionItem(
            payment_type=row.payment_type,
            count=row.count,
            percentage=round(row.count / total * 100, 2) if total > 0 else 0.0,
        )
        for row in rows
    ]

    return PaymentDistributionResponse(data=data, total=total)


async def get_dashboard_summary(
    filters: AnalyticsFilters, db: AsyncSession
) -> DashboardSummary:
    """Get aggregated dashboard metrics."""
    stmt = select(
        func.count().label("total"),
        func.sum(TransactionDB.amount).label("volume"),
        func.count(func.distinct(TransactionDB.payment_type)).label("types"),
    )
    stmt = _apply_filters(stmt, filters)
    result = await db.execute(stmt)
    row = result.one()

    total = row.total or 0
    volume = row.volume or Decimal("0.00")
    types = row.types or 0

    # Get success count for rate
    success_stmt = select(func.count()).where(TransactionDB.status == "SUCCESS")
    success_stmt = _apply_filters(success_stmt, filters)
    success_result = await db.execute(success_stmt)
    success_count = success_result.scalar() or 0

    success_rate = round(success_count / total * 100, 2) if total > 0 else 0.0

    return DashboardSummary(
        total_transactions=total,
        success_rate=success_rate,
        total_volume=volume,
        payment_types=types,
    )
