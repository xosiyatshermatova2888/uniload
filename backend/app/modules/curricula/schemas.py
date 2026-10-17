import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel

EducationForm = Literal["full_time", "part_time", "evening", "distance"]
ControlType = Literal["exam", "credit_test", "none"]
CODE = r"^[\w.\-]+$"


class LessonTypeOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    is_auditorium: bool
    counts_in_workload: bool
    is_system: bool
    sort_order: int
    row_version: int


class LessonTypeIn(BaseModel):
    code: str = Field(pattern=r"^[a-z0-9_]{2,32}$")
    name: str = Field(min_length=2, max_length=128)
    is_auditorium: bool = False
    counts_in_workload: bool = True
    sort_order: int = Field(100, ge=0, le=1000)


class LessonTypeUpdateIn(BaseModel):
    row_version: int
    name: str | None = Field(default=None, min_length=2, max_length=128)
    is_auditorium: bool | None = None
    counts_in_workload: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=1000)


class SubjectOut(ORMModel):
    id: uuid.UUID
    code: str
    name_uz: str
    name_ru: str | None
    name_en: str | None
    default_department_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    row_version: int


class SubjectIn(BaseModel):
    code: str = Field(min_length=1, max_length=32, pattern=CODE)
    name_uz: str = Field(min_length=2, max_length=255)
    name_ru: str | None = Field(default=None, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    default_department_id: uuid.UUID | None = None
    is_active: bool = True


class SubjectUpdateIn(BaseModel):
    row_version: int
    code: str | None = Field(default=None, min_length=1, max_length=32, pattern=CODE)
    name_uz: str | None = Field(default=None, min_length=2, max_length=255)
    name_ru: str | None = Field(default=None, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    default_department_id: uuid.UUID | None = None
    is_active: bool | None = None


class CurriculumOut(ORMModel):
    id: uuid.UUID
    education_program_id: uuid.UUID
    education_form: EducationForm
    admission_year: int
    version: int
    status: Literal["draft", "approved", "archived"]
    title: str | None
    approval_doc: str | None
    approved_at: datetime | None
    based_on_id: uuid.UUID | None
    created_at: datetime
    row_version: int
    subjects_count: int = 0
    total_credits: Decimal | None = None


class CurriculumSubjectOut(ORMModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    semester_no: int
    credits: Decimal | None
    department_id: uuid.UUID
    control_type: ControlType
    is_elective: bool
    elective_group: str | None
    row_version: int
    hours: dict[str, Decimal]


class CurriculumDetailOut(CurriculumOut):
    duration_years: int
    subjects: list[CurriculumSubjectOut]
    totals_by_semester: dict[int, dict[str, Decimal]]


class CurriculumIn(BaseModel):
    education_program_id: uuid.UUID
    education_form: EducationForm = "full_time"
    admission_year: int = Field(ge=2000, le=2100)
    title: str | None = Field(default=None, max_length=255)
    approval_doc: str | None = Field(default=None, max_length=2000)


class CurriculumUpdateIn(BaseModel):
    row_version: int
    title: str | None = Field(default=None, max_length=255)
    approval_doc: str | None = Field(default=None, max_length=2000)


class CurriculumApproveIn(BaseModel):
    row_version: int
    approval_doc: str = Field(min_length=3, max_length=2000,
                              description="Tasdiqlovchi hujjat: buyruq raqami va sanasi")


class VersionIn(BaseModel):
    row_version: int


Hours = dict[str, Decimal]


class CurriculumSubjectIn(BaseModel):
    subject_id: uuid.UUID
    semester_no: int = Field(ge=1, le=12)
    credits: Decimal | None = Field(default=None, ge=0, le=60)
    department_id: uuid.UUID | None = Field(default=None, description="Bo‘sh bo‘lsa — fanning asosiy kafedrasi")
    control_type: ControlType = "exam"
    is_elective: bool = False
    elective_group: str | None = Field(default=None, max_length=32)
    hours: Hours = Field(default_factory=dict, description="Mashg‘ulot turi kodi → soat")


class CurriculumSubjectUpdateIn(BaseModel):
    row_version: int
    semester_no: int | None = Field(default=None, ge=1, le=12)
    credits: Decimal | None = Field(default=None, ge=0, le=60)
    department_id: uuid.UUID | None = None
    control_type: ControlType | None = None
    is_elective: bool | None = None
    elective_group: str | None = Field(default=None, max_length=32)
    hours: Hours | None = None
