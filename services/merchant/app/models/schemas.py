"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class MerchantRegisterRequest(BaseModel):
    """Registration request."""

    business_name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8)
    contact: Optional[str] = None


class MerchantProfile(BaseModel):
    """Merchant profile response."""

    id: str
    business_name: str
    email: str
    contact: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """Login request."""

    email: str
    password: str


class SessionResponse(BaseModel):
    """Login session response."""

    session_id: str
    merchant_id: str
    expires_at: datetime


class ApiKeyResponse(BaseModel):
    """API key response."""

    id: str
    merchant_id: str
    key_value: str
    label: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyValidationResult(BaseModel):
    """Result of API key validation."""

    valid: bool
    merchant_id: Optional[str] = None
