"""DB sessiyalari va tenant konteksti.

Har bir tranzaksiya boshida (`after_begin`) PostgreSQL sessiya o‘zgaruvchilari o‘rnatiladi:
`app.university_id`, `app.platform`, `app.override_reason`. RLS siyosatlari va triggerlar
shularga tayanadi. `set_config(..., true)` faqat joriy tranzaksiyaga amal qiladi, shuning uchun
commit’dan keyingi yangi tranzaksiyada ham qayta o‘rnatiladi.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@dataclass(frozen=True)
class TenantScope:
    university_id: uuid.UUID | None
    platform: bool = False
    override_reason: str | None = None


_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, autoflush=False)


@event.listens_for(Session, "after_begin")
def _apply_tenant_scope(session: Session, transaction, connection) -> None:
    scope: TenantScope | None = session.info.get("scope")
    if scope is None:
        return
    connection.execute(
        text("SELECT set_config('app.university_id', :u, true),"
             " set_config('app.platform', :p, true),"
             " set_config('app.override_reason', :o, true)"),
        {"u": str(scope.university_id) if scope.university_id else "",
         "p": "on" if scope.platform else "off",
         "o": scope.override_reason or ""},
    )


@event.listens_for(Session, "before_flush")
def _stamp_actor(session: Session, flush_context, instances) -> None:
    actor = session.info.get("actor_id")
    for obj in session.new:
        if hasattr(obj, "created_by") and getattr(obj, "created_by", None) is None:
            obj.created_by = actor
            obj.updated_by = actor
    for obj in session.dirty:
        if hasattr(obj, "updated_by") and session.is_modified(obj, include_collections=False):
            obj.updated_by = actor


def open_session(scope: TenantScope, actor_id: uuid.UUID | None = None) -> Session:
    session = SessionLocal()
    session.info["scope"] = scope
    session.info["actor_id"] = actor_id
    return session


def platform_session(actor_id: uuid.UUID | None = None) -> Session:
    """RLS’ni platforma rejimida ochadi. Faqat auth va Super Admin kodida ishlatiladi."""
    return open_session(TenantScope(university_id=None, platform=True), actor_id)
