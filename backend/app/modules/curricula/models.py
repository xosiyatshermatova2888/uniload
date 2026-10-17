import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, Numeric, SmallInteger, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TenantMixin
from app.db.constraints import tenant_fk, tenant_unique

EDUCATION_FORMS = ("full_time", "part_time", "evening", "distance")
CURRICULUM_STATUSES = ("draft", "approved", "archived")
CONTROL_TYPES = ("exam", "credit_test", "none")

# Tizim mashg‘ulot turlari (docs/03, lesson_types). Universitet o‘z turlarini qo‘sha oladi.
SYSTEM_LESSON_TYPES = [
    # code, name, is_auditorium, counts_in_workload
    ("lecture", "Ma’ruza", True, True),
    ("practice", "Amaliy mashg‘ulot", True, True),
    ("lab", "Laboratoriya mashg‘uloti", True, True),
    ("seminar", "Seminar", True, True),
    ("independent", "Mustaqil ta’lim", False, False),
    ("course_work", "Kurs ishi", False, True),
    ("course_project", "Kurs loyihasi", False, True),
    ("internship", "Malakaviy amaliyot", False, True),
    ("final_control", "Yakuniy nazorat", False, True),
    ("graduation_work", "Bitiruv malakaviy ishi", False, True),
    ("other", "Boshqa me’yoriy yuklama", False, True),
]


class LessonType(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "lesson_types"
    __table_args__ = (
        tenant_unique(),
        UniqueConstraint("university_id", "code"),
        CheckConstraint("code ~ '^[a-z0-9_]{2,32}$'", name="code_format"),
    )

    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(128))
    is_auditorium: Mapped[bool] = mapped_column(default=False, server_default="false")
    counts_in_workload: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_system: Mapped[bool] = mapped_column(default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=100, server_default="100")


class Subject(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "subjects"
    __table_args__ = (
        tenant_unique(),
        tenant_fk("default_department_id", "departments"),
        Index("uq_subjects_code", "university_id", text("lower(code)"), unique=True),
    )

    code: Mapped[str] = mapped_column(String(32))
    name_uz: Mapped[str] = mapped_column(String(255))
    name_ru: Mapped[str | None] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255))
    default_department_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class Curriculum(IdMixin, AuditMixin, TenantMixin, Base):
    """O‘quv reja versiyasi. Tasdiqlangan versiya o‘zgarmaydi — o‘zgarish yangi versiya bilan."""

    __tablename__ = "curricula"
    __table_args__ = (
        tenant_unique(),
        tenant_fk("education_program_id", "education_programs"),
        UniqueConstraint("university_id", "education_program_id", "education_form", "admission_year", "version"),
        CheckConstraint(f"education_form IN {EDUCATION_FORMS}", name="education_form"),
        CheckConstraint(f"status IN {CURRICULUM_STATUSES}", name="status"),
        CheckConstraint("admission_year BETWEEN 2000 AND 2100", name="admission_year"),
        CheckConstraint("version >= 1", name="version"),
    )

    education_program_id: Mapped[uuid.UUID] = mapped_column(index=True)
    education_form: Mapped[str] = mapped_column(String(16))
    admission_year: Mapped[int] = mapped_column(SmallInteger)
    version: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    title: Mapped[str | None] = mapped_column(String(255))
    approval_doc: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None]
    approved_by: Mapped[uuid.UUID | None]
    based_on_id: Mapped[uuid.UUID | None]


class CurriculumSubject(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "curriculum_subjects"
    __table_args__ = (
        tenant_unique(),
        tenant_fk("curriculum_id", "curricula", ondelete="CASCADE"),
        tenant_fk("subject_id", "subjects"),
        tenant_fk("department_id", "departments"),
        UniqueConstraint("curriculum_id", "subject_id", "semester_no"),
        CheckConstraint("semester_no BETWEEN 1 AND 12", name="semester_no"),
        CheckConstraint("credits IS NULL OR credits >= 0", name="credits"),
        CheckConstraint(f"control_type IN {CONTROL_TYPES}", name="control_type"),
    )

    curriculum_id: Mapped[uuid.UUID] = mapped_column(index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(index=True)
    semester_no: Mapped[int] = mapped_column(SmallInteger)
    credits: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    department_id: Mapped[uuid.UUID] = mapped_column(index=True)
    control_type: Mapped[str] = mapped_column(String(16), default="exam", server_default="exam")
    is_elective: Mapped[bool] = mapped_column(default=False, server_default="false")
    elective_group: Mapped[str | None] = mapped_column(String(32))


class CurriculumSubjectHours(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "curriculum_subject_hours"
    __table_args__ = (
        tenant_fk("curriculum_subject_id", "curriculum_subjects", ondelete="CASCADE"),
        tenant_fk("lesson_type_id", "lesson_types"),
        UniqueConstraint("curriculum_subject_id", "lesson_type_id"),
        CheckConstraint("hours >= 0", name="hours"),
    )

    curriculum_subject_id: Mapped[uuid.UUID] = mapped_column(index=True)
    lesson_type_id: Mapped[uuid.UUID]
    hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
