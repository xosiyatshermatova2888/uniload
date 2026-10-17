"""Autentifikatsiya: login, refresh rotatsiyasi, logout, parolni tiklash.

Kirish paytida tenant hali noma’lum, shuning uchun bu modul DB’ga platforma rejimida
(`platform_session`) murojaat qiladi — bu ruxsat faqat shu yerda va Super Admin kodida.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.config import get_settings
from app.core.deps import load_grants
from app.core.errors import AppError, Unauthorized
from app.core.security import (
    create_access_token,
    hash_opaque_token,
    hash_password,
    needs_rehash,
    new_opaque_token,
    validate_password_policy,
    verify_password,
)
from app.db.ids import uuid7
from app.modules.audit import service as audit
from app.modules.auth.schemas import MeOut, TokenOut, UniversityBrief
from app.modules.tenants.models import University
from app.modules.users.models import PasswordResetToken, RefreshToken, Role, User, UserRole

log = logging.getLogger("uniload.auth")

INVALID_CREDENTIALS = "Login yoki parol noto‘g‘ri"


@dataclass
class Issued:
    token: TokenOut
    refresh_raw: str
    refresh_expires: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def build_me(db: Session, user: User) -> MeOut:
    university = db.get(University, user.university_id) if user.university_id else None
    role_codes = db.scalars(
        select(Role.code).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user.id)
    ).all()
    perms = sorted({g.permission for g in load_grants(db, user.id)})
    return MeOut(
        id=user.id, username=user.username, email=user.email, full_name=user.full_name, locale=user.locale,
        is_platform_admin=user.is_platform_admin, must_change_password=user.must_change_password,
        university=UniversityBrief(id=university.id, code=university.code, name=university.name,
                                   short_name=university.short_name) if university else None,
        roles=sorted(set(role_codes)), permissions=perms,
    )


def _issue(db: Session, user: User, *, family_id: uuid.UUID | None, ip: str | None,
           user_agent: str | None) -> Issued:
    s = get_settings()
    access, ttl = create_access_token(user_id=user.id, university_id=user.university_id,
                                      is_platform_admin=user.is_platform_admin)
    raw, token_hash = new_opaque_token()
    expires = _now() + timedelta(days=s.refresh_token_ttl_days)
    rt = RefreshToken(id=uuid7(), user_id=user.id, token_hash=token_hash, family_id=family_id or uuid7(),
                      expires_at=expires, ip=ip, user_agent=(user_agent or "")[:512])
    db.add(rt)
    db.flush()
    return Issued(TokenOut(access_token=access, expires_in=ttl, user=build_me(db, user)), raw, expires)


def _set_login_state(db: Session, user: User, **values) -> None:
    """Kirish hisoblagichlari Core UPDATE bilan yoziladi: ular `row_version`ni oshirmasligi kerak,
    aks holda admin foydalanuvchini tahrirlayotganda soxta “boshqa foydalanuvchi o‘zgartirdi” xatosi chiqadi."""
    db.execute(update(User).where(User.id == user.id).values(**values))
    for key, value in values.items():
        set_committed_value(user, key, value)


def _check_tenant_active(db: Session, user: User) -> None:
    if user.university_id is None:
        return
    uni = db.get(University, user.university_id)
    if uni is None or uni.status != "active":
        raise AppError("Universitet akkaunti faol emas. Administrator bilan bog‘laning.",
                       status=403, code="TENANT_SUSPENDED", title="Kirish cheklangan")


def login(db: Session, *, username: str, password: str, ip: str | None, user_agent: str | None) -> Issued:
    s = get_settings()
    username = username.strip().lower()
    user = db.scalar(select(User).where(User.username == username))
    now = _now()

    if user is None:
        verify_password(password, None)  # vaqtni tenglashtirish
        audit.record(db, action="auth.login_failed", entity_type="user", university_id=None,
                     actor_user_id=None, ip=ip, after={"username": username, "reason": "unknown_username"})
        db.commit()
        raise Unauthorized(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

    if user.locked_until and user.locked_until > now:
        raise AppError("Ko‘p marta noto‘g‘ri urinish. Birozdan keyin qayta urinib ko‘ring.",
                       status=429, code="ACCOUNT_LOCKED", title="Akkaunt vaqtincha bloklangan")

    if not verify_password(password, user.password_hash) or not user.is_active:
        failed = user.failed_login_count + 1
        locked = None
        if failed >= s.max_failed_logins:
            failed, locked = 0, now + timedelta(minutes=s.lockout_minutes)
        _set_login_state(db, user, failed_login_count=failed, locked_until=locked)
        audit.record(db, action="auth.login_failed", entity_type="user", entity_id=user.id,
                     university_id=user.university_id, actor_user_id=user.id, ip=ip,
                     after={"reason": "inactive" if not user.is_active else "bad_password"})
        db.commit()
        raise Unauthorized(INVALID_CREDENTIALS, code="INVALID_CREDENTIALS")

    _check_tenant_active(db, user)
    _set_login_state(db, user, failed_login_count=0, locked_until=None, last_login_at=now)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    issued = _issue(db, user, family_id=None, ip=ip, user_agent=user_agent)
    audit.record(db, action="auth.login", entity_type="user", entity_id=user.id,
                 university_id=user.university_id, actor_user_id=user.id, ip=ip)
    db.commit()
    return issued


def refresh(db: Session, *, raw_token: str | None, ip: str | None, user_agent: str | None) -> Issued:
    if not raw_token:
        raise Unauthorized("Sessiya topilmadi", code="NO_SESSION")
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(raw_token)))
    if rt is None:
        raise Unauthorized("Sessiya topilmadi", code="NO_SESSION")
    user = db.get(User, rt.user_id)

    if rt.revoked_at is not None:
        # Qayta ishlatilgan token — o‘g‘irlangan bo‘lishi mumkin: butun zanjirni bekor qilamiz.
        db.execute(update(RefreshToken).where(RefreshToken.family_id == rt.family_id,
                                              RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=_now()))
        audit.record(db, action="auth.refresh_reuse_detected", entity_type="user", entity_id=rt.user_id,
                     university_id=user.university_id if user else None, actor_user_id=rt.user_id, ip=ip)
        db.commit()
        raise Unauthorized("Sessiya bekor qilingan. Qaytadan kiring.", code="SESSION_REVOKED")
    if rt.expires_at <= _now() or user is None or not user.is_active:
        raise Unauthorized("Sessiya muddati tugagan", code="SESSION_EXPIRED")

    _check_tenant_active(db, user)
    issued = _issue(db, user, family_id=rt.family_id, ip=ip, user_agent=user_agent)
    rt.revoked_at = _now()
    rt.replaced_by_id = db.scalar(select(RefreshToken.id).where(
        RefreshToken.token_hash == hash_opaque_token(issued.refresh_raw)))
    db.commit()
    return issued


def logout(db: Session, *, raw_token: str | None, ip: str | None) -> None:
    if not raw_token:
        return
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_opaque_token(raw_token)))
    if rt is None:
        return
    db.execute(update(RefreshToken).where(RefreshToken.family_id == rt.family_id,
                                          RefreshToken.revoked_at.is_(None)).values(revoked_at=_now()))
    user = db.get(User, rt.user_id)
    audit.record(db, action="auth.logout", entity_type="user", entity_id=rt.user_id,
                 university_id=user.university_id if user else None, actor_user_id=rt.user_id, ip=ip)
    db.commit()


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> None:
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id,
                                          RefreshToken.revoked_at.is_(None)).values(revoked_at=_now()))


def change_password(db: Session, *, user: User, current: str, new: str, ip: str | None) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError("Joriy parol noto‘g‘ri", status=422, code="INVALID_PASSWORD",
                       title="Ma’lumotlar noto‘g‘ri")
    validate_password_policy(new)
    user.password_hash = hash_password(new)
    user.must_change_password = False
    audit.record(db, action="auth.password_changed", entity_type="user", entity_id=user.id,
                 university_id=user.university_id, actor_user_id=user.id, ip=ip)
    db.commit()


def forgot_password(db: Session, *, username: str, ip: str | None) -> None:
    """Login mavjudligini oshkor qilmaydi. Token foydalanuvchi emailiga yuboriladi (hozircha mock — logga).
    Email kiritilmagan foydalanuvchi parolini administrator tiklaydi."""
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or not user.is_active or not user.email:
        return
    raw, token_hash = new_opaque_token()
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash,
                              expires_at=_now() + timedelta(minutes=get_settings().password_reset_ttl_minutes)))
    audit.record(db, action="auth.password_reset_requested", entity_type="user", entity_id=user.id,
                 university_id=user.university_id, actor_user_id=None, ip=ip)
    db.commit()
    if get_settings().env != "prod":
        log.warning("[MOCK EMAIL] %s uchun parolni tiklash tokeni: %s", user.email, raw)


def reset_password(db: Session, *, raw_token: str, new_password: str, ip: str | None) -> None:
    prt = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hash_opaque_token(raw_token)))
    if prt is None or prt.used_at is not None or prt.expires_at <= _now():
        raise AppError("Havola yaroqsiz yoki muddati tugagan", status=400, code="RESET_TOKEN_INVALID")
    validate_password_policy(new_password)
    user = db.get(User, prt.user_id)
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.failed_login_count = 0
    user.locked_until = None
    prt.used_at = _now()
    revoke_all_sessions(db, user.id)
    audit.record(db, action="auth.password_reset", entity_type="user", entity_id=user.id,
                 university_id=user.university_id, actor_user_id=user.id, ip=ip)
    db.commit()
