import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TenantMixin
from app.db.constraints import tenant_fk, tenant_unique, year_fk

# Lavozimlar katalogi. Me’yoriy soatlar universitet hujjatidan `position_norms` ga kiritiladi.
POSITIONS = {
    "assistant": "Assistent (o‘qituvchi)",
    "senior_teacher": "Katta o‘qituvchi",
    "docent": "Dotsent",
    "professor": "Professor",
    "department_head": "Kafedra mudiri",
}
EMPLOYMENT_TYPES = {
    "main": "Asosiy shtat",
    "internal_part_time": "Ichki o‘rindosh",
    "external_part_time": "Tashqi o‘rindosh",
    "hourly": "Soatbay",
}
DEGREES = ("none", "phd", "dsc")
TITLES = ("none", "docent", "professor", "senior_researcher")


class Teacher(IdMixin, AuditMixin, TenantMixin, Base):
    """Professor-o‘qituvchi shaxsi (tenant darajasi). Yillik lavozim/stavka — `teacher_employment`."""

    __tablename__ = "teachers"
    __table_args__ = (
        tenant_unique(),
        UniqueConstraint("university_id", "employee_no"),
        Index("ix_teachers_name", "university_id", "last_name", "first_name"),
        CheckConstraint(f"academic_degree IN {DEGREES}", name="degree"),
        CheckConstraint(f"academic_title IN {TITLES}", name="title"),
    )

    last_name: Mapped[str] = mapped_column(String(64))
    first_name: Mapped[str] = mapped_column(String(64))
    middle_name: Mapped[str | None] = mapped_column(String(64))
    employee_no: Mapped[str] = mapped_column(String(32))
    academic_degree: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    academic_title: Mapped[str] = mapped_column(String(24), default="none", server_default="none")
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class PositionNorm(IdMixin, AuditMixin, TenantMixin, Base):
    """Lavozim bo‘yicha 1 stavkaga yillik me’yoriy yuklama. Qiymat kiritilmaguncha NULL —
    tizim taxminiy son qo‘ymaydi."""

    __tablename__ = "position_norms"
    __table_args__ = (
        year_fk(),
        UniqueConstraint("academic_year_id", "position_code"),
        CheckConstraint(f"position_code IN {tuple(POSITIONS)}", name="position"),
        CheckConstraint("norm_hours_per_rate IS NULL OR norm_hours_per_rate > 0", name="norm"),
        CheckConstraint("max_overload_pct IS NULL OR max_overload_pct BETWEEN 0 AND 100", name="overload"),
    )

    academic_year_id: Mapped[uuid.UUID] = mapped_column(index=True)
    position_code: Mapped[str] = mapped_column(String(32))
    norm_hours_per_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_overload_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    source_document: Mapped[str | None] = mapped_column(Text)
    needs_review: Mapped[bool] = mapped_column(default=False, server_default="false")


class TeacherEmployment(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "teacher_employment"
    __table_args__ = (
        year_fk(),
        tenant_fk("teacher_id", "teachers"),
        tenant_fk("department_id", "departments"),
        UniqueConstraint("academic_year_id", "teacher_id", "department_id", "employment_type"),
        Index("ix_teacher_employment_department", "academic_year_id", "department_id"),
        CheckConstraint(f"position_code IN {tuple(POSITIONS)}", name="position"),
        CheckConstraint(f"employment_type IN {tuple(EMPLOYMENT_TYPES)}", name="employment_type"),
        CheckConstraint("rate > 0 AND rate <= 2", name="rate"),
        CheckConstraint("ends_on IS NULL OR starts_on IS NULL OR ends_on > starts_on", name="dates"),
    )

    academic_year_id: Mapped[uuid.UUID] = mapped_column(index=True)
    teacher_id: Mapped[uuid.UUID] = mapped_column(index=True)
    department_id: Mapped[uuid.UUID]
    position_code: Mapped[str] = mapped_column(String(32))
    employment_type: Mapped[str] = mapped_column(String(24), default="main", server_default="main")
    rate: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    # Snapshot: rate × lavozim me’yori (me’yor kiritilmagan bo‘lsa NULL).
    norm_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    starts_on: Mapped[date | None]
    ends_on: Mapped[date | None]
