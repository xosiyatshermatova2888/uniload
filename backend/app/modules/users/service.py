import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import Ctx
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.core.permissions import PERMISSIONS
from app.core.schemas import Page, PageParams, paginate
from app.core.security import hash_password, validate_password_policy
from app.modules.audit import service as audit
from app.modules.auth.service import revoke_all_sessions
from app.modules.org.models import Department, Faculty
from app.modules.users.models import Permission, Role, RolePermission, User, UserRole
from app.modules.users.schemas import (
    RoleAssignmentIn,
    RoleAssignmentOut,
    RoleCreateIn,
    RoleDetailOut,
    RoleOut,
    RoleUpdateIn,
    UserCreateIn,
    UserDetailOut,
    UserOut,
    UserUpdateIn,
)

# Universitet admin bu ruxsatlarni maxsus rolga qo‘sha olmaydi.
PLATFORM_ONLY = {code for code in PERMISSIONS if code.startswith("platform.") and code != "platform.subscriptions.view"}


def _check_version(obj, row_version: int) -> None:
    if obj.row_version != row_version:
        raise Conflict("Yozuv boshqa foydalanuvchi tomonidan o‘zgartirildi. Sahifani yangilang.",
                       code="CONCURRENT_UPDATE")


# ---------------------------------------------------------------- users

def list_users(ctx: Ctx, params: PageParams, q: str | None, is_active: bool | None) -> Page[UserOut]:
    stmt = select(User).where(User.university_id == ctx.university_id).order_by(User.full_name)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.full_name).like(like), User.username.like(like),
                              User.email.like(like)))
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    return paginate(ctx.db, stmt, params, UserOut)


def _get_user(ctx: Ctx, user_id: uuid.UUID) -> User:
    user = ctx.db.get(User, user_id)
    if user is None or user.university_id != ctx.university_id:
        raise NotFound("Foydalanuvchi topilmadi")
    return user


def _assignments(db: Session, user_id: uuid.UUID) -> list[RoleAssignmentOut]:
    rows = db.execute(
        select(UserRole, Role).join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id).order_by(Role.name)
    ).all()
    return [RoleAssignmentOut(role_id=r.id, role_code=r.code, role_name=r.name,
                              scope_type=ur.scope_type, scope_id=ur.scope_id) for ur, r in rows]


def get_user(ctx: Ctx, user_id: uuid.UUID) -> UserDetailOut:
    user = _get_user(ctx, user_id)
    return UserDetailOut(**UserOut.model_validate(user).model_dump(), roles=_assignments(ctx.db, user.id))


def _validate_assignments(ctx: Ctx, items: list[RoleAssignmentIn]) -> list[tuple[Role, RoleAssignmentIn]]:
    result = []
    for item in items:
        role = ctx.db.get(Role, item.role_id)
        if role is None or (role.university_id not in (None, ctx.university_id)):
            raise ValidationFailed("Rol topilmadi", code="ROLE_NOT_FOUND")
        if role.code == "super_admin":
            raise Forbidden("Super Admin rolini universitet foydalanuvchisiga berib bo‘lmaydi")
        if item.scope_type in ("university", "self") and item.scope_id is not None:
            raise ValidationFailed("Bu ko‘lam uchun scope_id ko‘rsatilmaydi", code="SCOPE_INVALID")
        if item.scope_type in ("faculty", "department"):
            if item.scope_id is None:
                raise ValidationFailed("Fakultet/kafedra ko‘lami uchun scope_id majburiy", code="SCOPE_INVALID")
            model = Faculty if item.scope_type == "faculty" else Department
            target = ctx.db.get(model, item.scope_id)
            if target is None or target.university_id != ctx.university_id:
                raise ValidationFailed("Ko‘lam uchun tanlangan fakultet/kafedra topilmadi", code="SCOPE_NOT_FOUND")
        result.append((role, item))
    return result


def _replace_roles(ctx: Ctx, user: User, items: list[RoleAssignmentIn]) -> None:
    validated = _validate_assignments(ctx, items)
    if user.id == ctx.principal.user_id and not any(
            "users.manage" in _role_permissions(ctx.db, r.id) and a.scope_type == "university"
            for r, a in validated):
        raise Conflict("O‘zingizdan foydalanuvchilarni boshqarish huquqini olib tashlay olmaysiz",
                       code="SELF_LOCKOUT")
    ctx.db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    seen = set()
    for role, a in validated:
        key = (role.id, a.scope_type, a.scope_id)
        if key in seen:
            continue
        seen.add(key)
        ctx.db.add(UserRole(university_id=ctx.university_id, user_id=user.id, role_id=role.id,
                            scope_type=a.scope_type, scope_id=a.scope_id))


def create_user(ctx: Ctx, body: UserCreateIn) -> UserDetailOut:
    validate_password_policy(body.initial_password)
    email = body.email.strip().lower() if body.email else None
    user = User(university_id=ctx.university_id, username=body.username, email=email,
                full_name=body.full_name.strip(),
                phone=body.phone, password_hash=hash_password(body.initial_password),
                must_change_password=True)
    ctx.db.add(user)
    ctx.db.flush()
    validated = _validate_assignments(ctx, body.roles)
    for role, a in validated:
        ctx.db.add(UserRole(university_id=ctx.university_id, user_id=user.id, role_id=role.id,
                            scope_type=a.scope_type, scope_id=a.scope_id))
    ctx.db.flush()
    audit.record_ctx(ctx, action="user.created", entity_type="user", entity_id=user.id,
                     after={**audit.snapshot(user), "roles": [r.code for r, _ in validated]})
    ctx.db.commit()
    return get_user(ctx, user.id)


def update_user(ctx: Ctx, user_id: uuid.UUID, body: UserUpdateIn) -> UserDetailOut:
    user = _get_user(ctx, user_id)
    _check_version(user, body.row_version)
    before = audit.snapshot(user)
    data = body.model_dump(exclude_unset=True, exclude={"row_version"})
    if data.get("is_active") is False and user.id == ctx.principal.user_id:
        raise Conflict("O‘zingizni bloklay olmaysiz", code="SELF_LOCKOUT")
    if data.get("email"):
        data["email"] = data["email"].strip().lower()
    for key, value in data.items():
        setattr(user, key, value)
    ctx.db.flush()
    if data.get("is_active") is False:
        revoke_all_sessions(ctx.db, user.id)
    b, a = audit.diff(before, audit.snapshot(user))
    if a:
        audit.record_ctx(ctx, action="user.updated", entity_type="user", entity_id=user.id, before=b, after=a)
    ctx.db.commit()
    return get_user(ctx, user.id)


def replace_user_roles(ctx: Ctx, user_id: uuid.UUID, items: list[RoleAssignmentIn]) -> UserDetailOut:
    user = _get_user(ctx, user_id)
    before = [a.model_dump(mode="json") for a in _assignments(ctx.db, user.id)]
    _replace_roles(ctx, user, items)
    ctx.db.flush()
    after = [a.model_dump(mode="json") for a in _assignments(ctx.db, user.id)]
    audit.record_ctx(ctx, action="user.roles_changed", entity_type="user", entity_id=user.id,
                     before={"roles": before}, after={"roles": after})
    ctx.db.commit()
    return get_user(ctx, user.id)


# ---------------------------------------------------------------- roles

def _role_permissions(db: Session, role_id: uuid.UUID) -> list[str]:
    return sorted(db.scalars(
        select(Permission.code).join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)).all())


def list_permissions(db: Session) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.module, Permission.code)))


def list_roles(ctx: Ctx) -> list[RoleOut]:
    roles = ctx.db.scalars(
        select(Role).where(or_(Role.university_id.is_(None), Role.university_id == ctx.university_id),
                           Role.code != "super_admin")
        .order_by(Role.is_system.desc(), Role.name)).all()
    return [RoleOut.model_validate(r) for r in roles]


def _get_role(ctx: Ctx, role_id: uuid.UUID) -> Role:
    role = ctx.db.get(Role, role_id)
    if role is None or role.university_id not in (None, ctx.university_id) or role.code == "super_admin":
        raise NotFound("Rol topilmadi")
    return role


def get_role(ctx: Ctx, role_id: uuid.UUID) -> RoleDetailOut:
    role = _get_role(ctx, role_id)
    users_count = ctx.db.scalar(select(func.count()).select_from(UserRole).where(
        UserRole.role_id == role.id, UserRole.university_id == ctx.university_id)) or 0
    return RoleDetailOut(**RoleOut.model_validate(role).model_dump(),
                         permissions=_role_permissions(ctx.db, role.id), users_count=users_count)


def _set_permissions(ctx: Ctx, role: Role, codes: list[str]) -> None:
    unknown = set(codes) - PERMISSIONS.keys()
    if unknown:
        raise ValidationFailed(f"Noma’lum ruxsatlar: {', '.join(sorted(unknown))}", code="UNKNOWN_PERMISSION")
    forbidden = set(codes) & PLATFORM_ONLY
    if forbidden:
        raise Forbidden(f"Platforma ruxsatlarini berib bo‘lmaydi: {', '.join(sorted(forbidden))}")
    ctx.db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    if codes:
        perm_ids = ctx.db.scalars(select(Permission.id).where(Permission.code.in_(codes))).all()
        ctx.db.add_all([RolePermission(role_id=role.id, permission_id=pid) for pid in perm_ids])


def create_role(ctx: Ctx, body: RoleCreateIn) -> RoleDetailOut:
    role = Role(university_id=ctx.university_id, code=body.code, name=body.name,
                description=body.description, default_scope=body.default_scope, is_system=False)
    ctx.db.add(role)
    ctx.db.flush()
    _set_permissions(ctx, role, body.permissions)
    ctx.db.flush()
    audit.record_ctx(ctx, action="role.created", entity_type="role", entity_id=role.id,
                     after={**audit.snapshot(role), "permissions": sorted(body.permissions)})
    ctx.db.commit()
    return get_role(ctx, role.id)


def update_role(ctx: Ctx, role_id: uuid.UUID, body: RoleUpdateIn) -> RoleDetailOut:
    role = _get_role(ctx, role_id)
    if role.is_system:
        raise Forbidden("Tizim rolini o‘zgartirib bo‘lmaydi. Undan nusxa olib maxsus rol yarating.",
                        code="SYSTEM_ROLE")
    _check_version(role, body.row_version)
    before = {**audit.snapshot(role), "permissions": _role_permissions(ctx.db, role.id)}
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.permissions is not None:
        _set_permissions(ctx, role, body.permissions)
    ctx.db.flush()
    after = {**audit.snapshot(role), "permissions": _role_permissions(ctx.db, role.id)}
    b, a = audit.diff(before, after)
    audit.record_ctx(ctx, action="role.updated", entity_type="role", entity_id=role.id, before=b, after=a)
    ctx.db.commit()
    return get_role(ctx, role.id)


def delete_role(ctx: Ctx, role_id: uuid.UUID) -> None:
    role = _get_role(ctx, role_id)
    if role.is_system:
        raise Forbidden("Tizim rolini o‘chirib bo‘lmaydi", code="SYSTEM_ROLE")
    in_use = ctx.db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id))
    if in_use:
        raise Conflict("Rol foydalanuvchilarga biriktirilgan. Avval ularni boshqa rolga o‘tkazing.",
                       code="ROLE_IN_USE")
    snap = audit.snapshot(role)
    ctx.db.delete(role)
    audit.record_ctx(ctx, action="role.deleted", entity_type="role", entity_id=role_id, before=snap)
    ctx.db.commit()
