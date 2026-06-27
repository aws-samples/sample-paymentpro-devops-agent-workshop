"""Merchant-related models."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from shared.constants.config import SESSION_DURATION_HOURS
from shared.enums.types import ApiKeyStatus, MerchantStatus
from shared.utils.datetime_utils import utc_now
from shared.utils.id_generator import generate_api_key_value, generate_id


class MerchantRegistration(BaseModel):
    """Merchant registration request DTO."""

    business_name: str = Field(min_length=2, max_length=200)
    email: str
    password: str = Field(min_length=8)
    contact: Optional[str] = None


class Merchant(BaseModel):
    """Merchant record."""

    id: str = Field(default_factory=generate_id)
    business_name: str
    email: str
    password_hash: str
    contact: Optional[str] = None
    status: MerchantStatus = MerchantStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ApiKey(BaseModel):
    """API key record."""

    id: str = Field(default_factory=generate_id)
    merchant_id: str
    key_value: str = Field(default_factory=generate_api_key_value)
    label: str
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: Optional[datetime] = None


class Session(BaseModel):
    """Merchant session record."""

    id: str = Field(default_factory=generate_id)
    merchant_id: str
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS)
    )
