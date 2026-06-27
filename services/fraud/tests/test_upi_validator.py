"""Tests for UPI validation logic."""

from app.services.upi_validator import KNOWN_UPI_PROVIDERS, validate_upi


class TestValidateUpi:
    """Tests for validate_upi function."""

    def test_valid_upi_paytm(self) -> None:
        errors = validate_upi("user123@paytm")
        assert errors == []

    def test_valid_upi_ybl(self) -> None:
        errors = validate_upi("john.doe@ybl")
        assert errors == []

    def test_valid_upi_oksbi(self) -> None:
        errors = validate_upi("merchant_1@oksbi")
        assert errors == []

    def test_valid_upi_with_dots(self) -> None:
        errors = validate_upi("first.last@upi")
        assert errors == []

    def test_valid_upi_with_underscores(self) -> None:
        errors = validate_upi("user_name@hdfc")
        assert errors == []

    def test_empty_upi_id(self) -> None:
        errors = validate_upi("")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_UPI_FORMAT"

    def test_missing_at_symbol(self) -> None:
        errors = validate_upi("userpaytm")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_UPI_FORMAT"

    def test_multiple_at_symbols(self) -> None:
        errors = validate_upi("user@name@paytm")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_UPI_FORMAT"

    def test_empty_username(self) -> None:
        errors = validate_upi("@paytm")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_UPI_FORMAT"

    def test_special_chars_in_username(self) -> None:
        errors = validate_upi("user!name@paytm")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_UPI_FORMAT"

    def test_unknown_provider(self) -> None:
        errors = validate_upi("user@unknownbank")
        assert len(errors) == 1
        assert errors[0].code == "UNKNOWN_UPI_PROVIDER"

    def test_provider_case_insensitive(self) -> None:
        # Provider matching is case-insensitive
        errors = validate_upi("user@PAYTM")
        # The regex requires lowercase in provider, so this should fail format
        # Actually our regex is [a-zA-Z0-9]+ so it matches, then we lowercase for lookup
        assert errors == []

    def test_all_known_providers_valid(self) -> None:
        for provider in KNOWN_UPI_PROVIDERS:
            errors = validate_upi(f"testuser@{provider}")
            assert errors == [], f"Provider '{provider}' should be valid"

    def test_username_too_long(self) -> None:
        long_username = "a" * 51
        errors = validate_upi(f"{long_username}@paytm")
        assert len(errors) == 1
        assert errors[0].code == "INVALID_UPI_FORMAT"
