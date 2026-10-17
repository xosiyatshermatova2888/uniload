import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.core.deps import Ctx
from app.core.errors import AppError, Conflict, Forbidden, NotFound, ValidationFailed
from app.modules.academic_years import domain
from app.modules.academic_years.models import AcademicYear, Semester
from app.modules.academic_years.schemas import (
    AcademicYearCreateIn,
    AcademicYearDetailOut,
    AcademicYearOut,
    AcademicYearUpdateIn,
    CopyPreviewOut,
    SemesterIn,
    SemesterOut,
    TransitionIn,
)
from app.modules.audit import service as audit

NOT_YET_AVAILABLE = [
    "Lavozim me’yorlari (2-bosqich)",
    "O‘qituvchilar bandligi (2-bosqich)",
    "Akademik guruhlar va kursni ko‘tarish (2-bosqich)",
    "Oqimlar (2-bosqich)",
]


def _check_version(obj, row_version: int) -> None:
    if obj.row_version != row_version:
        raise Conflict("Yozuv boshqa foydalanuvchi tomonidan o‘zgartirildi. Sahifani yangilang.",
                       code="CONCURRENT_UPDATE")


def to_out(year: AcademicYear) -> AcademicYearOut:
    return AcademicYearOut(
        id=year.id, start_year=year.start_year, end_year=year.end_year, label=year.label,
        status=year.status, status_label=domain.STATUS_LABELS[year.status], is_current=year.is_current,
        is_locked=year.status in domain.LOCKED_STATUSES, source_year_id=year.source_year_id,
        starts_on=year.starts_on, ends_on=year.ends_on, approved_at=year.approved_at,
        archived_at=year.archived_at, created_at=year.created_at, row_version=year.row_version,
        allowed_transitions=domain.allowed_targets(year.status),
    )


def get_year(ctx: Ctx, year_id: uuid.UUID) -> AcademicYear:
    # RLS boshqa tenant yilini baribir yashiradi; shart — ikkinchi himoya qatlami.
    year = ctx.db.scalar(select(AcademicYear).where(AcademicYear.id == year_id,
                                                    AcademicYear.university_id == ctx.university_id))
    if year is None:
        raise NotFound("O‘quv yili topilmadi")
    return year


def _semesters(ctx: Ctx, year_id: uuid.UUID) -> list[Semester]:
    return list(ctx.db.scalars(select(Semester).where(Semester.academic_year_id == year_id)
                               .order_by(Semester.term)))


def detail(ctx: Ctx, year: AcademicYear) -> AcademicYearDetailOut:
    source = ctx.db.get(AcademicYear, year.source_year_id) if year.source_year_id else None
    return AcademicYearDetailOut(**to_out(year).model_dump(),
                                 semesters=[SemesterOut.model_validate(s) for s in _semesters(ctx, year.id)],
                                 source_label=source.label if source else None)


def list_years(ctx: Ctx) -> list[AcademicYearOut]:
    years = ctx.db.scalars(select(AcademicYear).where(AcademicYear.university_id == ctx.university_id)
                           .order_by(AcademicYear.start_year.desc()))
    return [to_out(y) for y in years]


def _plan(ctx: Ctx, body: AcademicYearCreateIn) -> tuple[CopyPreviewOut, AcademicYear | None]:
    exists = ctx.db.scalar(select(AcademicYear.id).where(AcademicYear.university_id == ctx.university_id,
                                                         AcademicYear.start_year == body.start_year)) is not None
    default_start, default_end = domain.default_year_dates(body.start_year)
    starts_on, ends_on = body.starts_on or default_start, body.ends_on or default_end
    warnings: list[str] = []
    source: AcademicYear | None = None
    specs = domain.default_semesters(body.start_year)

    if body.mode == "copy":
        if body.source_year_id is None:
            raise ValidationFailed("Nusxalash uchun manba o‘quv yilini tanlang", code="SOURCE_REQUIRED")
        source = get_year(ctx, body.source_year_id)
        gap = body.start_year - source.start_year
        if gap <= 0:
            raise ValidationFailed("Manba yil yangi yildan oldin bo‘lishi kerak", code="SOURCE_AFTER_TARGET")
        if gap > 1:
            warnings.append(f"Manba yil {source.label} — yangi yildan {gap} yil oldin.")
        if body.options.semesters:
            specs = [domain.SemesterSpec(s.term, s.name, domain.shift_year(s.starts_on, gap),
                                         domain.shift_year(s.ends_on, gap), s.weeks)
                     for s in _semesters(ctx, source.id)] or specs

    errors = domain.validate_semesters(specs, starts_on, ends_on)
    if errors:
        warnings.extend(errors)
    preview = CopyPreviewOut(
        label=domain.label(body.start_year), already_exists=exists, mode=body.mode,
        source_label=source.label if source else None, starts_on=starts_on, ends_on=ends_on,
        semesters=[SemesterIn(term=s.term, name=s.name, starts_on=s.starts_on, ends_on=s.ends_on, weeks=s.weeks)
                   for s in specs],
        will_copy={"semesters": len(specs) if source and body.options.semesters else 0},
        not_yet_available=NOT_YET_AVAILABLE if body.mode == "copy" else [],
        warnings=warnings,
    )
    return preview, source


def preview(ctx: Ctx, body: AcademicYearCreateIn) -> CopyPreviewOut:
    return _plan(ctx, body)[0]


def create_year(ctx: Ctx, body: AcademicYearCreateIn) -> AcademicYearDetailOut:
    plan, source = _plan(ctx, body)
    if plan.already_exists:
        raise Conflict(f"{plan.label} o‘quv yili allaqachon mavjud", code="YEAR_EXISTS")
    sem_errors = domain.validate_semesters(
        [domain.SemesterSpec(s.term, s.name, s.starts_on, s.ends_on, s.weeks) for s in plan.semesters],
        plan.starts_on, plan.ends_on)
    if sem_errors:
        raise ValidationFailed("; ".join(sem_errors), code="SEMESTERS_INVALID")

    has_current = ctx.db.scalar(select(AcademicYear.id).where(AcademicYear.university_id == ctx.university_id,
                                                              AcademicYear.is_current)) is not None
    year = AcademicYear(university_id=ctx.university_id, start_year=body.start_year,
                        end_year=body.start_year + 1, status="draft", is_current=not has_current,
                        source_year_id=source.id if source else None,
                        starts_on=plan.starts_on, ends_on=plan.ends_on)
    ctx.db.add(year)
    ctx.db.flush()
    for s in plan.semesters:
        ctx.db.add(Semester(university_id=ctx.university_id, academic_year_id=year.id, term=s.term,
                            name=s.name, starts_on=s.starts_on, ends_on=s.ends_on, weeks=s.weeks))
    ctx.db.flush()
    ctx.db.refresh(year)  # label — DB’da hisoblanadigan ustun
    audit.record_ctx(ctx, action="academic_year.created", entity_type="academic_year", entity_id=year.id,
                     academic_year_id=year.id,
                     after={**audit.snapshot(year), "mode": body.mode, "copied": plan.will_copy})
    ctx.db.commit()
    return detail(ctx, year)


def update_year(ctx: Ctx, year_id: uuid.UUID, body: AcademicYearUpdateIn) -> AcademicYearDetailOut:
    year = get_year(ctx, year_id)
    if year.status in domain.LOCKED_STATUSES:
        raise Conflict("Tasdiqlangan yoki arxivlangan o‘quv yilini tahrirlab bo‘lmaydi", code="YEAR_LOCKED")
    _check_version(year, body.row_version)
    before = audit.snapshot(year)
    data = body.model_dump(exclude_unset=True, exclude={"row_version"})
    for key, value in data.items():
        if value is not None:
            setattr(year, key, value)
    if year.ends_on <= year.starts_on:
        raise ValidationFailed("Tugash sanasi boshlanish sanasidan keyin bo‘lishi kerak", code="DATES_INVALID")
    errors = domain.validate_semesters(
        [domain.SemesterSpec(s.term, s.name, s.starts_on, s.ends_on, s.weeks) for s in _semesters(ctx, year.id)],
        year.starts_on, year.ends_on)
    if errors:
        raise ValidationFailed("; ".join(errors), code="SEMESTERS_INVALID")
    ctx.db.flush()
    b, a = audit.diff(before, audit.snapshot(year))
    if a:
        audit.record_ctx(ctx, action="academic_year.updated", entity_type="academic_year", entity_id=year.id,
                         academic_year_id=year.id, before=b, after=a)
    ctx.db.commit()
    return detail(ctx, year)


def transition(ctx: Ctx, year_id: uuid.UUID, body: TransitionIn) -> AcademicYearDetailOut:
    year = get_year(ctx, year_id)
    _check_version(year, body.row_version)
    permission = domain.required_permission(body.to)
    if not ctx.principal.has(permission, university_wide=True):
        raise Forbidden(f"Kerakli ruxsat: {permission}")
    try:
        domain.check_transition(domain.TransitionRequest(year.status, body.to, body.comment), context=ctx)
    except domain.TransitionError as e:
        raise AppError(e.message, status=409, code=e.code, title="Holatni o‘zgartirib bo‘lmaydi") from e

    previous = year.status
    now = datetime.now(UTC)
    year.status = body.to
    if body.to == "approved":
        year.approved_at, year.approved_by = now, ctx.principal.user_id
    if body.to == "archived":
        year.archived_at = now
    ctx.db.flush()
    audit.record_ctx(ctx, action="academic_year.status_changed", entity_type="academic_year",
                     entity_id=year.id, academic_year_id=year.id,
                     before={"status": previous}, after={"status": body.to}, reason=body.comment)
    ctx.db.commit()
    return detail(ctx, year)


def set_current(ctx: Ctx, year_id: uuid.UUID) -> AcademicYearDetailOut:
    year = get_year(ctx, year_id)
    if year.status == "archived":
        raise Conflict("Arxivlangan yilni joriy qilib bo‘lmaydi", code="YEAR_ARCHIVED")
    if year.is_current:
        return detail(ctx, year)
    previous = ctx.db.scalar(select(AcademicYear).where(AcademicYear.university_id == ctx.university_id,
                                                        AcademicYear.is_current))
    if previous is not None:
        previous.is_current = False
        ctx.db.flush()  # partial unique index: avval eskisini o‘chiramiz
    year.is_current = True
    ctx.db.flush()
    audit.record_ctx(ctx, action="academic_year.set_current", entity_type="academic_year", entity_id=year.id,
                     academic_year_id=year.id,
                     before={"current_year_id": str(previous.id) if previous else None},
                     after={"current_year_id": str(year.id)})
    ctx.db.commit()
    return detail(ctx, year)


def replace_semesters(ctx: Ctx, year_id: uuid.UUID, items: list[SemesterIn]) -> list[SemesterOut]:
    year = get_year(ctx, year_id)
    if year.status in domain.LOCKED_STATUSES:
        raise Conflict("Tasdiqlangan yoki arxivlangan o‘quv yilini tahrirlab bo‘lmaydi", code="YEAR_LOCKED")
    specs = [domain.SemesterSpec(s.term, s.name, s.starts_on, s.ends_on, s.weeks) for s in items]
    errors = domain.validate_semesters(specs, year.starts_on, year.ends_on)
    if errors:
        raise ValidationFailed("; ".join(errors), code="SEMESTERS_INVALID")
    existing = {s.term: s for s in _semesters(ctx, year.id)}
    before = [SemesterOut.model_validate(s).model_dump(mode="json") for s in existing.values()]
    for spec in specs:
        sem = existing.pop(spec.term, None)
        if sem is None:
            ctx.db.add(Semester(university_id=ctx.university_id, academic_year_id=year.id, term=spec.term,
                                name=spec.name, starts_on=spec.starts_on, ends_on=spec.ends_on, weeks=spec.weeks))
        else:
            sem.name, sem.starts_on, sem.ends_on, sem.weeks = spec.name, spec.starts_on, spec.ends_on, spec.weeks
    if existing:
        ctx.db.execute(delete(Semester).where(Semester.id.in_([s.id for s in existing.values()])))
    ctx.db.flush()
    result = _semesters(ctx, year.id)
    audit.record_ctx(ctx, action="academic_year.semesters_updated", entity_type="academic_year",
                     entity_id=year.id, academic_year_id=year.id, before={"semesters": before},
                     after={"semesters": [SemesterOut.model_validate(s).model_dump(mode="json") for s in result]})
    ctx.db.commit()
    return [SemesterOut.model_validate(s) for s in result]
