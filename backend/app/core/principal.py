import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Grant:
    permission: str
    scope_type: str
    scope_id: uuid.UUID | None


@dataclass
class Principal:
    user_id: uuid.UUID
    university_id: uuid.UUID | None
    is_platform_admin: bool
    email: str
    full_name: str
    teacher_id: uuid.UUID | None = None
    grants: list[Grant] = field(default_factory=list)

    def has(self, code: str, *, university_wide: bool = False,
            department_id: uuid.UUID | None = None) -> bool:
        """Ruxsat tekshiruvi.

        - `university_wide=True` — butun universitet ko‘lamida kerak (masalan, yil yaratish).
        - `department_id` berilsa — shu kafedrani qamrab olishi kerak.
        - Hech biri berilmasa — ruxsat biror ko‘lamda mavjud bo‘lsa yetarli (ro‘yxatlarni
          ko‘rish uchun; natijani ko‘lam bo‘yicha filtrlash servis vazifasi).
        Fakultet → kafedra ierarxiyasi 2-bosqichda (kafedralar moduli bilan) qo‘shiladi.
        """
        for g in self.grants:
            if g.permission != code:
                continue
            if g.scope_type in ("platform", "university"):
                return True
            if university_wide:
                continue
            if department_id is None:
                return True
            if g.scope_type == "department" and g.scope_id == department_id:
                return True
        return False

    @property
    def permissions(self) -> list[str]:
        return sorted({g.permission for g in self.grants})
