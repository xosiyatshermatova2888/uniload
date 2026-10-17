import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditMixin, Base, IdMixin, TenantMixin
from app.modules.academic_years.domain import YEAR_STATUSES


class AcademicYear(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "academic_years"
    __table_args__ = (
        CheckConstraint("end_year = start_year + 1", name="consecutive"),
        CheckConstraint("start_year BETWEEN 2000 AND 2100", name="start_year_range"),
        CheckConstraint("ends_on > starts_on", name="dates"),
        CheckConstraint(f"status IN {YEAR_STATUSES}", name="status"),
        UniqueConstraint("university_id", "start_year"),
        # Kompozit FK’lar uchun: farzand yozuv aynan shu tenant yiliga bog‘lanadi.
        UniqueConstraint("university_id", "id"),
        Index("uq_academic_years_one_current", "university_id", unique=True,
              postgresql_where=text("is_current")),
    )

    start_year: Mapped[int] = mapped_column(SmallInteger)
    end_year: Mapped[int] = mapped_column(SmallInteger)
    label: Mapped[str] = mapped_column(
        String(9), Computed("(start_year::text || '–' || end_year::text)", persisted=True))
    status: Mapped[str] = mapped_column(String(16), default="draft", server_default="draft")
    is_current: Mapped[bool] = mapped_column(default=False, server_default="false")
    source_year_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"))
    starts_on: Mapped[date]
    ends_on: Mapped[date]
    approved_at: Mapped[datetime | None]
    approved_by: Mapped[uuid.UUID | None]
    archived_at: Mapped[datetime | None]


class Semester(IdMixin, AuditMixin, TenantMixin, Base):
    __tablename__ = "semesters"
    __table_args__ = (
        ForeignKeyConstraint(["university_id", "academic_year_id"],
                             ["academic_years.university_id", "academic_years.id"], ondelete="CASCADE"),
        UniqueConstraint("academic_year_id", "term"),
        CheckConstraint("term IN (1, 2)", name="term"),
        CheckConstraint("ends_on > starts_on", name="dates"),
        CheckConstraint("weeks IS NULL OR weeks BETWEEN 1 AND 30", name="weeks"),
    )

    academic_year_id: Mapped[uuid.UUID] = mapped_column(index=True)
    term: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(64))
    starts_on: Mapped[date]
    ends_on: Mapped[date]
    weeks: Mapped[int | None] = mapped_column(SmallInteger)
