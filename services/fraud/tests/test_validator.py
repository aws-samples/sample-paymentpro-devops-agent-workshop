"""Tests for the payment validation orchestrator."""

from decimal import Decimal

from shared.enums.types import PaymentType

from app.models.requests import PaymentValidationRequest
from app.services.validator import validate_payment


class TestValidatePaymentOrchestrator:
    """Tests for validate_payment orchestrator."""

    def test_valid_credit_card_payment(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("100.00"),
            merchant_id="merchant_1",
            card_number="4111111111111111",
            card_expiry="12/30",
            cvv="123",
        )
        result = validate_payment(request)
        assert result.valid is True
        assert result.errors == []

    def test_valid_upi_payment(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.UPI,
            amount=Decimal("500.00"),
            merchant_id="merchant_1",
            upi_id="user@paytm",
        )
        result = validate_payment(request)
        assert result.valid is True
        assert result.errors == []

    def test_valid_wallet_payment(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.WALLET,
            amount=Decimal("200.00"),
            merchant_id="merchant_1",
            wallet_id="wallet12345678",
            wallet_balance=Decimal("500.00"),
        )
        result = validate_payment(request)
        assert result.valid is True
        assert result.errors == []

    def test_valid_debit_card_payment(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.DEBIT_CARD,
            amount=Decimal("50.00"),
            merchant_id="merchant_1",
            card_number="4111111111111111",
            card_expiry="12/30",
            cvv="123",
        )
        result = validate_payment(request)
        assert result.valid is True
        assert result.errors == []

    def test_missing_card_fields(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("100.00"),
            merchant_id="merchant_1",
            # Missing card_number, card_expiry, cvv
        )
        result = validate_payment(request)
        assert result.valid is False
        codes = {e.code for e in result.errors}
        assert "MISSING_REQUIRED_FIELD" in codes

    def test_missing_upi_field(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.UPI,
            amount=Decimal("100.00"),
            merchant_id="merchant_1",
            # Missing upi_id
        )
        result = validate_payment(request)
        assert result.valid is False
        assert any(e.code == "MISSING_REQUIRED_FIELD" for e in result.errors)

    def test_missing_wallet_fields(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.WALLET,
            amount=Decimal("100.00"),
            merchant_id="merchant_1",
            # Missing wallet_id, wallet_balance
        )
        result = validate_payment(request)
        assert result.valid is False
        assert any(e.code == "MISSING_REQUIRED_FIELD" for e in result.errors)

    def test_invalid_amount_with_valid_card(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("0.001"),  # Below minimum (3 decimal places + too low)
            merchant_id="merchant_1",
            card_number="4111111111111111",
            card_expiry="12/30",
            cvv="123",
        )
        result = validate_payment(request)
        assert result.valid is False
        assert any(e.code in ("AMOUNT_TOO_LOW", "INVALID_AMOUNT") for e in result.errors)

    def test_aggregates_all_errors(self) -> None:
        """Multiple errors from different validators are all returned."""
        request = PaymentValidationRequest(
            payment_type=PaymentType.CREDIT_CARD,
            amount=Decimal("0.50"),  # Amount error
            merchant_id="merchant_1",
            card_number="1234567890123456",  # Luhn error
            card_expiry="01/20",  # Expired
            cvv="12",  # Wrong length
        )
        result = validate_payment(request)
        assert result.valid is False
        assert len(result.errors) >= 3  # Amount + card errors

    def test_result_includes_payment_type(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.UPI,
            amount=Decimal("100.00"),
            merchant_id="merchant_1",
            upi_id="user@paytm",
        )
        result = validate_payment(request)
        assert result.payment_type == PaymentType.UPI

    def test_result_includes_timestamp(self) -> None:
        request = PaymentValidationRequest(
            payment_type=PaymentType.UPI,
            amount=Decimal("100.00"),
            merchant_id="merchant_1",
            upi_id="user@paytm",
        )
        result = validate_payment(request)
        assert result.validated_at is not None
