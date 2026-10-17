import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    """Faqat qo‘shiladigan jurnal: ilova roliga UPDATE/DELETE berilmagan.

    Oylik partitsiyalash hajm oshganda (4-bosqich) qo‘shiladi.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "university_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_time", "university_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    university_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("universities.id", ondelete="RESTRICT"))
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_user_id: Mapped[uuid.UUID | None]
    actor_ip: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    academic_year_id: Mapped[uuid.UUID | None]
    before: Mapped[dict[str, Any] | None]
    after: Mapped[dict[str, Any] | None]
    reason: Mapped[str | None] = mapped_column(Text)
