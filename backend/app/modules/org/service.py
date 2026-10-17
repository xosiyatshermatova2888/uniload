import uuid

from sqlalchemy import func, or_, select

from app.core import crud
from app.core.deps import Ctx
from app.core.errors import ValidationFailed
from app.modules.org.models import Department, EducationProgram, Faculty
from app.modules.org.schemas import (
    DepartmentIn,
    DepartmentUpdateIn,
    FacultyIn,
    FacultyOut,
    FacultyUpdateIn,
    ProgramIn,
    ProgramUpdateIn,
)
from app.modules.users.models import User


def _like(q: str) -> str:
    return f"%{q.strip().lower()}%"


# ------------------------------------------------------------------ fakultetlar

def list_faculties(ctx: Ctx, q: str | None, is_active: bool | None) -> list[FacultyOut]:
    counts = (select(Department.faculty_id, func.count().label("n")).group_by(Department.faculty_id).subquery())
    stmt = (select(Faculty, func.coalesce(counts.c.n, 0))
            .outerjoin(counts, counts.c.faculty_id == Faculty.id)
            .where(Faculty.university_id == ctx.university_id).order_by(Faculty.name))
    if q:
        stmt = stmt.where(or_(func.lower(Faculty.name).like(_like(q)), func.lower(Faculty.code).like(_like(q))))
    if is_active is not None:
        stmt = stmt.where(Faculty.is_active == is_active)
    return [FacultyOut(**FacultyOut.model_validate(f).model_dump(exclude={"departments_count"}), departments_count=n)
            for f, n in ctx.db.execute(stmt)]


def create_faculty(ctx: Ctx, body: FacultyIn) -> Faculty:
    obj = crud.create(ctx, Faculty(university_id=ctx.university_id, **body.model_dump()), entity_type="faculty")
    ctx.db.commit()
    return obj


def update_faculty(ctx: Ctx, faculty_id: uuid.UUID, body: FacultyUpdateIn) -> Faculty:
    obj = crud.get_or_404(ctx, Faculty, faculty_id, "Fakultet topilmadi")
    crud.update(ctx, obj, body.model_dump(exclude_unset=True), entity_type="faculty")
    ctx.db.commit()
    return obj


def delete_faculty(ctx: Ctx, faculty_id: uuid.UUID) -> None:
    crud.delete(ctx, crud.get_or_404(ctx, Faculty, faculty_id, "Fakultet topilmadi"), entity_type="faculty")
    ctx.db.commit()


# ------------------------------------------------------------------ kafedralar

def _validate_department_refs(ctx: Ctx, data: dict, obj: Department | None = None) -> None:
    if data.get("faculty_id"):
        crud.get_or_404(ctx, Faculty, data["faculty_id"], "Fakultet topilmadi")
    if data.get("head_user_id"):
        user = ctx.db.get(User, data["head_user_id"])
        if user is None or user.university_id != ctx.university_id:
            raise ValidationFailed("Kafedra mudiri sifatida tanlangan foydalanuvchi topilmadi", code="USER_NOT_FOUND")
    if data.get("merged_into_id"):
        if obj is not None and data["merged_into_id"] == obj.id:
            raise ValidationFailed("Kafedrani o‘ziga birlashtirib bo‘lmaydi", code="MERGE_SELF")
        crud.get_or_404(ctx, Department, data["merged_into_id"], "Birlashtiriladigan kafedra topilmadi")


def list_departments(ctx: Ctx, q: str | None, faculty_id: uuid.UUID | None, is_active: bool | None):
    stmt = select(Department).where(Department.university_id == ctx.university_id).order_by(Department.name)
    if q:
        stmt = stmt.where(or_(func.lower(Department.name).like(_like(q)), func.lower(Department.code).like(_like(q))))
    if faculty_id:
        stmt = stmt.where(Department.faculty_id == faculty_id)
    if is_active is not None:
        stmt = stmt.where(Department.is_active == is_active)
    return list(ctx.db.scalars(stmt))


def create_department(ctx: Ctx, body: DepartmentIn) -> Department:
    data = body.model_dump()
    _validate_department_refs(ctx, data)
    obj = crud.create(ctx, Department(university_id=ctx.university_id, **data), entity_type="department")
    ctx.db.commit()
    return obj


def update_department(ctx: Ctx, department_id: uuid.UUID, body: DepartmentUpdateIn) -> Department:
    obj = crud.get_or_404(ctx, Department, department_id, "Kafedra topilmadi")
    data = body.model_dump(exclude_unset=True)
    _validate_department_refs(ctx, data, obj)
    if data.get("merged_into_id"):
        data["is_active"] = False  # birlashtirilgan kafedra endi yangi taqsimotlarda ishlatilmaydi
    crud.update(ctx, obj, data, entity_type="department")
    ctx.db.commit()
    return obj


def delete_department(ctx: Ctx, department_id: uuid.UUID) -> None:
    crud.delete(ctx, crud.get_or_404(ctx, Department, department_id, "Kafedra topilmadi"), entity_type="department")
    ctx.db.commit()


# ------------------------------------------------------------------ ta’lim yo‘nalishlari

def list_programs(ctx: Ctx, q: str | None, department_id: uuid.UUID | None, degree: str | None,
                  is_active: bool | None):
    stmt = select(EducationProgram).where(EducationProgram.university_id == ctx.university_id) \
        .order_by(EducationProgram.code)
    if q:
        stmt = stmt.where(or_(func.lower(EducationProgram.name).like(_like(q)), EducationProgram.code.like(f"%{q}%")))
    if department_id:
        stmt = stmt.where(EducationProgram.department_id == department_id)
    if degree:
        stmt = stmt.where(EducationProgram.degree == degree)
    if is_active is not None:
        stmt = stmt.where(EducationProgram.is_active == is_active)
    return list(ctx.db.scalars(stmt))


def create_program(ctx: Ctx, body: ProgramIn) -> EducationProgram:
    crud.get_or_404(ctx, Department, body.department_id, "Kafedra topilmadi")
    obj = crud.create(ctx, EducationProgram(university_id=ctx.university_id, **body.model_dump()),
                      entity_type="education_program")
    ctx.db.commit()
    return obj


def update_program(ctx: Ctx, program_id: uuid.UUID, body: ProgramUpdateIn) -> EducationProgram:
    obj = crud.get_or_404(ctx, EducationProgram, program_id, "Ta’lim yo‘nalishi topilmadi")
    data = body.model_dump(exclude_unset=True)
    if data.get("department_id"):
        crud.get_or_404(ctx, Department, data["department_id"], "Kafedra topilmadi")
    crud.update(ctx, obj, data, entity_type="education_program")
    ctx.db.commit()
    return obj


def delete_program(ctx: Ctx, program_id: uuid.UUID) -> None:
    crud.delete(ctx, crud.get_or_404(ctx, EducationProgram, program_id, "Ta’lim yo‘nalishi topilmadi"),
                entity_type="education_program")
    ctx.db.commit()
