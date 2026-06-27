"""Payment processing orchestrator — coordinates validation, routing, and outcome."""

import random
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.service_clients import call_fraud_service, call_routing_service
from app.config import get_settings
from app.models.db_models import TransactionDB
from app.models.schemas import (
    PaginatedTransactions,
    PaymentRequest,
    PaymentResponse,
    TransactionDetail,
    TransactionFilters,
)

logger = structlog.get_logger()
settings = get_settings()


async def process_payment(request: PaymentRequest, db: AsyncSession) -> PaymentResponse:
    """Process a payment request through the full pipeline.

    Pipeline:
    1. Validate inputs via Fraud Service
    2. Get route via Routing Service
    3. Simulate payment outcome
    4. Store transaction record
    """
    transaction_id = str(uuid4())
    now = datetime.now(timezone.utc)

    # Create initial transaction record (PENDING)
    transaction = TransactionDB(
        id=transaction_id,
        merchant_id=request.merchant_id,
        payment_type=request.payment_type.value,
        amount=request.amount,
        currency=request.currency,
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    db.add(transaction)
    await db.commit()

    # Step 1: Validate via Fraud Service
    try:
        validation_payload = {
            "payment_type": request.payment_type.value,
            "amount": str(request.amount),
            "merchant_id": request.merchant_id,
            "card_number": request.card_number,
            "card_expiry": request.card_expiry,
            "cvv": request.cvv,
            "upi_id": request.upi_id,
            "wallet_id": request.wallet_id,
            "wallet_balance": str(request.wallet_balance) if request.wallet_balance else None,
        }
        validation_result = await call_fraud_service(validation_payload)

        if not validation_result.get("valid", False):
            errors = validation_result.get("errors", [])
            error_msg = "; ".join(e.get("message", "") for e in errors[:3])
            transaction.status = "FAILED"
            transaction.failure_reason = f"Validation failed: {error_msg}"
            transaction.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return PaymentResponse(
                transaction_id=transaction_id,
                status="FAILED",
                message=f"Payment validation failed: {error_msg}",
                created_at=now,
            )
    except Exception as e:
        logger.error("fraud_service_error", error=str(e))
        # Fail closed — if fraud service is unavailable, reject payment
        transaction.status = "FAILED"
        transaction.failure_reason = "Validation service unavailable"
        transaction.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return PaymentResponse(
            transaction_id=transaction_id,
            status="FAILED",
            message="Payment validation service unavailable",
            created_at=now,
        )

    # Step 2: Get route via Routing Service
    try:
        routing_result = await call_routing_service(
            payment_type=request.payment_type.value,
            amount=str(request.amount),
            merchant_id=request.merchant_id,
        )
        route_target = routing_result.get("route_target", "default_gateway")
        transaction.route_target = route_target
    except Exception as e:
        logger.warning("routing_service_error", error=str(e))
        # Routing failure is non-fatal — use default
        route_target = "default_gateway"
        transaction.route_target = route_target

    # Step 3: Simulate payment outcome
    success = random.random() < settings.success_rate  # noqa: S311

    if success:
        transaction.status = "SUCCESS"
        transaction.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return PaymentResponse(
            transaction_id=transaction_id,
            status="SUCCESS",
            message="Payment processed successfully",
            route_target=route_target,
            created_at=now,
        )
    else:
        transaction.status = "FAILED"
        transaction.failure_reason = "Payment declined by provider"
        transaction.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return PaymentResponse(
            transaction_id=transaction_id,
            status="FAILED",
            message="Payment declined by provider",
            route_target=route_target,
            created_at=now,
        )


async def get_transaction(transaction_id: str, db: AsyncSession) -> TransactionDetail | None:
    """Get transaction by ID."""
    stmt = select(TransactionDB).where(TransactionDB.id == transaction_id)
    result = await db.execute(stmt)
    txn = result.scalar_one_or_none()
    if not txn:
        return None
    return TransactionDetail.model_validate(txn)


async def list_transactions(
    filters: TransactionFilters, db: AsyncSession
) -> PaginatedTransactions:
    """List transactions with filtering and pagination."""
    stmt = select(TransactionDB)

    if filters.merchant_id:
        stmt = stmt.where(TransactionDB.merchant_id == filters.merchant_id)
    if filters.status:
        stmt = stmt.where(TransactionDB.status == filters.status)
    if filters.payment_type:
        stmt = stmt.where(TransactionDB.payment_type == filters.payment_type)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Paginate
    offset = (filters.page - 1) * filters.limit
    stmt = stmt.order_by(TransactionDB.created_at.desc()).offset(offset).limit(filters.limit)

    result = await db.execute(stmt)
    transactions = result.scalars().all()

    return PaginatedTransactions(
        items=[TransactionDetail.model_validate(t) for t in transactions],
        total=total,
        page=filters.page,
        limit=filters.limit,
    )
