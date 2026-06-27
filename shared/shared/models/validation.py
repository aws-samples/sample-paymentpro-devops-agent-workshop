"""Validation result models."""

from pydantic import BaseModel


class ValidationError(BaseModel):
    """A single field validation error."""

    field: str
    code: str
    message: str


class ValidationResult(BaseModel):
    """Result of a validation operation."""

    valid: bool
    errors: list[ValidationError] = []
