"""Tests for response formatting utilities."""

from shared.constants.config import ERROR_TYPE_BASE_URL
from shared.utils.response import error_response, success_response


class TestSuccessResponse:
    """Tests for success response formatting."""

    def test_basic_response(self):
        result = success_response({"id": "123", "name": "test"})
        assert result["data"] == {"id": "123", "name": "test"}
        assert result["status_code"] == 200
        assert "timestamp" in result

    def test_custom_status_code(self):
        result = success_response({"id": "123"}, status_code=201)
        assert result["status_code"] == 201


class TestErrorResponse:
    """Tests for RFC 7807 error response formatting."""

    def test_basic_error(self):
        result = error_response(
            error_type="not-found",
            title="Not Found",
            status=404,
            detail="Transaction not found",
            instance="/api/v1/payments/abc123",
        )
        assert result["type"] == f"{ERROR_TYPE_BASE_URL}/not-found"
        assert result["title"] == "Not Found"
        assert result["status"] == 404
        assert result["detail"] == "Transaction not found"
        assert result["instance"] == "/api/v1/payments/abc123"
        assert "errors" not in result

    def test_validation_error_with_field_errors(self):
        result = error_response(
            error_type="validation-error",
            title="Validation Error",
            status=400,
            detail="One or more fields failed validation",
            instance="/api/v1/payments",
            errors=[
                {"field": "card_number", "code": "INVALID_LUHN", "message": "Failed Luhn check"},
                {"field": "card_expiry", "code": "CARD_EXPIRED", "message": "Card has expired"},
            ],
        )
        assert result["type"] == f"{ERROR_TYPE_BASE_URL}/validation-error"
        assert result["status"] == 400
        assert len(result["errors"]) == 2
        assert result["errors"][0]["field"] == "card_number"

    def test_error_type_url_format(self):
        result = error_response(
            error_type="internal-error",
            title="Internal Server Error",
            status=500,
            detail="Unexpected error",
            instance="/api/v1/payments",
        )
        assert result["type"].startswith("https://")
        assert result["type"].endswith("/internal-error")
