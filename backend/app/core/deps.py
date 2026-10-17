"""So‘rov konteksti: autentifikatsiya, tenant sessiyasi va ruxsat tekshiruvi.

Har bir so‘rovda bitta DB sessiya ochiladi. `university_id` faqat tokendan olinadi —
so‘rov tanasi yoki parametrlaridan hech qachon.
"""

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, Unauthorized
from app.core.principal import Grant, Principal
from app.core.security import decode_access_token
from app.db.session import TenantScope, open_session
from app.modules.users.models import Permission, Role, RolePermission, User, UserRole

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Ctx:
    db: Session
    principal: Principal
    request_id: str | None
    ip: str | None

    @property
    def university_id(self) -> uuid.UUID:
        if self.principal.university_id is None:
            raise Forbidden("Bu amal universitet foydalanuvchisi uchun", code="TENANT_REQUIRED")
        return self.principal.university_id


def load_grants(db: Session, user_id: uuid.UUID) -> list[Grant]:
    rows = db.execute(
        select(Permission.code, UserRole.scope_type, UserRole.scope_id)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(UserRole.user_id == user_id)
    ).all()
    grants = [Grant(code, scope_type, scope_id) for code, scope_type, scope_id in rows]
    faculty_ids = {g.scope_id for g in grants if g.scope_type == "faculty" and g.scope_id}
    if faculty_ids:
        # Fakultet ko‘lami = shu fakultetning barcha kafedralari.
        from app.modules.org.models import Department
        by_faculty: dict[uuid.UUID, list[uuid.UUID]] = {}
        for dep_id, fac_id in db.execute(
                select(Department.id, Department.faculty_id).where(Department.faculty_id.in_(faculty_ids))):
            by_faculty.setdefault(fac_id, []).append(dep_id)
        grants += [Grant(g.permission, "department", dep_id) for g in grants if g.scope_type == "faculty"
                   for dep_id in by_faculty.get(g.scope_id, [])]
    return grants


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_ctx(request: Request,
            creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Iterator[Ctx]:
    if creds is None or creds.scheme.lower() != "bearer":
        raise Unauthorized()
    payload = decode_access_token(creds.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
        university_id = uuid.UUID(payload["uni"]) if payload.get("uni") else None
    except (ValueError, TypeError) as e:
        raise Unauthorized("Token yaroqsiz", code="TOKEN_INVALID") from e
    is_platform = bool(payload.get("pa")) and university_id is None

    db = open_session(TenantScope(university_id=university_id, platform=is_platform), actor_id=user_id)
    try:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise Unauthorized("Foydalanuvchi faol emas", code="USER_INACTIVE")
        if user.university_id != university_id:
            raise Unauthorized("Token yaroqsiz", code="TOKEN_INVALID")
        principal = Principal(
            user_id=user.id, university_id=user.university_id, is_platform_admin=user.is_platform_admin,
            username=user.username, full_name=user.full_name, teacher_id=user.teacher_id,
            grants=load_grants(db, user.id),
        )
        yield Ctx(db=db, principal=principal,
                  request_id=getattr(request.state, "request_id", None), ip=_client_ip(request))
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def get_tenant_ctx(ctx: Ctx = Depends(get_ctx)) -> Ctx:
    """Universitet ma’lumotlari bilan ishlovchi endpointlar uchun."""
    _ = ctx.university_id
    return ctx


def get_platform_ctx(ctx: Ctx = Depends(get_ctx)) -> Ctx:
    if not ctx.principal.is_platform_admin:
        raise Forbidden("Faqat platforma administratori uchun")
    return ctx


def require(code: str, *, university_wide: bool = False) -> Callable[..., Ctx]:
    def dependency(ctx: Ctx = Depends(get_tenant_ctx)) -> Ctx:
        if not ctx.principal.has(code, university_wide=university_wide):
            raise Forbidden(f"Kerakli ruxsat: {code}")
        return ctx
    return dependency


def require_platform(code: str) -> Callable[..., Ctx]:
    def dependency(ctx: Ctx = Depends(get_platform_ctx)) -> Ctx:
        if not ctx.principal.has(code):
            raise Forbidden(f"Kerakli ruxsat: {code}")
        return ctx
    return dependency
