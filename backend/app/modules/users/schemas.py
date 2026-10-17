import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import ORMModel

ScopeType = Literal["university", "faculty", "department", "self"]


class RoleAssignmentIn(BaseModel):
    role_id: uuid.UUID
    scope_type: ScopeType
    scope_id: uuid.UUID | None = None


class RoleAssignmentOut(BaseModel):
    role_id: uuid.UUID
    role_code: str
    role_name: str
    scope_type: str
    scope_id: uuid.UUID | None


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    locale: str
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    row_version: int


class UserDetailOut(UserOut):
    roles: list[RoleAssignmentOut]


class UserCreateIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    initial_password: str = Field(min_length=8, max_length=256,
                                  description="Birinchi kirishda almashtirish talab qilinadi")
    roles: list[RoleAssignmentIn] = []


class UserUpdateIn(BaseModel):
    row_version: int
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    locale: Literal["uz", "ru", "en"] | None = None
    is_active: bool | None = None


class RolesReplaceIn(BaseModel):
    roles: list[RoleAssignmentIn]


class PermissionOut(ORMModel):
    code: str
    module: str
    description: str


class RoleOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    default_scope: str
    is_system: bool
    row_version: int


class RoleDetailOut(RoleOut):
    permissions: list[str]
    users_count: int


class RoleCreateIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_]{2,64}$")
    name: str = Field(min_length=2, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    default_scope: ScopeType = "university"
    permissions: list[str] = []


class RoleUpdateIn(BaseModel):
    row_version: int
    name: str | None = Field(default=None, min_length=2, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    permissions: list[str] | None = None
