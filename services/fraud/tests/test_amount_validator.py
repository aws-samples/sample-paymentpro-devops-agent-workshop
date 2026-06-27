"""Tests for amount validation logic."""

from decimal import Decimal

from app.services.amount_validator import validate_amount


class TestValidateAmount:
    """Tests for validate_amount function."""

    def test_valid_amount(self) -> None:
        errors = validate_amount(Decimal("100.00"))
        assert errors == []

    def test_valid_minimum_amount(self) -> None:
        errors = validate_amount(Decimal("0.01"))
        assert errors == []

    def test_valid_maximum_amount(self) -> None:
        errors = validate_amount(Decimal("10000000.00"))
        assert errors == []

    def test_valid_one_decimal_place(self) -> None:
        errors = validate_amount(Decimal("99.9"))
        assert errors == []

    def test_valid_no_decimal_places(self) -> None:
        errors = validate_amount(Decimal("500"))
        assert errors == []

    def test_invalid_zero_amount(self) -> None:
        errors = validate_amount(Decimal("0"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_AMOUNT"

    def test_invalid_negative_amount(self) -> None:
        errors = validate_amount(Decimal("-10"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_AMOUNT"

    def test_amount_below_minimum(self) -> None:
        errors = validate_amount(Decimal("0.001"))
        assert len(errors) >= 1
        assert any(e.code in ("AMOUNT_TOO_LOW", "INVALID_AMOUNT") for e in errors)

    def test_amount_above_maximum(self) -> None:
        errors = validate_amount(Decimal("10000001.00"))
        assert len(errors) == 1
        assert errors[0].code == "AMOUNT_TOO_HIGH"

    def test_too_many_decimal_places(self) -> None:
        errors = validate_amount(Decimal("99.999"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_AMOUNT"
        assert "decimal" in errors[0].message.lower()

    def test_error_field_is_amount(self) -> None:
        errors = validate_amount(Decimal("0"))
        assert errors[0].field == "amount"
