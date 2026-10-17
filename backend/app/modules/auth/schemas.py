import uuid

from pydantic import BaseModel, Field

from app.core.schemas import LoginName


class LoginIn(BaseModel):
    username: LoginName
    password: str = Field(min_length=1, max_length=256)


class UniversityBrief(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    short_name: str | None


class MeOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None
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
    username: LoginName


class PasswordResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=256)
