"""Ma’lumotnoma modullari uchun umumiy yordamchilar: tenant bo‘yicha olish, optimistik qulf,
o‘zgarishlarni qo‘llash va auditga yozish."""

import uuid
from typing import Any, TypeVar

from sqlalchemy import select

from app.core.deps import Ctx
from app.core.errors import Conflict, NotFound
from app.modules.audit import service as audit

T = TypeVar("T")


def get_or_404(ctx: Ctx, model: type[T], obj_id: uuid.UUID, message: str = "Yozuv topilmadi") -> T:
    # RLS boshqa tenant yozuvini baribir yashiradi; shart — ikkinchi himoya qatlami.
    obj = ctx.db.scalar(select(model).where(model.id == obj_id, model.university_id == ctx.university_id))
    if obj is None:
        raise NotFound(message)
    return obj


def check_version(obj: Any, row_version: int) -> None:
    if obj.row_version != row_version:
        raise Conflict("Yozuv boshqa foydalanuvchi tomonidan o‘zgartirildi. Sahifani yangilang.",
                       code="CONCURRENT_UPDATE")


def create(ctx: Ctx, obj: T, *, entity_type: str, academic_year_id: uuid.UUID | None = None,
           extra: dict[str, Any] | None = None) -> T:
    ctx.db.add(obj)
    ctx.db.flush()
    audit.record_ctx(ctx, action=f"{entity_type}.created", entity_type=entity_type, entity_id=obj.id,
                     academic_year_id=academic_year_id, after={**audit.snapshot(obj), **(extra or {})})
    return obj


def update(ctx: Ctx, obj: T, data: dict[str, Any], *, entity_type: str,
           academic_year_id: uuid.UUID | None = None) -> T:
    """`data` ichida `row_version` bo‘lishi shart; qolgan maydonlar obyektga yoziladi."""
    check_version(obj, data.pop("row_version"))
    before = audit.snapshot(obj)
    for key, value in data.items():
        setattr(obj, key, value)
    ctx.db.flush()
    b, a = audit.diff(before, audit.snapshot(obj))
    if a:
        audit.record_ctx(ctx, action=f"{entity_type}.updated", entity_type=entity_type, entity_id=obj.id,
                         academic_year_id=academic_year_id, before=b, after=a)
    return obj


def delete(ctx: Ctx, obj: Any, *, entity_type: str, academic_year_id: uuid.UUID | None = None) -> None:
    snap = audit.snapshot(obj)
    ctx.db.delete(obj)
    ctx.db.flush()  # FK RESTRICT xatosi shu yerda — 409 REFERENCE_ERROR sifatida qaytadi
    audit.record_ctx(ctx, action=f"{entity_type}.deleted", entity_type=entity_type, entity_id=snap["id"],
                     academic_year_id=academic_year_id, before=snap)
