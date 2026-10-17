import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas import ORMModel

Position = Literal["assistant", "senior_teacher", "docent", "professor", "department_head"]
EmploymentType = Literal["main", "internal_part_time", "external_part_time", "hourly"]
Degree = Literal["none", "phd", "dsc"]
Title = Literal["none", "docent", "professor", "senior_researcher"]


class TeacherOut(ORMModel):
    id: uuid.UUID
    last_name: str
    first_name: str
    middle_name: str | None
    full_name: str = ""
    employee_no: str
    academic_degree: str
    academic_title: str
    email: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    row_version: int


class TeacherIn(BaseModel):
    last_name: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=64)
    middle_name: str | None = Field(default=None, max_length=64)
    employee_no: str = Field(min_length=1, max_length=32)
    academic_degree: Degree = "none"
    academic_title: Title = "none"
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = True


class TeacherUpdateIn(BaseModel):
    row_version: int
    last_name: str | None = Field(default=None, min_length=1, max_length=64)
    first_name: str | None = Field(default=None, min_length=1, max_length=64)
    middle_name: str | None = Field(default=None, max_length=64)
    employee_no: str | None = Field(default=None, min_length=1, max_length=32)
    academic_degree: Degree | None = None
    academic_title: Title | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None


class EmploymentOut(ORMModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: str = ""
    department_id: uuid.UUID
    position_code: str
    employment_type: str
    rate: Decimal
    norm_hours: Decimal | None
    starts_on: date | None
    ends_on: date | None
    row_version: int


class EmploymentIn(BaseModel):
    teacher_id: uuid.UUID
    department_id: uuid.UUID
    position_code: Position
    employment_type: EmploymentType = "main"
    rate: Decimal = Field(gt=0, le=2, decimal_places=2)
    starts_on: date | None = None
    ends_on: date | None = None


class EmploymentUpdateIn(BaseModel):
    row_version: int
    department_id: uuid.UUID | None = None
    position_code: Position | None = None
    employment_type: EmploymentType | None = None
    rate: Decimal | None = Field(default=None, gt=0, le=2, decimal_places=2)
    starts_on: date | None = None
    ends_on: date | None = None


class HistoryItem(BaseModel):
    academic_year_id: uuid.UUID
    year_label: str
    year_status: str
    department_id: uuid.UUID
    position_code: str
    employment_type: str
    rate: Decimal
    norm_hours: Decimal | None


class PositionNormOut(ORMModel):
    position_code: str
    position_name: str = ""
    norm_hours_per_rate: Decimal | None
    max_overload_pct: Decimal | None
    source_document: str | None
    needs_review: bool


class PositionNormIn(BaseModel):
    position_code: Position
    norm_hours_per_rate: Decimal | None = Field(default=None, gt=0, le=2000)
    max_overload_pct: Decimal | None = Field(default=None, ge=0, le=100)
    source_document: str | None = Field(default=None, max_length=2000)


class PositionNormsIn(BaseModel):
    norms: list[PositionNormIn] = Field(max_length=20)


class CatalogOut(BaseModel):
    positions: dict[str, str]
    employment_types: dict[str, str]
