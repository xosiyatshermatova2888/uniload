import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog

_SECRET_FIELDS = {"password_hash", "token_hash"}


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    return value


def snapshot(obj: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    """ORM obyektining ustunlarini audit uchun JSON ko‘rinishiga o‘tkazadi."""
    skip = _SECRET_FIELDS | (exclude or set())
    return {attr.key: _json_safe(getattr(obj, attr.key))
            for attr in inspect(obj).mapper.column_attrs if attr.key not in skip}


def diff(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    ignore = {"updated_at", "row_version", "updated_by"}
    keys = [k for k in after if k not in ignore and before.get(k) != after.get(k)]
    return {k: before.get(k) for k in keys}, {k: after.get(k) for k in keys}


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    university_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    ip: str | None = None,
    request_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    academic_year_id: uuid.UUID | None = None,
) -> None:
    db.add(AuditLog(
        university_id=university_id, actor_user_id=actor_user_id, actor_ip=ip, request_id=request_id,
        action=action, entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        academic_year_id=academic_year_id, before=_json_safe(before), after=_json_safe(after),
        reason=reason,
    ))


def record_ctx(ctx, *, action: str, entity_type: str, entity_id: Any = None, **kwargs: Any) -> None:
    """`Ctx` dan foydalanuvchi, IP va request_id ni oladi."""
    kwargs.setdefault("university_id", ctx.principal.university_id)
    record(ctx.db, action=action, entity_type=entity_type, entity_id=entity_id,
           actor_user_id=ctx.principal.user_id, ip=ctx.ip, request_id=ctx.request_id, **kwargs)
