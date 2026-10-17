import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.permissions import SCOPE_TYPES
from app.db.base import AuditMixin, Base, IdMixin
from app.db.ids import uuid7


class User(IdMixin, AuditMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("is_platform_admin OR university_id IS NOT NULL", name="tenant_required"),
        CheckConstraint("email = lower(email)", name="email_lower"),
        Index("ix_users_university_active", "university_id", "is_active"),
    )

    university_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    locale: Mapped[str] = mapped_column(String(2), default="uz", server_default="uz")
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_platform_admin: Mapped[bool] = mapped_column(default=False, server_default="false")
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default="false")
    failed_login_count: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    # Foydalanuvchi ↔ professor-o‘qituvchi profili (PO o‘z yuklamasini ko‘rishi uchun).
    teacher_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), unique=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_revoked", "user_id", "revoked_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    replaced_by_id: Mapped[uuid.UUID | None]
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    module: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(255))


class Role(IdMixin, AuditMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        Index("uq_roles_university_code", "university_id", "code", unique=True,
              postgresql_nulls_not_distinct=True),
        CheckConstraint("code ~ '^[a-z0-9_]{2,64}$'", name="code_format"),
        CheckConstraint(f"default_scope IN {SCOPE_TYPES}", name="default_scope"),
    )

    # NULL — tizim roli (barcha universitetlar uchun shablon).
    university_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(500))
    default_scope: Mapped[str] = mapped_column(String(16), default="university", server_default="university")
    is_system: Mapped[bool] = mapped_column(default=False, server_default="false")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class UserRole(IdMixin, AuditMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        CheckConstraint(f"scope_type IN {SCOPE_TYPES}", name="scope_type"),
        CheckConstraint(
            "(scope_type IN ('platform', 'university', 'self')) = (scope_id IS NULL)", name="scope_id"),
        CheckConstraint("scope_type = 'platform' OR university_id IS NOT NULL", name="tenant_required"),
        Index("uq_user_roles_assignment", "user_id", "role_id", "scope_type", "scope_id", unique=True,
              postgresql_nulls_not_distinct=True),
    )

    university_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("universities.id", ondelete="RESTRICT"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True)
    scope_type: Mapped[str] = mapped_column(String(16))
    # faculty/department ID — 2-bosqichda tegishli jadvallarga tekshiruv qo‘shiladi.
    scope_id: Mapped[uuid.UUID | None]
