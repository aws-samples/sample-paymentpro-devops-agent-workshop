"""Shared configuration constants for Payment Processing Services."""

from decimal import Decimal

# Currency
CURRENCY: str = "INR"

# Amount limits
MAX_AMOUNT: Decimal = Decimal("10000000.00")
MIN_AMOUNT: Decimal = Decimal("0.01")

# API Key
API_KEY_LENGTH: int = 64  # hex characters

# Session
SESSION_DURATION_HOURS: int = 24

# Merchant
MAX_BUSINESS_NAME_LENGTH: int = 200

# Password
MIN_PASSWORD_LENGTH: int = 8

# Error response base URL
ERROR_TYPE_BASE_URL: str = "https://api.paymentprocessor.com/errors"
