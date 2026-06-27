"""Tests for card validation logic."""

from app.services.card_validator import CardNetwork, detect_card_network, validate_card


class TestDetectCardNetwork:
    """Tests for card network detection."""

    def test_amex_34(self) -> None:
        assert detect_card_network("340000000000000") == CardNetwork.AMEX

    def test_amex_37(self) -> None:
        assert detect_card_network("370000000000000") == CardNetwork.AMEX

    def test_visa(self) -> None:
        assert detect_card_network("4111111111111111") == CardNetwork.VISA

    def test_mastercard_51(self) -> None:
        assert detect_card_network("5100000000000000") == CardNetwork.MASTERCARD

    def test_mastercard_55(self) -> None:
        assert detect_card_network("5500000000000000") == CardNetwork.MASTERCARD

    def test_mastercard_2221(self) -> None:
        assert detect_card_network("2221000000000000") == CardNetwork.MASTERCARD

    def test_generic(self) -> None:
        assert detect_card_network("6011000000000000") == CardNetwork.GENERIC

    def test_empty_string(self) -> None:
        assert detect_card_network("") == CardNetwork.GENERIC


class TestValidateCard:
    """Tests for validate_card function."""

    def test_valid_visa_card(self) -> None:
        # 4111111111111111 is a well-known Luhn-valid test number
        errors = validate_card("4111111111111111", "12/30", "123")
        assert errors == []

    def test_valid_card_with_spaces(self) -> None:
        errors = validate_card("4111 1111 1111 1111", "12/30", "123")
        assert errors == []

    def test_valid_card_with_dashes(self) -> None:
        errors = validate_card("4111-1111-1111-1111", "12/30", "123")
        assert errors == []

    def test_valid_amex_card(self) -> None:
        # 378282246310005 is a Luhn-valid Amex test number
        errors = validate_card("378282246310005", "12/30", "1234")
        assert errors == []

    def test_invalid_card_non_digits(self) -> None:
        errors = validate_card("4111abcd11111111", "12/30", "123")
        assert any(e.code == "INVALID_CARD_FORMAT" for e in errors)

    def test_invalid_card_too_short(self) -> None:
        errors = validate_card("411111111111", "12/30", "123")
        assert any(e.code == "INVALID_CARD_LENGTH" for e in errors)

    def test_invalid_card_too_long(self) -> None:
        errors = validate_card("41111111111111111111", "12/30", "123")
        assert any(e.code == "INVALID_CARD_LENGTH" for e in errors)

    def test_luhn_check_fails(self) -> None:
        errors = validate_card("4111111111111112", "12/30", "123")
        assert any(e.code == "LUHN_CHECK_FAILED" for e in errors)

    def test_invalid_cvv_non_digits(self) -> None:
        errors = validate_card("4111111111111111", "12/30", "abc")
        assert any(e.code == "INVALID_CVV" for e in errors)

    def test_invalid_cvv_wrong_length_visa(self) -> None:
        errors = validate_card("4111111111111111", "12/30", "1234")
        assert any(e.code == "INVALID_CVV" for e in errors)

    def test_invalid_cvv_wrong_length_amex(self) -> None:
        errors = validate_card("378282246310005", "12/30", "123")
        assert any(e.code == "INVALID_CVV" for e in errors)

    def test_invalid_expiry_format(self) -> None:
        errors = validate_card("4111111111111111", "13/30", "123")
        assert any(e.code == "INVALID_EXPIRY_FORMAT" for e in errors)

    def test_invalid_expiry_bad_format(self) -> None:
        errors = validate_card("4111111111111111", "2030-12", "123")
        assert any(e.code == "INVALID_EXPIRY_FORMAT" for e in errors)

    def test_expired_card(self) -> None:
        errors = validate_card("4111111111111111", "01/20", "123")
        assert any(e.code == "EXPIRED_CARD" for e in errors)

    def test_multiple_errors_returned(self) -> None:
        # Invalid number AND expired card AND bad CVV
        errors = validate_card("1234", "01/20", "ab")
        assert len(errors) >= 2
