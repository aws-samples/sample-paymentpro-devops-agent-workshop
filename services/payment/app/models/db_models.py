"""SQLAlchemy database models for transactions."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransactionDB(Base):
    """Payment transaction record."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    route_target: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
