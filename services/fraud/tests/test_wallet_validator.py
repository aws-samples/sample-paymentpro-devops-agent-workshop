"""Tests for wallet validation logic."""

from decimal import Decimal

from app.services.wallet_validator import validate_wallet


class TestValidateWallet:
    """Tests for validate_wallet function."""

    def test_valid_wallet(self) -> None:
        errors = validate_wallet("ABCD1234EFGH", Decimal("500.00"), Decimal("100.00"))
        assert errors == []

    def test_valid_wallet_exact_balance(self) -> None:
        errors = validate_wallet("wallet12345678", Decimal("100.00"), Decimal("100.00"))
        assert errors == []

    def test_valid_wallet_min_length(self) -> None:
        errors = validate_wallet("abcd1234", Decimal("500.00"), Decimal("100.00"))
        assert errors == []

    def test_valid_wallet_max_length(self) -> None:
        wallet_id = "a" * 32
        errors = validate_wallet(wallet_id, Decimal("500.00"), Decimal("100.00"))
        assert errors == []

    def test_empty_wallet_id(self) -> None:
        errors = validate_wallet("", Decimal("500.00"), Decimal("100.00"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_WALLET_ID"

    def test_wallet_id_too_short(self) -> None:
        errors = validate_wallet("abc1234", Decimal("500.00"), Decimal("100.00"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_WALLET_ID"

    def test_wallet_id_too_long(self) -> None:
        wallet_id = "a" * 33
        errors = validate_wallet(wallet_id, Decimal("500.00"), Decimal("100.00"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_WALLET_ID"

    def test_wallet_id_special_chars(self) -> None:
        errors = validate_wallet("wallet-123!", Decimal("500.00"), Decimal("100.00"))
        assert len(errors) == 1
        assert errors[0].code == "INVALID_WALLET_ID"

    def test_insufficient_balance(self) -> None:
        errors = validate_wallet("wallet12345678", Decimal("50.00"), Decimal("100.00"))
        assert len(errors) == 1
        assert errors[0].code == "INSUFFICIENT_BALANCE"

    def test_invalid_id_and_insufficient_balance(self) -> None:
        errors = validate_wallet("bad", Decimal("50.00"), Decimal("100.00"))
        assert len(errors) == 2
        codes = {e.code for e in errors}
        assert "INVALID_WALLET_ID" in codes
        assert "INSUFFICIENT_BALANCE" in codes
