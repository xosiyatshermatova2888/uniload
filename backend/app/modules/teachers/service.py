import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, or_, select

from app.core import crud
from app.core.deps import Ctx
from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.modules.academic_years.models import AcademicYear
from app.modules.academic_years.service import get_editable_year, get_year
from app.modules.audit import service as audit
from app.modules.org.models import Department
from app.modules.teachers.models import POSITIONS, PositionNorm, Teacher, TeacherEmployment
from app.modules.teachers.schemas import (
    EmploymentIn,
    EmploymentOut,
    EmploymentUpdateIn,
    HistoryItem,
    PositionNormIn,
    PositionNormOut,
    TeacherIn,
    TeacherOut,
    TeacherUpdateIn,
)


def full_name(t: Teacher) -> str:
    return " ".join(p for p in (t.last_name, t.first_name, t.middle_name) if p)


def teacher_out(t: Teacher) -> TeacherOut:
    return TeacherOut(**TeacherOut.model_validate(t).model_dump(exclude={"full_name"}), full_name=full_name(t))


# ------------------------------------------------------------------ o‘qituvchilar

def list_teachers(ctx: Ctx, q: str | None, is_active: bool | None) -> list[TeacherOut]:
    stmt = select(Teacher).where(Teacher.university_id == ctx.university_id).order_by(
        Teacher.last_name, Teacher.first_name)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Teacher.last_name).like(like), func.lower(Teacher.first_name).like(like),
                              func.lower(Teacher.employee_no).like(like)))
    if is_active is not None:
        stmt = stmt.where(Teacher.is_active == is_active)
    return [teacher_out(t) for t in ctx.db.scalars(stmt)]


def get_teacher(ctx: Ctx, teacher_id: uuid.UUID) -> TeacherOut:
    return teacher_out(crud.get_or_404(ctx, Teacher, teacher_id, "O‘qituvchi topilmadi"))


def create_teacher(ctx: Ctx, body: TeacherIn) -> TeacherOut:
    t = crud.create(ctx, Teacher(university_id=ctx.university_id, **body.model_dump()), entity_type="teacher")
    ctx.db.commit()
    return teacher_out(t)


def update_teacher(ctx: Ctx, teacher_id: uuid.UUID, body: TeacherUpdateIn) -> TeacherOut:
    t = crud.get_or_404(ctx, Teacher, teacher_id, "O‘qituvchi topilmadi")
    crud.update(ctx, t, body.model_dump(exclude_unset=True), entity_type="teacher")
    ctx.db.commit()
    return teacher_out(t)


def history(ctx: Ctx, teacher_id: uuid.UUID) -> list[HistoryItem]:
    crud.get_or_404(ctx, Teacher, teacher_id, "O‘qituvchi topilmadi")
    rows = ctx.db.execute(
        select(TeacherEmployment, AcademicYear)
        .join(AcademicYear, AcademicYear.id == TeacherEmployment.academic_year_id)
        .where(TeacherEmployment.teacher_id == teacher_id).order_by(AcademicYear.start_year.desc())).all()
    return [HistoryItem(academic_year_id=y.id, year_label=y.label, year_status=y.status,
                        department_id=e.department_id, position_code=e.position_code,
                        employment_type=e.employment_type, rate=e.rate,
                        norm_hours=e.norm_hours) for e, y in rows]


# ------------------------------------------------------------------ lavozim me’yorlari

def _norms(ctx: Ctx, year_id: uuid.UUID) -> dict[str, PositionNorm]:
    return {n.position_code: n for n in ctx.db.scalars(
        select(PositionNorm).where(PositionNorm.academic_year_id == year_id))}


def _q(value: Decimal | None) -> Decimal | None:
    return value.quantize(Decimal("0.01")) if value is not None else None


def compute_norm_hours(rate: Decimal, norm: PositionNorm | None) -> Decimal | None:
    if norm is None or norm.norm_hours_per_rate is None:
        return None
    return (rate * norm.norm_hours_per_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def list_norms(ctx: Ctx, year_id: uuid.UUID) -> list[PositionNormOut]:
    get_year(ctx, year_id)
    existing = _norms(ctx, year_id)
    result = []
    for code, name in POSITIONS.items():
        n = existing.get(code)
        result.append(PositionNormOut(
            position_code=code, position_name=name,
            norm_hours_per_rate=n.norm_hours_per_rate if n else None,
            max_overload_pct=n.max_overload_pct if n else None,
            source_document=n.source_document if n else None, needs_review=n.needs_review if n else False))
    return result


def replace_norms(ctx: Ctx, year_id: uuid.UUID, items: list[PositionNormIn]) -> list[PositionNormOut]:
    year = get_editable_year(ctx, year_id)
    existing = _norms(ctx, year.id)
    before = {k: audit.snapshot(v) for k, v in existing.items()}
    for item in items:
        n = existing.get(item.position_code)
        if n is None:
            n = PositionNorm(university_id=ctx.university_id, academic_year_id=year.id,
                             position_code=item.position_code)
            ctx.db.add(n)
            existing[item.position_code] = n
        n.norm_hours_per_rate = _q(item.norm_hours_per_rate)
        n.max_overload_pct = _q(item.max_overload_pct)
        n.source_document, n.needs_review = item.source_document, False
    ctx.db.flush()
    # Me’yor o‘zgarsa — shu yil bandliklaridagi me’yoriy soat snapshot’i qayta hisoblanadi.
    for e in ctx.db.scalars(select(TeacherEmployment).where(TeacherEmployment.academic_year_id == year.id)):
        e.norm_hours = compute_norm_hours(e.rate, existing.get(e.position_code))
    ctx.db.flush()
    audit.record_ctx(ctx, action="position_norms.updated", entity_type="academic_year", entity_id=year.id,
                     academic_year_id=year.id, before={"norms": before},
                     after={"norms": {k: audit.snapshot(v) for k, v in existing.items()}})
    ctx.db.commit()
    return list_norms(ctx, year.id)


# ------------------------------------------------------------------ yillik bandlik

def _require_department_permission(ctx: Ctx, department_id: uuid.UUID) -> None:
    if not ctx.principal.has("teachers.manage", department_id=department_id):
        raise Forbidden("Bu kafedra o‘qituvchilarini boshqarish huquqingiz yo‘q")


def _employment_out(e: TeacherEmployment, t: Teacher) -> EmploymentOut:
    return EmploymentOut(**EmploymentOut.model_validate(e).model_dump(exclude={"teacher_name"}),
                         teacher_name=full_name(t))


def list_employment(ctx: Ctx, year_id: uuid.UUID, department_id: uuid.UUID | None,
                    teacher_id: uuid.UUID | None) -> list[EmploymentOut]:
    get_year(ctx, year_id)
    stmt = (select(TeacherEmployment, Teacher).join(Teacher, Teacher.id == TeacherEmployment.teacher_id)
            .where(TeacherEmployment.academic_year_id == year_id).order_by(Teacher.last_name, Teacher.first_name))
    # Kafedra ko‘lamidagi foydalanuvchi faqat o‘z kafedralarini ko‘radi.
    scope = ctx.principal.department_scope("teachers.view")
    if scope is not None:
        stmt = stmt.where(TeacherEmployment.department_id.in_(scope or {uuid.UUID(int=0)}))
    if department_id:
        stmt = stmt.where(TeacherEmployment.department_id == department_id)
    if teacher_id:
        stmt = stmt.where(TeacherEmployment.teacher_id == teacher_id)
    return [_employment_out(e, t) for e, t in ctx.db.execute(stmt)]


def _validate_dates(year: AcademicYear, starts_on, ends_on) -> None:
    for d in (starts_on, ends_on):
        if d is not None and not (year.starts_on <= d <= year.ends_on):
            raise ValidationFailed("Bandlik sanalari o‘quv yili chegarasida bo‘lishi kerak", code="DATES_OUT_OF_YEAR")


def create_employment(ctx: Ctx, year_id: uuid.UUID, body: EmploymentIn) -> EmploymentOut:
    year = get_editable_year(ctx, year_id)
    _require_department_permission(ctx, body.department_id)
    teacher = crud.get_or_404(ctx, Teacher, body.teacher_id, "O‘qituvchi topilmadi")
    if not teacher.is_active:
        raise ValidationFailed("Nofaol o‘qituvchiga bandlik qo‘shib bo‘lmaydi", code="TEACHER_INACTIVE")
    department = crud.get_or_404(ctx, Department, body.department_id, "Kafedra topilmadi")
    if not department.is_active:
        raise ValidationFailed("Nofaol kafedraga bandlik qo‘shib bo‘lmaydi", code="DEPARTMENT_INACTIVE")
    _validate_dates(year, body.starts_on, body.ends_on)
    norm = _norms(ctx, year.id).get(body.position_code)
    e = crud.create(ctx, TeacherEmployment(university_id=ctx.university_id, academic_year_id=year.id,
                                           norm_hours=compute_norm_hours(body.rate, norm), **body.model_dump()),
                    entity_type="teacher_employment", academic_year_id=year.id)
    ctx.db.commit()
    return _employment_out(e, teacher)


def _get_employment(ctx: Ctx, year_id: uuid.UUID, employment_id: uuid.UUID) -> TeacherEmployment:
    e = crud.get_or_404(ctx, TeacherEmployment, employment_id, "Bandlik topilmadi")
    if e.academic_year_id != year_id:
        raise NotFound("Bandlik topilmadi")
    return e


def update_employment(ctx: Ctx, year_id: uuid.UUID, employment_id: uuid.UUID,
                      body: EmploymentUpdateIn) -> EmploymentOut:
    year = get_editable_year(ctx, year_id)
    e = _get_employment(ctx, year.id, employment_id)
    _require_department_permission(ctx, e.department_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("department_id"):
        _require_department_permission(ctx, data["department_id"])
        crud.get_or_404(ctx, Department, data["department_id"], "Kafedra topilmadi")
    _validate_dates(year, data.get("starts_on", e.starts_on), data.get("ends_on", e.ends_on))
    rate, position = data.get("rate", e.rate), data.get("position_code", e.position_code)
    data["norm_hours"] = compute_norm_hours(rate, _norms(ctx, year.id).get(position))
    crud.update(ctx, e, data, entity_type="teacher_employment", academic_year_id=year.id)
    ctx.db.commit()
    return _employment_out(e, ctx.db.get(Teacher, e.teacher_id))


def delete_employment(ctx: Ctx, year_id: uuid.UUID, employment_id: uuid.UUID) -> None:
    year = get_editable_year(ctx, year_id)
    e = _get_employment(ctx, year.id, employment_id)
    _require_department_permission(ctx, e.department_id)
    crud.delete(ctx, e, entity_type="teacher_employment", academic_year_id=year.id)
    ctx.db.commit()
