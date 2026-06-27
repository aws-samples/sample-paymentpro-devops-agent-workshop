"""Enum definitions for Payment Processing Services."""

from enum import StrEnum


class PaymentType(StrEnum):
    """Supported payment method types."""

    UPI = "UPI"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    WALLET = "WALLET"


class TransactionStatus(StrEnum):
    """Transaction lifecycle states."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class MerchantStatus(StrEnum):
    """Merchant account states."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ApiKeyStatus(StrEnum):
    """API key states."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
