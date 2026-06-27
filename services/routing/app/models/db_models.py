"""SQLAlchemy database models."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class RoutingRuleDB(Base):
    """Routing rule database model."""

    __tablename__ = "routing_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    merchant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_min: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    amount_max: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("10000000.00"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    route_target: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
