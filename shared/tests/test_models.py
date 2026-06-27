"""Tests for Pydantic models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from shared.enums.types import (
    ApiKeyStatus,
    MerchantStatus,
    PaymentType,
    TransactionStatus,
)
from shared.models.merchant import ApiKey, Merchant, MerchantRegistration, Session
from shared.models.routing import RoutingDecision, RoutingRequest, RoutingRule
from shared.models.transaction import PaymentRequest, PaymentResponse, Transaction
from shared.models.validation import ValidationError, ValidationResult


class TestPaymentRequest:
    """Tests for PaymentRequest model."""

    def test_valid_upi_request(self):
        req = PaymentRequest(
            payment_type=PaymentType.UPI,
            amount=Decimal("100.00"),
            upi_id="user@upi",
        )
        assert req.payment_type == PaymentType.UPI
        assert req.amount == Decimal("100.00")

    def test_valid_card_request(self):
        req = PaymentRequest(
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("500.00"),
            card_number="4532015112830366",
            card_expiry="12/30",
            card_cvv="123",
        )
        assert req.payment_type == PaymentType.CREDIT_CARD

    def test_invalid_zero_amount(self):
        with pytest.raises(PydanticValidationError):
            PaymentRequest(
                payment_type=PaymentType.UPI,
                amount=Decimal("0"),
            )

    def test_invalid_negative_amount(self):
        with pytest.raises(PydanticValidationError):
            PaymentRequest(
                payment_type=PaymentType.WALLET,
                amount=Decimal("-10"),
            )


class TestTransaction:
    """Tests for Transaction model."""

    def test_auto_generated_fields(self):
        txn = Transaction(
            merchant_id="test-merchant-id",
            payment_type=PaymentType.UPI,
            amount=Decimal("250.00"),
        )
        assert txn.id is not None
        assert txn.status == TransactionStatus.PENDING
        assert txn.currency == "INR"
        assert txn.created_at is not None

    def test_custom_status(self):
        txn = Transaction(
            merchant_id="test-merchant-id",
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("1000.00"),
            status=TransactionStatus.SUCCESS,
        )
        assert txn.status == TransactionStatus.SUCCESS


class TestMerchantRegistration:
    """Tests for MerchantRegistration model."""

    def test_valid_registration(self):
        reg = MerchantRegistration(
            business_name="Test Shop",
            email="test@example.com",
            password="securepass123",
        )
        assert reg.business_name == "Test Shop"

    def test_short_business_name(self):
        with pytest.raises(PydanticValidationError):
            MerchantRegistration(
                business_name="A",
                email="test@example.com",
                password="securepass123",
            )

    def test_short_password(self):
        with pytest.raises(PydanticValidationError):
            MerchantRegistration(
                business_name="Test Shop",
                email="test@example.com",
                password="short",
            )


class TestApiKey:
    """Tests for ApiKey model."""

    def test_auto_generated_fields(self):
        key = ApiKey(merchant_id="test-merchant", label="primary")
        assert key.id is not None
        assert key.key_value is not None
        assert len(key.key_value) == 64
        assert key.status == ApiKeyStatus.ACTIVE


class TestRoutingRule:
    """Tests for RoutingRule model."""

    def test_valid_rule(self):
        rule = RoutingRule(
            merchant_id="test-merchant",
            payment_type=PaymentType.UPI,
            priority=1,
            route_target="upi-provider-1",
        )
        assert rule.is_active is True
        assert rule.priority == 1

    def test_invalid_priority_too_low(self):
        with pytest.raises(PydanticValidationError):
            RoutingRule(
                merchant_id="test-merchant",
                priority=0,
                route_target="provider",
            )

    def test_invalid_priority_too_high(self):
        with pytest.raises(PydanticValidationError):
            RoutingRule(
                merchant_id="test-merchant",
                priority=101,
                route_target="provider",
            )


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_result(self):
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_invalid_result_with_errors(self):
        result = ValidationResult(
            valid=False,
            errors=[
                ValidationError(
                    field="card_number",
                    code="INVALID_LUHN",
                    message="Card number failed Luhn check",
                )
            ],
        )
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "INVALID_LUHN"
