import uuid

from sqlalchemy import delete, func, select

from app.core import crud
from app.core.deps import Ctx
from app.core.errors import NotFound, ValidationFailed
from app.modules.academic_years.models import Semester
from app.modules.academic_years.service import get_editable_year, get_year
from app.modules.audit import service as audit
from app.modules.curricula.models import Curriculum, CurriculumSubject, LessonType, Subject
from app.modules.groups.models import Stream, StreamGroup, StudentGroup
from app.modules.groups.schemas import GroupBulkItem, GroupIn, GroupUpdateIn, StreamIn, StreamOut, StreamUpdateIn
from app.modules.org.models import EducationProgram


def curriculum_semester(course: int, term: int) -> int:
    """`course`-kurs guruhi `term`-semestrda o‘quv rejaning qaysi semestrini o‘qiydi (docs/05, 5.4)."""
    return 2 * course - 2 + term


def _get_group(ctx: Ctx, year_id: uuid.UUID, group_id: uuid.UUID) -> StudentGroup:
    group = crud.get_or_404(ctx, StudentGroup, group_id, "Guruh topilmadi")
    if group.academic_year_id != year_id:
        raise NotFound("Guruh topilmadi")
    return group


def _validate_curriculum(ctx: Ctx, curriculum_id: uuid.UUID, course: int) -> None:
    c = crud.get_or_404(ctx, Curriculum, curriculum_id, "O‘quv reja topilmadi")
    if c.status == "archived":
        raise ValidationFailed("Arxivlangan o‘quv rejaga guruh biriktirib bo‘lmaydi", code="CURRICULUM_ARCHIVED")
    program = ctx.db.get(EducationProgram, c.education_program_id)
    if course > program.duration_years:
        raise ValidationFailed(f"{course}-kurs — yo‘nalish davomiyligidan ({program.duration_years} yil) katta",
                               code="COURSE_OUT_OF_RANGE")


def _check_contingent(group: StudentGroup, data: dict) -> None:
    """Yakuniy qiymatlar bo‘yicha: byudjet + kontrakt = jami (agar ikkalasi kiritilgan bo‘lsa)."""
    total = data.get("student_count", group.student_count)
    budget = data.get("budget_count", group.budget_count)
    contract = data.get("contract_count", group.contract_count)
    if budget is not None and contract is not None and budget + contract != total:
        raise ValidationFailed(f"{group.code}: byudjet ({budget}) + kontrakt ({contract}) talabalar umumiy soniga "
                               f"({total}) teng emas", code="CONTINGENT_MISMATCH")


def list_groups(ctx: Ctx, year_id: uuid.UUID, q: str | None, curriculum_id: uuid.UUID | None,
                course: int | None, needs_review: bool | None) -> list[StudentGroup]:
    get_year(ctx, year_id)
    stmt = select(StudentGroup).where(StudentGroup.academic_year_id == year_id).order_by(
        StudentGroup.course, StudentGroup.code)
    if q:
        stmt = stmt.where(func.lower(StudentGroup.code).like(f"%{q.strip().lower()}%"))
    if curriculum_id:
        stmt = stmt.where(StudentGroup.curriculum_id == curriculum_id)
    if course:
        stmt = stmt.where(StudentGroup.course == course)
    if needs_review is not None:
        stmt = stmt.where(StudentGroup.needs_review == needs_review)
    return list(ctx.db.scalars(stmt))


def create_group(ctx: Ctx, year_id: uuid.UUID, body: GroupIn) -> StudentGroup:
    year = get_editable_year(ctx, year_id)
    _validate_curriculum(ctx, body.curriculum_id, body.course)
    obj = crud.create(ctx, StudentGroup(university_id=ctx.university_id, academic_year_id=year.id,
                                        **body.model_dump()), entity_type="student_group", academic_year_id=year.id)
    ctx.db.commit()
    return obj


def update_group(ctx: Ctx, year_id: uuid.UUID, group_id: uuid.UUID, body: GroupUpdateIn) -> StudentGroup:
    year = get_editable_year(ctx, year_id)
    group = _get_group(ctx, year.id, group_id)
    data = body.model_dump(exclude_unset=True)
    if "curriculum_id" in data or "course" in data:
        _validate_curriculum(ctx, data.get("curriculum_id") or group.curriculum_id, data.get("course") or group.course)
    _check_contingent(group, data)
    if {"student_count", "budget_count", "contract_count"} & data.keys() and "needs_review" not in data:
        data["needs_review"] = False  # kontingent yangilandi — tekshiruv belgisi olib tashlanadi
    crud.update(ctx, group, data, entity_type="student_group", academic_year_id=year.id)
    ctx.db.commit()
    return group


def bulk_update_counts(ctx: Ctx, year_id: uuid.UUID, items: list[GroupBulkItem]) -> list[StudentGroup]:
    """Kontingentni ommaviy yangilash — bitta tranzaksiyada (bitta xato bo‘lsa hech biri saqlanmaydi)."""
    year = get_editable_year(ctx, year_id)
    result = []
    for item in items:
        group = _get_group(ctx, year.id, item.id)
        data = item.model_dump(exclude_unset=True, exclude={"id"})
        _check_contingent(group, data)
        data["needs_review"] = False
        result.append(crud.update(ctx, group, data, entity_type="student_group", academic_year_id=year.id))
    ctx.db.commit()
    return result


def delete_group(ctx: Ctx, year_id: uuid.UUID, group_id: uuid.UUID) -> None:
    year = get_editable_year(ctx, year_id)
    crud.delete(ctx, _get_group(ctx, year.id, group_id), entity_type="student_group", academic_year_id=year.id)
    ctx.db.commit()


# ------------------------------------------------------------------ oqimlar

def _stream_out(ctx: Ctx, stream: Stream) -> StreamOut:
    rows = ctx.db.execute(select(StudentGroup.id, StudentGroup.student_count)
                          .join(StreamGroup, StreamGroup.group_id == StudentGroup.id)
                          .where(StreamGroup.stream_id == stream.id).order_by(StudentGroup.code)).all()
    return StreamOut(id=stream.id, name=stream.name, semester_id=stream.semester_id, subject_id=stream.subject_id,
                     lesson_type_id=stream.lesson_type_id, group_ids=[r[0] for r in rows],
                     student_count=sum(r[1] for r in rows), row_version=stream.row_version)


def list_streams(ctx: Ctx, year_id: uuid.UUID, subject_id: uuid.UUID | None) -> list[StreamOut]:
    get_year(ctx, year_id)
    stmt = select(Stream).where(Stream.academic_year_id == year_id).order_by(Stream.name)
    if subject_id:
        stmt = stmt.where(Stream.subject_id == subject_id)
    return [_stream_out(ctx, s) for s in ctx.db.scalars(stmt)]


def _validate_stream_groups(ctx: Ctx, year_id: uuid.UUID, semester: Semester, subject_id: uuid.UUID,
                            group_ids: list[uuid.UUID]) -> None:
    """Har bir guruh o‘quv rejasida shu fan aynan shu semestrda bo‘lishi shart."""
    if len(set(group_ids)) != len(group_ids):
        raise ValidationFailed("Guruh oqimga ikki marta qo‘shilgan", code="DUPLICATE_GROUP")
    problems = []
    for gid in group_ids:
        group = _get_group(ctx, year_id, gid)
        semester_no = curriculum_semester(group.course, semester.term)
        exists = ctx.db.scalar(select(CurriculumSubject.id).where(
            CurriculumSubject.curriculum_id == group.curriculum_id, CurriculumSubject.subject_id == subject_id,
            CurriculumSubject.semester_no == semester_no))
        if exists is None:
            problems.append(f"{group.code} ({semester_no}-semestr)")
    if problems:
        raise ValidationFailed("Bu fan quyidagi guruhlarning o‘quv rejasida shu semestrda yo‘q: " + ", ".join(problems),
                               code="SUBJECT_NOT_IN_CURRICULUM")


def _set_stream_groups(ctx: Ctx, stream: Stream, group_ids: list[uuid.UUID]) -> None:
    ctx.db.execute(delete(StreamGroup).where(StreamGroup.stream_id == stream.id))
    ctx.db.add_all([StreamGroup(university_id=ctx.university_id, academic_year_id=stream.academic_year_id,
                                stream_id=stream.id, group_id=g) for g in group_ids])


def create_stream(ctx: Ctx, year_id: uuid.UUID, body: StreamIn) -> StreamOut:
    year = get_editable_year(ctx, year_id)
    semester = ctx.db.get(Semester, body.semester_id)
    if semester is None or semester.academic_year_id != year.id:
        raise ValidationFailed("Semestr bu o‘quv yiliga tegishli emas", code="SEMESTER_NOT_IN_YEAR")
    crud.get_or_404(ctx, Subject, body.subject_id, "Fan topilmadi")
    crud.get_or_404(ctx, LessonType, body.lesson_type_id, "Mashg‘ulot turi topilmadi")
    _validate_stream_groups(ctx, year.id, semester, body.subject_id, body.group_ids)
    stream = crud.create(ctx, Stream(university_id=ctx.university_id, academic_year_id=year.id,
                                     **body.model_dump(exclude={"group_ids"})),
                         entity_type="stream", academic_year_id=year.id,
                         extra={"group_ids": [str(g) for g in body.group_ids]})
    _set_stream_groups(ctx, stream, body.group_ids)
    ctx.db.commit()
    return _stream_out(ctx, stream)


def update_stream(ctx: Ctx, year_id: uuid.UUID, stream_id: uuid.UUID, body: StreamUpdateIn) -> StreamOut:
    year = get_editable_year(ctx, year_id)
    stream = crud.get_or_404(ctx, Stream, stream_id, "Oqim topilmadi")
    if stream.academic_year_id != year.id:
        raise NotFound("Oqim topilmadi")
    data = body.model_dump(exclude_unset=True, exclude={"group_ids"})
    crud.update(ctx, stream, data, entity_type="stream", academic_year_id=year.id)
    if body.group_ids is not None:
        _validate_stream_groups(ctx, year.id, ctx.db.get(Semester, stream.semester_id), stream.subject_id,
                                body.group_ids)
        before = _stream_out(ctx, stream).group_ids
        _set_stream_groups(ctx, stream, body.group_ids)
        audit.record_ctx(ctx, action="stream.groups_changed", entity_type="stream", entity_id=stream.id,
                         academic_year_id=year.id, before={"group_ids": [str(g) for g in before]},
                         after={"group_ids": [str(g) for g in body.group_ids]})
    ctx.db.commit()
    return _stream_out(ctx, stream)


def delete_stream(ctx: Ctx, year_id: uuid.UUID, stream_id: uuid.UUID) -> None:
    year = get_editable_year(ctx, year_id)
    stream = crud.get_or_404(ctx, Stream, stream_id, "Oqim topilmadi")
    if stream.academic_year_id != year.id:
        raise NotFound("Oqim topilmadi")
    crud.delete(ctx, stream, entity_type="stream", academic_year_id=year.id)
    ctx.db.commit()
