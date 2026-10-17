import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.deps import Ctx
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import hash_password, validate_password_policy
from app.modules.audit import service as audit
from app.modules.curricula.service import ensure_lesson_types
from app.modules.tenants.models import Plan, Subscription, University
from app.modules.tenants.schemas import (
    PlanCreateIn,
    PlatformUniversityOut,
    SubscriptionCreateIn,
    SubscriptionUpdateIn,
    UniversityCreateIn,
    UniversityOut,
    UniversityPlatformUpdateIn,
    UniversityUpdateIn,
)
from app.modules.users.models import Role, User, UserRole

# Universitet sozlamalarining ruxsat etilgan kalitlari (keyingi bosqichlarda kengayadi).
SETTINGS_KEYS = {"overload_tolerance_pct", "underload_min_pct", "rounding", "calendar", "approval"}

TRIAL_DAYS = 30


def _check_version(obj, row_version: int) -> None:
    if obj.row_version != row_version:
        raise Conflict("Yozuv boshqa foydalanuvchi tomonidan o‘zgartirildi. Sahifani yangilang.",
                       code="CONCURRENT_UPDATE")


def _apply_update(uni: University, data: dict) -> None:
    if "settings" in data and data["settings"] is not None:
        unknown = set(data["settings"]) - SETTINGS_KEYS
        if unknown:
            raise ValidationFailed(f"Noma’lum sozlamalar: {', '.join(sorted(unknown))}", code="UNKNOWN_SETTING")
        data["settings"] = {**(uni.settings or {}), **data["settings"]}
    for key, value in data.items():
        setattr(uni, key, value)


# ------------------------------------------------------------ o‘z universiteti

def get_own(ctx: Ctx) -> University:
    uni = ctx.db.get(University, ctx.university_id)
    if uni is None:
        raise NotFound("Universitet topilmadi")
    return uni


def update_own(ctx: Ctx, body: UniversityUpdateIn) -> University:
    uni = get_own(ctx)
    _check_version(uni, body.row_version)
    before = audit.snapshot(uni)
    _apply_update(uni, body.model_dump(exclude_unset=True, exclude={"row_version"}))
    ctx.db.flush()
    b, a = audit.diff(before, audit.snapshot(uni))
    if a:
        audit.record_ctx(ctx, action="university.updated", entity_type="university", entity_id=uni.id,
                         before=b, after=a)
    ctx.db.commit()
    return uni


# ------------------------------------------------------------ platforma

def _platform_out(ctx: Ctx, uni: University) -> PlatformUniversityOut:
    users_count = ctx.db.scalar(select(func.count()).select_from(User).where(User.university_id == uni.id)) or 0
    row = ctx.db.execute(
        select(Subscription.status, Plan.code).join(Plan, Plan.id == Subscription.plan_id)
        .where(Subscription.university_id == uni.id)
        .order_by(Subscription.starts_at.desc()).limit(1)).first()
    return PlatformUniversityOut(**UniversityOut.model_validate(uni).model_dump(), users_count=users_count,
                                 subscription_status=row[0] if row else None, plan_code=row[1] if row else None)


def list_universities(ctx: Ctx) -> list[PlatformUniversityOut]:
    return [_platform_out(ctx, u) for u in ctx.db.scalars(select(University).order_by(University.name))]


def get_university(ctx: Ctx, university_id: uuid.UUID) -> PlatformUniversityOut:
    uni = ctx.db.get(University, university_id)
    if uni is None:
        raise NotFound("Universitet topilmadi")
    return _platform_out(ctx, uni)


def create_university(ctx: Ctx, body: UniversityCreateIn) -> PlatformUniversityOut:
    validate_password_policy(body.first_admin.initial_password)
    plan = ctx.db.scalar(select(Plan).where(Plan.code == body.plan_code, Plan.is_active))
    if plan is None:
        raise ValidationFailed("Tarif topilmadi", code="PLAN_NOT_FOUND")
    admin_role = ctx.db.scalar(select(Role).where(Role.code == "university_admin", Role.university_id.is_(None)))
    if admin_role is None:
        raise Conflict("Tizim rollari topilmadi. `python -m app.cli bootstrap` ni ishga tushiring.",
                       code="NOT_BOOTSTRAPPED")

    uni = University(code=body.code, name=body.name, short_name=body.short_name, stir=body.stir)
    ctx.db.add(uni)
    ctx.db.flush()
    now = datetime.now(UTC)
    trial = plan.code == "trial"
    ctx.db.add(Subscription(university_id=uni.id, plan_id=plan.id, status="trial" if trial else "active",
                            starts_at=now, ends_at=now + timedelta(days=TRIAL_DAYS) if trial else None))
    admin = User(university_id=uni.id, username=body.first_admin.username,
                 email=body.first_admin.email.strip().lower() if body.first_admin.email else None,
                 full_name=body.first_admin.full_name, must_change_password=True,
                 password_hash=hash_password(body.first_admin.initial_password))
    ctx.db.add(admin)
    ctx.db.flush()
    ctx.db.add(UserRole(university_id=uni.id, user_id=admin.id, role_id=admin_role.id, scope_type="university"))
    ensure_lesson_types(ctx.db, uni.id)
    ctx.db.flush()
    audit.record_ctx(ctx, action="university.created", entity_type="university", entity_id=uni.id,
                     university_id=uni.id,
                     after={**audit.snapshot(uni), "plan": plan.code, "first_admin": admin.username})
    ctx.db.commit()
    return _platform_out(ctx, uni)


def update_university(ctx: Ctx, university_id: uuid.UUID, body: UniversityPlatformUpdateIn) -> PlatformUniversityOut:
    uni = ctx.db.get(University, university_id)
    if uni is None:
        raise NotFound("Universitet topilmadi")
    _check_version(uni, body.row_version)
    before = audit.snapshot(uni)
    _apply_update(uni, body.model_dump(exclude_unset=True, exclude={"row_version"}))
    ctx.db.flush()
    b, a = audit.diff(before, audit.snapshot(uni))
    if a:
        audit.record_ctx(ctx, action="university.updated", entity_type="university", entity_id=uni.id,
                         university_id=uni.id, before=b, after=a)
    ctx.db.commit()
    return _platform_out(ctx, uni)


def list_plans(ctx: Ctx) -> list[Plan]:
    return list(ctx.db.scalars(select(Plan).order_by(Plan.price_monthly.nulls_first(), Plan.code)))


def create_plan(ctx: Ctx, body: PlanCreateIn) -> Plan:
    plan = Plan(**body.model_dump())
    ctx.db.add(plan)
    ctx.db.flush()
    audit.record_ctx(ctx, action="plan.created", entity_type="plan", entity_id=plan.id, after=audit.snapshot(plan))
    ctx.db.commit()
    return plan


def list_subscriptions(ctx: Ctx, university_id: uuid.UUID) -> list[Subscription]:
    if ctx.db.get(University, university_id) is None:
        raise NotFound("Universitet topilmadi")
    return list(ctx.db.scalars(select(Subscription).where(Subscription.university_id == university_id)
                               .order_by(Subscription.starts_at.desc())))


def create_subscription(ctx: Ctx, university_id: uuid.UUID, body: SubscriptionCreateIn) -> Subscription:
    if ctx.db.get(University, university_id) is None:
        raise NotFound("Universitet topilmadi")
    if ctx.db.get(Plan, body.plan_id) is None:
        raise ValidationFailed("Tarif topilmadi", code="PLAN_NOT_FOUND")
    sub = Subscription(university_id=university_id, **body.model_dump())
    ctx.db.add(sub)
    ctx.db.flush()
    audit.record_ctx(ctx, action="subscription.created", entity_type="subscription", entity_id=sub.id,
                     university_id=university_id, after=audit.snapshot(sub))
    ctx.db.commit()
    return sub


def update_subscription(ctx: Ctx, subscription_id: uuid.UUID, body: SubscriptionUpdateIn) -> Subscription:
    sub = ctx.db.get(Subscription, subscription_id)
    if sub is None:
        raise NotFound("Obuna topilmadi")
    _check_version(sub, body.row_version)
    before = audit.snapshot(sub)
    for key, value in body.model_dump(exclude_unset=True, exclude={"row_version"}).items():
        setattr(sub, key, value)
    ctx.db.flush()
    b, a = audit.diff(before, audit.snapshot(sub))
    audit.record_ctx(ctx, action="subscription.updated", entity_type="subscription", entity_id=sub.id,
                     university_id=sub.university_id, before=b, after=a)
    ctx.db.commit()
    return sub
