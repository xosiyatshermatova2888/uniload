import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.db.ids import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB,
        uuid.UUID: PG_UUID(as_uuid=True),
    }


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)


class AuditMixin:
    """Standart audit maydonlari va optimistik qulf (docs/03-er-model.md, 3.1).

    `created_by`/`updated_by` FK emas: foydalanuvchilar hech qachon o‘chirilmaydi, FK esa
    universities ↔ users o‘rtasida aylanma bog‘liqlik hosil qiladi.
    """

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    created_by: Mapped[uuid.UUID | None]
    updated_by: Mapped[uuid.UUID | None]
    row_version: Mapped[int] = mapped_column(default=1, server_default="1")

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:
        return {"version_id_col": cls.row_version}


class TenantMixin:
    @declared_attr
    def university_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"), index=True)
