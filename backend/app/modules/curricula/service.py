import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core import crud
from app.core.deps import Ctx
from app.core.errors import Conflict, Forbidden, ValidationFailed
from app.modules.audit import service as audit
from app.modules.curricula.models import (
    SYSTEM_LESSON_TYPES,
    Curriculum,
    CurriculumSubject,
    CurriculumSubjectHours,
    LessonType,
    Subject,
)
from app.modules.curricula.schemas import (
    CurriculumApproveIn,
    CurriculumDetailOut,
    CurriculumIn,
    CurriculumOut,
    CurriculumSubjectIn,
    CurriculumSubjectOut,
    CurriculumSubjectUpdateIn,
    CurriculumUpdateIn,
    LessonTypeIn,
    LessonTypeUpdateIn,
    SubjectIn,
    SubjectUpdateIn,
)
from app.modules.org.models import Department, EducationProgram


def ensure_lesson_types(db: Session, university_id: uuid.UUID) -> int:
    """Universitet uchun tizim mashg‘ulot turlarini yaratadi (idempotent)."""
    existing = set(db.scalars(select(LessonType.code).where(LessonType.university_id == university_id)))
    added = 0
    for order, (code, name, auditorium, counts) in enumerate(SYSTEM_LESSON_TYPES):
        if code not in existing:
            db.add(LessonType(university_id=university_id, code=code, name=name, is_auditorium=auditorium,
                              counts_in_workload=counts, is_system=True, sort_order=(order + 1) * 10))
            added += 1
    db.flush()
    return added


# ------------------------------------------------------------------ mashg‘ulot turlari

def list_lesson_types(ctx: Ctx) -> list[LessonType]:
    return list(ctx.db.scalars(select(LessonType).where(LessonType.university_id == ctx.university_id)
                               .order_by(LessonType.sort_order, LessonType.code)))


def create_lesson_type(ctx: Ctx, body: LessonTypeIn) -> LessonType:
    obj = crud.create(ctx, LessonType(university_id=ctx.university_id, is_system=False, **body.model_dump()),
                      entity_type="lesson_type")
    ctx.db.commit()
    return obj


def update_lesson_type(ctx: Ctx, lesson_type_id: uuid.UUID, body: LessonTypeUpdateIn) -> LessonType:
    obj = crud.get_or_404(ctx, LessonType, lesson_type_id, "Mashg‘ulot turi topilmadi")
    crud.update(ctx, obj, body.model_dump(exclude_unset=True), entity_type="lesson_type")
    ctx.db.commit()
    return obj


def delete_lesson_type(ctx: Ctx, lesson_type_id: uuid.UUID) -> None:
    obj = crud.get_or_404(ctx, LessonType, lesson_type_id, "Mashg‘ulot turi topilmadi")
    if obj.is_system:
        raise Forbidden("Tizim mashg‘ulot turini o‘chirib bo‘lmaydi", code="SYSTEM_LESSON_TYPE")
    crud.delete(ctx, obj, entity_type="lesson_type")
    ctx.db.commit()


# ------------------------------------------------------------------ fanlar

def list_subjects(ctx: Ctx, q: str | None, department_id: uuid.UUID | None, is_active: bool | None):
    stmt = select(Subject).where(Subject.university_id == ctx.university_id).order_by(Subject.name_uz)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Subject.name_uz).like(like), func.lower(Subject.code).like(like)))
    if department_id:
        stmt = stmt.where(Subject.default_department_id == department_id)
    if is_active is not None:
        stmt = stmt.where(Subject.is_active == is_active)
    return list(ctx.db.scalars(stmt))


def create_subject(ctx: Ctx, body: SubjectIn) -> Subject:
    if body.default_department_id:
        crud.get_or_404(ctx, Department, body.default_department_id, "Kafedra topilmadi")
    obj = crud.create(ctx, Subject(university_id=ctx.university_id, **body.model_dump()), entity_type="subject")
    ctx.db.commit()
    return obj


def update_subject(ctx: Ctx, subject_id: uuid.UUID, body: SubjectUpdateIn) -> Subject:
    obj = crud.get_or_404(ctx, Subject, subject_id, "Fan topilmadi")
    data = body.model_dump(exclude_unset=True)
    if data.get("default_department_id"):
        crud.get_or_404(ctx, Department, data["default_department_id"], "Kafedra topilmadi")
    crud.update(ctx, obj, data, entity_type="subject")
    ctx.db.commit()
    return obj


def delete_subject(ctx: Ctx, subject_id: uuid.UUID) -> None:
    crud.delete(ctx, crud.get_or_404(ctx, Subject, subject_id, "Fan topilmadi"), entity_type="subject")
    ctx.db.commit()


# ------------------------------------------------------------------ o‘quv rejalari

def _summary(ctx: Ctx, curriculum_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, Decimal | None]]:
    if not curriculum_ids:
        return {}
    rows = ctx.db.execute(
        select(CurriculumSubject.curriculum_id, func.count(), func.sum(CurriculumSubject.credits))
        .where(CurriculumSubject.curriculum_id.in_(curriculum_ids)).group_by(CurriculumSubject.curriculum_id))
    return {cid: (n, credits) for cid, n, credits in rows}


def _out(c: Curriculum, summary: tuple[int, Decimal | None] | None) -> CurriculumOut:
    n, credits = summary or (0, None)
    return CurriculumOut(**CurriculumOut.model_validate(c).model_dump(exclude={"subjects_count", "total_credits"}),
                         subjects_count=n, total_credits=credits)


def list_curricula(ctx: Ctx, program_id: uuid.UUID | None, status: str | None, admission_year: int | None,
                   education_form: str | None) -> list[CurriculumOut]:
    stmt = select(Curriculum).where(Curriculum.university_id == ctx.university_id).order_by(
        Curriculum.admission_year.desc(), Curriculum.education_program_id, Curriculum.version.desc())
    if program_id:
        stmt = stmt.where(Curriculum.education_program_id == program_id)
    if status:
        stmt = stmt.where(Curriculum.status == status)
    if admission_year:
        stmt = stmt.where(Curriculum.admission_year == admission_year)
    if education_form:
        stmt = stmt.where(Curriculum.education_form == education_form)
    items = list(ctx.db.scalars(stmt))
    summary = _summary(ctx, [c.id for c in items])
    return [_out(c, summary.get(c.id)) for c in items]


def _lesson_type_maps(ctx: Ctx) -> tuple[dict[str, uuid.UUID], dict[uuid.UUID, str]]:
    types = list_lesson_types(ctx)
    return {t.code: t.id for t in types}, {t.id: t.code for t in types}


def detail(ctx: Ctx, curriculum_id: uuid.UUID) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    program = ctx.db.get(EducationProgram, c.education_program_id)
    _, code_by_id = _lesson_type_maps(ctx)
    rows = ctx.db.execute(
        select(CurriculumSubject, Subject).join(Subject, Subject.id == CurriculumSubject.subject_id)
        .where(CurriculumSubject.curriculum_id == c.id)
        .order_by(CurriculumSubject.semester_no, Subject.name_uz)).all()
    hours: dict[uuid.UUID, dict[str, Decimal]] = defaultdict(dict)
    for h in ctx.db.scalars(select(CurriculumSubjectHours).where(
            CurriculumSubjectHours.curriculum_subject_id.in_([cs.id for cs, _ in rows]))):
        hours[h.curriculum_subject_id][code_by_id[h.lesson_type_id]] = h.hours
    totals: dict[int, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    subjects = []
    for cs, subj in rows:
        for code, value in hours[cs.id].items():
            totals[cs.semester_no][code] += value
        subjects.append(CurriculumSubjectOut(
            id=cs.id, subject_id=subj.id, subject_code=subj.code, subject_name=subj.name_uz,
            semester_no=cs.semester_no, credits=cs.credits, department_id=cs.department_id,
            control_type=cs.control_type, is_elective=cs.is_elective, elective_group=cs.elective_group,
            row_version=cs.row_version, hours=hours[cs.id]))
    summary = _summary(ctx, [c.id]).get(c.id)
    return CurriculumDetailOut(**_out(c, summary).model_dump(), duration_years=program.duration_years,
                               subjects=subjects, totals_by_semester={k: dict(v) for k, v in totals.items()})


def _require_draft(c: Curriculum) -> None:
    if c.status != "draft":
        raise Conflict("Tasdiqlangan o‘quv rejani o‘zgartirib bo‘lmaydi — yangi versiya yarating",
                       code="CURRICULUM_LOCKED")


def create_curriculum(ctx: Ctx, body: CurriculumIn) -> CurriculumDetailOut:
    crud.get_or_404(ctx, EducationProgram, body.education_program_id, "Ta’lim yo‘nalishi topilmadi")
    latest = ctx.db.scalar(select(func.max(Curriculum.version)).where(
        Curriculum.university_id == ctx.university_id,
        Curriculum.education_program_id == body.education_program_id,
        Curriculum.education_form == body.education_form,
        Curriculum.admission_year == body.admission_year))
    c = crud.create(ctx, Curriculum(university_id=ctx.university_id, version=(latest or 0) + 1, status="draft",
                                    **body.model_dump()), entity_type="curriculum")
    ctx.db.commit()
    return detail(ctx, c.id)


def update_curriculum(ctx: Ctx, curriculum_id: uuid.UUID, body: CurriculumUpdateIn) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    _require_draft(c)
    crud.update(ctx, c, body.model_dump(exclude_unset=True), entity_type="curriculum")
    ctx.db.commit()
    return detail(ctx, c.id)


def delete_curriculum(ctx: Ctx, curriculum_id: uuid.UUID) -> None:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    _require_draft(c)
    crud.delete(ctx, c, entity_type="curriculum")
    ctx.db.commit()


def approve(ctx: Ctx, curriculum_id: uuid.UUID, body: CurriculumApproveIn) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    crud.check_version(c, body.row_version)
    _require_draft(c)
    count = ctx.db.scalar(select(func.count()).select_from(CurriculumSubject)
                          .where(CurriculumSubject.curriculum_id == c.id))
    if not count:
        raise ValidationFailed("Bo‘sh o‘quv rejani tasdiqlab bo‘lmaydi", code="CURRICULUM_EMPTY")
    c.status, c.approval_doc = "approved", body.approval_doc
    c.approved_at, c.approved_by = datetime.now(UTC), ctx.principal.user_id
    ctx.db.flush()
    audit.record_ctx(ctx, action="curriculum.approved", entity_type="curriculum", entity_id=c.id,
                     before={"status": "draft"}, after={"status": "approved", "approval_doc": body.approval_doc})
    ctx.db.commit()
    return detail(ctx, c.id)


def archive(ctx: Ctx, curriculum_id: uuid.UUID, row_version: int) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    crud.check_version(c, row_version)
    if c.status != "approved":
        raise Conflict("Faqat tasdiqlangan o‘quv rejani arxivlash mumkin", code="INVALID_STATUS")
    c.status = "archived"
    ctx.db.flush()
    audit.record_ctx(ctx, action="curriculum.archived", entity_type="curriculum", entity_id=c.id,
                     before={"status": "approved"}, after={"status": "archived"})
    ctx.db.commit()
    return detail(ctx, c.id)


def new_version(ctx: Ctx, curriculum_id: uuid.UUID) -> CurriculumDetailOut:
    """Tasdiqlangan (yoki arxiv) rejadan tarkibi bir xil yangi qoralama versiya — eski versiya o‘zgarmaydi."""
    src = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    if src.status == "draft":
        raise Conflict("Qoralama rejani to‘g‘ridan-to‘g‘ri tahrirlang", code="INVALID_STATUS")
    latest = ctx.db.scalar(select(func.max(Curriculum.version)).where(
        Curriculum.university_id == ctx.university_id, Curriculum.education_program_id == src.education_program_id,
        Curriculum.education_form == src.education_form, Curriculum.admission_year == src.admission_year))
    c = Curriculum(university_id=ctx.university_id, education_program_id=src.education_program_id,
                   education_form=src.education_form, admission_year=src.admission_year, version=latest + 1,
                   status="draft", title=src.title, based_on_id=src.id)
    ctx.db.add(c)
    ctx.db.flush()
    src_subjects = list(ctx.db.scalars(select(CurriculumSubject).where(CurriculumSubject.curriculum_id == src.id)))
    hours = list(ctx.db.scalars(select(CurriculumSubjectHours).where(
        CurriculumSubjectHours.curriculum_subject_id.in_([s.id for s in src_subjects]))))
    by_subject: dict[uuid.UUID, list[CurriculumSubjectHours]] = defaultdict(list)
    for h in hours:
        by_subject[h.curriculum_subject_id].append(h)
    for s in src_subjects:
        cs = CurriculumSubject(university_id=ctx.university_id, curriculum_id=c.id, subject_id=s.subject_id,
                               semester_no=s.semester_no, credits=s.credits, department_id=s.department_id,
                               control_type=s.control_type, is_elective=s.is_elective, elective_group=s.elective_group)
        ctx.db.add(cs)
        ctx.db.flush()
        ctx.db.add_all([CurriculumSubjectHours(university_id=ctx.university_id, curriculum_subject_id=cs.id,
                                               lesson_type_id=h.lesson_type_id, hours=h.hours)
                        for h in by_subject[s.id]])
    ctx.db.flush()
    audit.record_ctx(ctx, action="curriculum.created", entity_type="curriculum", entity_id=c.id,
                     after={**audit.snapshot(c), "based_on": str(src.id), "subjects": len(src_subjects)})
    ctx.db.commit()
    return detail(ctx, c.id)


# ------------------------------------------------------------------ reja fanlari

def _set_hours(ctx: Ctx, cs: CurriculumSubject, hours: dict[str, Decimal]) -> None:
    id_by_code, _ = _lesson_type_maps(ctx)
    unknown = set(hours) - id_by_code.keys()
    if unknown:
        raise ValidationFailed(f"Noma’lum mashg‘ulot turlari: {', '.join(sorted(unknown))}", code="UNKNOWN_LESSON_TYPE")
    if any(v < 0 for v in hours.values()):
        raise ValidationFailed("Soat manfiy bo‘lishi mumkin emas", code="NEGATIVE_HOURS")
    ctx.db.execute(delete(CurriculumSubjectHours).where(CurriculumSubjectHours.curriculum_subject_id == cs.id))
    ctx.db.add_all([CurriculumSubjectHours(university_id=ctx.university_id, curriculum_subject_id=cs.id,
                                           lesson_type_id=id_by_code[code], hours=value)
                    for code, value in hours.items() if value > 0])


def _check_semester(ctx: Ctx, c: Curriculum, semester_no: int) -> None:
    program = ctx.db.get(EducationProgram, c.education_program_id)
    if semester_no > program.duration_years * 2:
        raise ValidationFailed(f"Semestr {semester_no} — yo‘nalish davomiyligidan ({program.duration_years} yil) "
                               "tashqarida", code="SEMESTER_OUT_OF_RANGE")


def add_subject(ctx: Ctx, curriculum_id: uuid.UUID, body: CurriculumSubjectIn) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    _require_draft(c)
    _check_semester(ctx, c, body.semester_no)
    subject = crud.get_or_404(ctx, Subject, body.subject_id, "Fan topilmadi")
    department_id = body.department_id or subject.default_department_id
    if department_id is None:
        raise ValidationFailed("Fanni o‘qitadigan kafedrani ko‘rsating", code="DEPARTMENT_REQUIRED")
    crud.get_or_404(ctx, Department, department_id, "Kafedra topilmadi")
    data = body.model_dump(exclude={"hours", "department_id"})
    cs = crud.create(ctx, CurriculumSubject(university_id=ctx.university_id, curriculum_id=c.id,
                                            department_id=department_id, **data),
                     entity_type="curriculum_subject", extra={"hours": {k: str(v) for k, v in body.hours.items()}})
    _set_hours(ctx, cs, body.hours)
    ctx.db.commit()
    return detail(ctx, c.id)


def update_subject_entry(ctx: Ctx, curriculum_id: uuid.UUID, entry_id: uuid.UUID,
                         body: CurriculumSubjectUpdateIn) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    _require_draft(c)
    cs = crud.get_or_404(ctx, CurriculumSubject, entry_id, "Reja fani topilmadi")
    if cs.curriculum_id != c.id:
        raise ValidationFailed("Fan bu o‘quv rejaga tegishli emas", code="WRONG_CURRICULUM")
    data = body.model_dump(exclude_unset=True, exclude={"hours"})
    if data.get("semester_no"):
        _check_semester(ctx, c, data["semester_no"])
    if data.get("department_id"):
        crud.get_or_404(ctx, Department, data["department_id"], "Kafedra topilmadi")
    crud.update(ctx, cs, data, entity_type="curriculum_subject")
    if body.hours is not None:
        _set_hours(ctx, cs, body.hours)
        audit.record_ctx(ctx, action="curriculum_subject.hours_updated", entity_type="curriculum_subject",
                         entity_id=cs.id, after={"hours": {k: str(v) for k, v in body.hours.items()}})
    ctx.db.commit()
    return detail(ctx, c.id)


def remove_subject(ctx: Ctx, curriculum_id: uuid.UUID, entry_id: uuid.UUID) -> CurriculumDetailOut:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    _require_draft(c)
    cs = crud.get_or_404(ctx, CurriculumSubject, entry_id, "Reja fani topilmadi")
    if cs.curriculum_id != c.id:
        raise ValidationFailed("Fan bu o‘quv rejaga tegishli emas", code="WRONG_CURRICULUM")
    crud.delete(ctx, cs, entity_type="curriculum_subject")
    ctx.db.commit()
    return detail(ctx, c.id)
