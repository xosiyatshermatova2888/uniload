import uuid

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UniversityBrief(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    short_name: str | None


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    locale: str
    is_platform_admin: bool
    must_change_password: bool
    university: UniversityBrief | None
    roles: list[str]
    permissions: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: MeOut


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=256)


class PasswordForgotIn(BaseModel):
    email: EmailStr


class PasswordResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=256)
