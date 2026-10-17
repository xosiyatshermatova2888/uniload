from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")

USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,63}$"


def _normalize_login(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


# Login: kichik lotin harflari, raqamlar, nuqta, chiziqcha va pastki chiziq; 3–64 belgi.
Username = Annotated[str, BeforeValidator(_normalize_login), StringConstraints(pattern=USERNAME_PATTERN)]
LoginName = Annotated[str, BeforeValidator(_normalize_login), StringConstraints(min_length=1, max_length=64)]


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
