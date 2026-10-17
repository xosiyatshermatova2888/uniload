from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=200)


def paginate(db: Session, stmt: Select, params: PageParams, schema: type[BaseModel]) -> Page:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.limit(params.size).offset((params.page - 1) * params.size)).all()
    return Page(items=[schema.model_validate(r) for r in rows], total=total,
                page=params.page, size=params.size)
