"""Pydantic schemas for analytics responses."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AnalyticsFilters(BaseModel):
    """Query filters for analytics."""

    merchant_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class TimeSeriesPoint(BaseModel):
    """Single data point in a time series."""

    date: str
    count: int


class TransactionVolumeResponse(BaseModel):
    """Transaction volume over time."""

    data: list[TimeSeriesPoint]
    total: int


class SuccessRateResponse(BaseModel):
    """Success/failure rate breakdown."""

    success_count: int
    failure_count: int
    pending_count: int
    total: int
    success_rate: float


class PaymentDistributionItem(BaseModel):
    """Payment method distribution item."""

    payment_type: str
    count: int
    percentage: float


class PaymentDistributionResponse(BaseModel):
    """Payment method distribution."""

    data: list[PaymentDistributionItem]
    total: int


class DashboardSummary(BaseModel):
    """Aggregated dashboard metrics."""

    total_transactions: int
    success_rate: float
    total_volume: Decimal
    payment_types: int
