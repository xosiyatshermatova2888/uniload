import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.schemas import ORMModel

Language = Literal["uz", "ru", "en", "kk", "tj", "tk", "kaa"]


class GroupOut(ORMModel):
    id: uuid.UUID
    curriculum_id: uuid.UUID
    code: str
    course: int
    language: str
    student_count: int
    budget_count: int | None
    contract_count: int | None
    subgroup_count: int
    source_group_id: uuid.UUID | None
    needs_review: bool
    created_at: datetime
    row_version: int


class _Contingent(BaseModel):
    @model_validator(mode="after")
    def _sum(self):
        b, c, s = getattr(self, "budget_count", None), getattr(self, "contract_count", None), \
            getattr(self, "student_count", None)
        if b is not None and c is not None and s is not None and b + c != s:
            raise ValueError("Byudjet va kontrakt talabalar yig‘indisi umumiy soniga teng bo‘lishi kerak")
        return self


class GroupIn(_Contingent):
    curriculum_id: uuid.UUID
    code: str = Field(min_length=1, max_length=32)
    course: int = Field(ge=1, le=6)
    language: Language = "uz"
    student_count: int = Field(0, ge=0, le=500)
    budget_count: int | None = Field(default=None, ge=0)
    contract_count: int | None = Field(default=None, ge=0)
    subgroup_count: int = Field(1, ge=1, le=10)


class GroupUpdateIn(_Contingent):
    row_version: int
    curriculum_id: uuid.UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=32)
    course: int | None = Field(default=None, ge=1, le=6)
    language: Language | None = None
    student_count: int | None = Field(default=None, ge=0, le=500)
    budget_count: int | None = Field(default=None, ge=0)
    contract_count: int | None = Field(default=None, ge=0)
    subgroup_count: int | None = Field(default=None, ge=1, le=10)
    needs_review: bool | None = None


class GroupBulkItem(_Contingent):
    id: uuid.UUID
    row_version: int
    student_count: int = Field(ge=0, le=500)
    budget_count: int | None = Field(default=None, ge=0)
    contract_count: int | None = Field(default=None, ge=0)
    subgroup_count: int | None = Field(default=None, ge=1, le=10)


class GroupBulkIn(BaseModel):
    items: list[GroupBulkItem] = Field(min_length=1, max_length=500)


class StreamOut(BaseModel):
    id: uuid.UUID
    name: str
    semester_id: uuid.UUID
    subject_id: uuid.UUID
    lesson_type_id: uuid.UUID
    group_ids: list[uuid.UUID]
    student_count: int
    row_version: int


class StreamIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    semester_id: uuid.UUID
    subject_id: uuid.UUID
    lesson_type_id: uuid.UUID
    group_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class StreamUpdateIn(BaseModel):
    row_version: int
    name: str | None = Field(default=None, min_length=1, max_length=128)
    group_ids: list[uuid.UUID] | None = Field(default=None, min_length=1, max_length=50)
