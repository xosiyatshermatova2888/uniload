import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import Unauthorized, ValidationFailed

_hasher = PasswordHasher()
# Mavjud bo‘lmagan email bilan kirishda ham vaqt bir xil bo‘lishi uchun.
_DUMMY_HASH = _hasher.hash("timing-equalizer")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def validate_password_policy(password: str) -> None:
    problems = []
    if len(password) < 8:
        problems.append("kamida 8 belgi")
    if not re.search(r"[A-Za-z]", password):
        problems.append("kamida bitta harf")
    if not re.search(r"\d", password):
        problems.append("kamida bitta raqam")
    if problems:
        raise ValidationFailed("Parol talablarga javob bermaydi: " + ", ".join(problems),
                               code="WEAK_PASSWORD")


def create_access_token(*, user_id: uuid.UUID, university_id: uuid.UUID | None,
                        is_platform_admin: bool) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(UTC)
    ttl = s.access_token_ttl_minutes * 60
    payload = {
        "sub": str(user_id),
        "uni": str(university_id) if university_id else None,
        "pa": is_platform_admin,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm), ttl


def decode_access_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm],
                             options={"require": ["sub", "exp", "typ"]})
    except jwt.ExpiredSignatureError as e:
        raise Unauthorized("Sessiya muddati tugagan", code="TOKEN_EXPIRED") from e
    except jwt.PyJWTError as e:
        raise Unauthorized("Token yaroqsiz", code="TOKEN_INVALID") from e
    if payload.get("typ") != "access":
        raise Unauthorized("Token yaroqsiz", code="TOKEN_INVALID")
    return payload


def new_opaque_token() -> tuple[str, str]:
    """(xom token, sha256 xeshi). Bazada faqat xesh saqlanadi."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_opaque_token(raw)


def hash_opaque_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
