import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TenantMixin
from app.db.constraints import tenant_fk, tenant_unique

DEGREES = ("bachelor", "master")


class Faculty(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "faculties"
    __table_args__ = (
        tenant_unique(),
        Index("uq_faculties_code", "university_id", text("lower(code)"), unique=True),
    )

    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class Department(IdMixin, AuditMixin, TenantMixin, Base):
    """Kafedra. Yopilsa yoki birlashsa o‘chirilmaydi: `is_active=false`, `merged_into_id`."""

    __tablename__ = "departments"
    __table_args__ = (
        tenant_unique(),
        tenant_fk("faculty_id", "faculties"),
        Index("uq_departments_code", "university_id", text("lower(code)"), unique=True),
        CheckConstraint("merged_into_id IS NULL OR merged_into_id <> id", name="not_self_merged"),
    )

    faculty_id: Mapped[uuid.UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    head_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"))


class EducationProgram(IdMixin, AuditMixin, TenantMixin, Base):
    """Ta’lim yo‘nalishi / mutaxassislik (masalan, 60610100)."""

    __tablename__ = "education_programs"
    __table_args__ = (
        tenant_unique(),
        tenant_fk("department_id", "departments"),
        Index("uq_education_programs_code", "university_id", "code", "degree", unique=True),
        CheckConstraint(f"degree IN {DEGREES}", name="degree"),
        CheckConstraint("duration_years BETWEEN 1 AND 6", name="duration"),
    )

    department_id: Mapped[uuid.UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    degree: Mapped[str] = mapped_column(String(16))
    duration_years: Mapped[int] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
