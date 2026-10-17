import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel

YearStatus = Literal["draft", "calculated", "distributing", "in_review", "approved", "archived"]


class SemesterOut(ORMModel):
    id: uuid.UUID
    term: int
    name: str
    starts_on: date
    ends_on: date
    weeks: int | None


class SemesterIn(BaseModel):
    term: Literal[1, 2]
    name: str = Field(min_length=2, max_length=64)
    starts_on: date
    ends_on: date
    weeks: int | None = Field(default=None, ge=1, le=30)


class SemestersReplaceIn(BaseModel):
    semesters: list[SemesterIn] = Field(min_length=2, max_length=2)


class AcademicYearOut(ORMModel):
    id: uuid.UUID
    start_year: int
    end_year: int
    label: str
    status: YearStatus
    status_label: str
    is_current: bool
    is_locked: bool
    source_year_id: uuid.UUID | None
    starts_on: date
    ends_on: date
    approved_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    row_version: int
    allowed_transitions: list[YearStatus]


class AcademicYearDetailOut(AcademicYearOut):
    semesters: list[SemesterOut]
    source_label: str | None


class CopyOptions(BaseModel):
    """1-bosqichda faqat kalendar ko‘chiriladi. Guruhlar, bandlik, me’yorlar va oqimlar
    2-bosqichda tegishli modullar bilan birga qo‘shiladi (docs/05, 5.2)."""

    semesters: bool = True


class AcademicYearCreateIn(BaseModel):
    start_year: int = Field(ge=2000, le=2100)
    mode: Literal["empty", "copy"] = "empty"
    source_year_id: uuid.UUID | None = None
    options: CopyOptions = CopyOptions()
    starts_on: date | None = None
    ends_on: date | None = None


class CopyPreviewOut(BaseModel):
    label: str
    already_exists: bool
    mode: str
    source_label: str | None
    starts_on: date
    ends_on: date
    semesters: list[SemesterIn]
    will_copy: dict[str, int]
    not_yet_available: list[str]
    warnings: list[str]


class AcademicYearUpdateIn(BaseModel):
    row_version: int
    starts_on: date | None = None
    ends_on: date | None = None


class TransitionIn(BaseModel):
    to: YearStatus
    comment: str | None = Field(default=None, max_length=2000)
    row_version: int
