import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TenantMixin

UNIVERSITY_STATUSES = ("active", "suspended", "closed")
LOCALES = ("uz", "ru", "en")
SUBSCRIPTION_STATUSES = ("trial", "active", "past_due", "canceled")


class University(IdMixin, AuditMixin, Base):
    __tablename__ = "universities"
    __table_args__ = (
        CheckConstraint(f"status IN {UNIVERSITY_STATUSES}", name="status"),
        CheckConstraint(f"default_locale IN {LOCALES}", name="locale"),
        CheckConstraint("code = lower(code) AND code ~ '^[a-z0-9-]{2,64}$'", name="code_format"),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str | None] = mapped_column(String(64))
    stir: Mapped[str | None] = mapped_column(String(9))
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active", index=True)
    default_locale: Mapped[str] = mapped_column(String(2), default="uz", server_default="uz")
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default=text("'{}'::jsonb"))


class Plan(IdMixin, AuditMixin, Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    limits: Mapped[dict[str, Any]] = mapped_column(default=dict, server_default=text("'{}'::jsonb"))
    price_monthly: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class Subscription(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(f"status IN {SUBSCRIPTION_STATUSES}", name="status"),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="period"),
        Index("uq_subscriptions_one_active", "university_id", unique=True,
              postgresql_where=text("status IN ('trial', 'active')")),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16))
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime | None]
