"""Boshqaruv paneli. Yuklama ko‘rsatkichlari 3-bosqichda (hisoblash moduli bilan) to‘ldiriladi;
hozircha ular `null` — UI “hali hisoblanmagan” deb ko‘rsatadi, soxta raqam chiqarmaydi."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.deps import Ctx, require
from app.modules.academic_years import service as years
from app.modules.academic_years.schemas import AcademicYearDetailOut
from app.modules.audit.models import AuditLog
from app.modules.users.models import User

router = APIRouter(tags=["Boshqaruv paneli"])


class DashboardStats(BaseModel):
    active_users: int
    academic_years: int
    total_hours: float | None = None
    assigned_pct: float | None = None
    unassigned_hours: float | None = None
    overloaded_teachers: int | None = None


class ActivityItem(BaseModel):
    occurred_at: datetime
    action: str
    entity_type: str
    actor_name: str | None


class DashboardOut(BaseModel):
    year: AcademicYearDetailOut
    stats: DashboardStats
    warnings: list[str]
    recent_activity: list[ActivityItem]


@router.get("/years/{year_id}/dashboard", response_model=DashboardOut)
def dashboard(year_id: uuid.UUID, ctx: Ctx = Depends(require("dashboard.view"))):
    year = years.get_year(ctx, year_id)
    detail = years.detail(ctx, year)
    stats = DashboardStats(
        active_users=ctx.db.scalar(select(func.count()).select_from(User).where(
            User.university_id == ctx.university_id, User.is_active)) or 0,
        academic_years=len(years.list_years(ctx)),
    )
    warnings = []
    if year.status == "draft":
        warnings.append("Yuklama hali hisoblanmagan. Ma’lumotnomalar va hisoblash moduli "
                        "keyingi bosqichlarda qo‘shiladi.")
    if not detail.semesters:
        warnings.append("O‘quv yili uchun semestrlar kiritilmagan.")

    activity: list[ActivityItem] = []
    if ctx.principal.has("audit.view", university_wide=True):
        rows = ctx.db.execute(
            select(AuditLog.occurred_at, AuditLog.action, AuditLog.entity_type, User.full_name)
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .where(AuditLog.university_id == ctx.university_id)
            .order_by(AuditLog.id.desc()).limit(10)).all()
        activity = [ActivityItem(occurred_at=r[0], action=r[1], entity_type=r[2], actor_name=r[3]) for r in rows]

    return DashboardOut(year=detail, stats=stats, warnings=warnings, recent_activity=activity)
