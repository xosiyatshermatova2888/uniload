import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.deps import Ctx, require
from app.core.schemas import ORMModel, Page, PageParams, paginate
from app.modules.audit.models import AuditLog

router = APIRouter(tags=["Audit"])


class AuditLogOut(ORMModel):
    id: int
    occurred_at: datetime
    actor_user_id: uuid.UUID | None
    actor_ip: str | None
    request_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    academic_year_id: uuid.UUID | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None


@router.get("/audit-logs", response_model=Page[AuditLogOut], summary="Audit jurnali")
def list_audit_logs(
    params: PageParams = Depends(),
    entity_type: str | None = Query(None, max_length=64),
    entity_id: str | None = Query(None, max_length=64),
    user_id: uuid.UUID | None = None,
    action: str | None = Query(None, max_length=64),
    date_from: datetime | None = Query(None, alias="from"),
    date_to: datetime | None = Query(None, alias="to"),
    ctx: Ctx = Depends(require("audit.view", university_wide=True)),
):
    stmt = select(AuditLog).where(AuditLog.university_id == ctx.university_id).order_by(AuditLog.id.desc())
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id:
        stmt = stmt.where(AuditLog.actor_user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if date_from:
        stmt = stmt.where(AuditLog.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.occurred_at <= date_to)
    return paginate(ctx.db, stmt, params, AuditLogOut)
