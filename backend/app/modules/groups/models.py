import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TenantMixin
from app.db.constraints import same_year_fk, tenant_fk, year_fk

LANGUAGES = ("uz", "ru", "en", "kk", "tj", "tk", "kaa")


class StudentGroup(IdMixin, AuditMixin, TenantMixin, Base):
    """Akademik guruh — har bir o‘quv yili uchun alohida yozuv (yillar aralashmaydi)."""

    __tablename__ = "student_groups"
    __table_args__ = (
        year_fk(),
        tenant_fk("curriculum_id", "curricula"),
        UniqueConstraint("academic_year_id", "id"),
        Index("uq_student_groups_code", "academic_year_id", text("lower(code)"), unique=True),
        Index("ix_student_groups_curriculum_course", "academic_year_id", "curriculum_id", "course"),
        CheckConstraint("course BETWEEN 1 AND 6", name="course"),
        CheckConstraint("student_count >= 0", name="student_count"),
        CheckConstraint("budget_count IS NULL OR budget_count >= 0", name="budget_count"),
        CheckConstraint("contract_count IS NULL OR contract_count >= 0", name="contract_count"),
        CheckConstraint(
            "budget_count IS NULL OR contract_count IS NULL OR budget_count + contract_count = student_count",
            name="contingent_sum"),
        CheckConstraint("subgroup_count BETWEEN 1 AND 10", name="subgroup_count"),
        CheckConstraint(f"language IN {LANGUAGES}", name="language"),
    )

    academic_year_id: Mapped[uuid.UUID] = mapped_column(index=True)
    curriculum_id: Mapped[uuid.UUID] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(String(32))
    course: Mapped[int] = mapped_column(SmallInteger)
    language: Mapped[str] = mapped_column(String(3), default="uz", server_default="uz")
    student_count: Mapped[int] = mapped_column(default=0, server_default="0")
    budget_count: Mapped[int | None]
    contract_count: Mapped[int | None]
    subgroup_count: Mapped[int] = mapped_column(SmallInteger, default=1, server_default="1")
    source_group_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("student_groups.id", ondelete="SET NULL"))
    needs_review: Mapped[bool] = mapped_column(default=False, server_default="false")


class Stream(IdMixin, AuditMixin, TenantMixin, Base):
    """Oqim — bir fan bo‘yicha birga o‘qitiladigan guruhlar (masalan, umumiy ma’ruza)."""

    __tablename__ = "streams"
    __table_args__ = (
        year_fk(),
        same_year_fk("semester_id", "semesters"),
        tenant_fk("subject_id", "subjects"),
        tenant_fk("lesson_type_id", "lesson_types"),
        UniqueConstraint("academic_year_id", "id"),
        Index("ix_streams_subject", "academic_year_id", "subject_id"),
    )

    academic_year_id: Mapped[uuid.UUID] = mapped_column(index=True)
    semester_id: Mapped[uuid.UUID]
    subject_id: Mapped[uuid.UUID]
    lesson_type_id: Mapped[uuid.UUID]
    name: Mapped[str] = mapped_column(String(128))


class StreamGroup(TenantMixin, Base):
    """Oqim ↔ guruh. Ikkala FK ham `academic_year_id` orqali — guruh boshqa yildagi oqimga tushmaydi."""

    __tablename__ = "stream_groups"
    __table_args__ = (
        year_fk(),
        same_year_fk("stream_id", "streams"),
        same_year_fk("group_id", "student_groups"),
    )

    academic_year_id: Mapped[uuid.UUID]
    stream_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    group_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, index=True)
