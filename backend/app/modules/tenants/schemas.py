import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import ORMModel


class UniversityOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    short_name: str | None
    stir: str | None
    status: str
    default_locale: str
    settings: dict[str, Any]
    created_at: datetime
    row_version: int


class UniversityUpdateIn(BaseModel):
    """Universitet admin o‘zgartira oladigan maydonlar."""

    row_version: int
    name: str | None = Field(default=None, min_length=3, max_length=255)
    short_name: str | None = Field(default=None, max_length=64)
    stir: str | None = Field(default=None, pattern=r"^\d{9}$")
    default_locale: Literal["uz", "ru", "en"] | None = None
    settings: dict[str, Any] | None = None


class FirstAdminIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    initial_password: str = Field(min_length=8, max_length=256)


class UniversityCreateIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9-]{2,64}$")
    name: str = Field(min_length=3, max_length=255)
    short_name: str | None = Field(default=None, max_length=64)
    stir: str | None = Field(default=None, pattern=r"^\d{9}$")
    plan_code: str = "trial"
    first_admin: FirstAdminIn


class UniversityPlatformUpdateIn(UniversityUpdateIn):
    status: Literal["active", "suspended", "closed"] | None = None


class PlatformUniversityOut(UniversityOut):
    users_count: int
    subscription_status: str | None
    plan_code: str | None


class PlanOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    limits: dict[str, Any]
    price_monthly: Decimal | None
    is_active: bool


class PlanCreateIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_-]{2,32}$")
    name: str = Field(min_length=2, max_length=128)
    limits: dict[str, Any] = {}
    price_monthly: Decimal | None = Field(default=None, ge=0)


class SubscriptionOut(ORMModel):
    id: uuid.UUID
    university_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    starts_at: datetime
    ends_at: datetime | None
    row_version: int


class SubscriptionCreateIn(BaseModel):
    plan_id: uuid.UUID
    status: Literal["trial", "active", "past_due", "canceled"] = "active"
    starts_at: datetime
    ends_at: datetime | None = None


class SubscriptionUpdateIn(BaseModel):
    row_version: int
    status: Literal["trial", "active", "past_due", "canceled"] | None = None
    ends_at: datetime | None = None
