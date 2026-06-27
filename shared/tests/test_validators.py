"""Tests for validation utility functions."""

from decimal import Decimal

import pytest

from shared.utils.validators import (
    validate_amount,
    validate_card_expiry,
    validate_email,
    validate_luhn,
    validate_upi_id,
)


class TestValidateLuhn:
    """Tests for Luhn algorithm validation."""

    def test_valid_card_number(self):
        # 4532015112830366 is a valid Luhn number
        assert validate_luhn("4532015112830366") is True

    def test_invalid_card_number(self):
        assert validate_luhn("1234567890123456") is False

    def test_empty_string(self):
        assert validate_luhn("") is False

    def test_non_numeric(self):
        assert validate_luhn("abcd567890123456") is False

    def test_wrong_length(self):
        assert validate_luhn("123456789012") is False

    def test_all_zeros(self):
        assert validate_luhn("0000000000000000") is False

    def test_none_input(self):
        assert validate_luhn(None) is False  # type: ignore[arg-type]


class TestValidateEmail:
    """Tests for email validation."""

    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        assert validate_email("first.last@example.co.in") is True

    def test_invalid_no_at(self):
        assert validate_email("userexample.com") is False

    def test_invalid_no_domain(self):
        assert validate_email("user@") is False

    def test_empty_string(self):
        assert validate_email("") is False

    def test_too_long(self):
        assert validate_email("a" * 250 + "@b.com") is False


class TestValidateUpiId:
    """Tests for UPI ID validation."""

    def test_valid_upi_id(self):
        assert validate_upi_id("user@upi") is True

    def test_valid_upi_with_dots(self):
        assert validate_upi_id("first.last@paytm") is True

    def test_invalid_no_at(self):
        assert validate_upi_id("userupi") is False

    def test_invalid_short_username(self):
        assert validate_upi_id("ab@upi") is False

    def test_invalid_short_provider(self):
        assert validate_upi_id("user@a") is False

    def test_empty_string(self):
        assert validate_upi_id("") is False


class TestValidateCardExpiry:
    """Tests for card expiry validation."""

    def test_valid_future_expiry(self):
        assert validate_card_expiry("12/30") is True

    def test_invalid_format(self):
        assert validate_card_expiry("1/30") is False

    def test_invalid_month(self):
        assert validate_card_expiry("13/30") is False

    def test_expired_card(self):
        assert validate_card_expiry("01/20") is False

    def test_empty_string(self):
        assert validate_card_expiry("") is False

    def test_invalid_characters(self):
        assert validate_card_expiry("ab/cd") is False


class TestValidateAmount:
    """Tests for amount validation."""

    def test_valid_amount(self):
        assert validate_amount(Decimal("100.00")) is True

    def test_valid_minimum(self):
        assert validate_amount(Decimal("0.01")) is True

    def test_zero_amount(self):
        assert validate_amount(Decimal("0")) is False

    def test_negative_amount(self):
        assert validate_amount(Decimal("-10.00")) is False

    def test_exceeds_maximum(self):
        assert validate_amount(Decimal("10000001.00")) is False

    def test_too_many_decimals(self):
        assert validate_amount(Decimal("10.001")) is False

    def test_valid_string_input(self):
        assert validate_amount("99.99") is True

    def test_invalid_string(self):
        assert validate_amount("not_a_number") is False
