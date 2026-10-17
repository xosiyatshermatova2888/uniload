import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel

CODE_PATTERN = r"^[\w.\-]+$"


def code_field(default=...):
    return Field(default, min_length=1, max_length=32, pattern=CODE_PATTERN)


class FacultyOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    is_active: bool
    created_at: datetime
    row_version: int
    departments_count: int = 0


class FacultyIn(BaseModel):
    code: str = code_field()
    name: str = Field(min_length=2, max_length=255)
    is_active: bool = True


class FacultyUpdateIn(BaseModel):
    row_version: int
    code: str | None = code_field(None)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    is_active: bool | None = None


class DepartmentOut(ORMModel):
    id: uuid.UUID
    faculty_id: uuid.UUID
    code: str
    name: str
    head_user_id: uuid.UUID | None
    is_active: bool
    merged_into_id: uuid.UUID | None
    created_at: datetime
    row_version: int


class DepartmentIn(BaseModel):
    faculty_id: uuid.UUID
    code: str = code_field()
    name: str = Field(min_length=2, max_length=255)
    head_user_id: uuid.UUID | None = None
    is_active: bool = True


class DepartmentUpdateIn(BaseModel):
    row_version: int
    faculty_id: uuid.UUID | None = None
    code: str | None = code_field(None)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    head_user_id: uuid.UUID | None = None
    is_active: bool | None = None
    merged_into_id: uuid.UUID | None = None


class ProgramOut(ORMModel):
    id: uuid.UUID
    department_id: uuid.UUID
    code: str
    name: str
    degree: Literal["bachelor", "master"]
    duration_years: int
    is_active: bool
    created_at: datetime
    row_version: int


class ProgramIn(BaseModel):
    department_id: uuid.UUID
    code: str = code_field()
    name: str = Field(min_length=2, max_length=255)
    degree: Literal["bachelor", "master"] = "bachelor"
    duration_years: int = Field(4, ge=1, le=6)
    is_active: bool = True


class ProgramUpdateIn(BaseModel):
    row_version: int
    department_id: uuid.UUID | None = None
    code: str | None = code_field(None)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    degree: Literal["bachelor", "master"] | None = None
    duration_years: int | None = Field(default=None, ge=1, le=6)
    is_active: bool | None = None
