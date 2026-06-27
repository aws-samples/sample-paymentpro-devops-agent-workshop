"""Payment API endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import (
    PaginatedTransactions,
    PaymentRequest,
    PaymentResponse,
    TransactionDetail,
    TransactionFilters,
)
from app.services.payment_processor import get_transaction, list_transactions, process_payment

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment_endpoint(
    request: PaymentRequest, db: AsyncSession = Depends(get_db)
) -> PaymentResponse:
    """Process a new payment."""
    logger.info(
        "payment_request",
        payment_type=request.payment_type.value,
        merchant_id=request.merchant_id,
        amount=str(request.amount),
    )
    result = await process_payment(request, db)
    logger.info(
        "payment_result",
        transaction_id=result.transaction_id,
        status=result.status,
    )
    return result


@router.get("/{transaction_id}", response_model=TransactionDetail)
async def get_transaction_endpoint(
    transaction_id: str, db: AsyncSession = Depends(get_db)
) -> TransactionDetail:
    """Get transaction status and details."""
    result = await get_transaction(transaction_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result


@router.get("", response_model=PaginatedTransactions)
async def list_transactions_endpoint(
    merchant_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    payment_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTransactions:
    """List transactions with filtering and pagination."""
    filters = TransactionFilters(
        merchant_id=merchant_id,
        status=status,
        payment_type=payment_type,
        page=page,
        limit=limit,
    )
    return await list_transactions(filters, db)
