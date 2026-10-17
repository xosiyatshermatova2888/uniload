"""Alembic va bootstrap uchun barcha modellarni bir joyda import qiladi."""

from app.db.base import Base
from app.modules.academic_years.models import AcademicYear, Semester
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Plan, Subscription, University
from app.modules.users.models import (
    PasswordResetToken,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserRole,
)

__all__ = [
    "Base", "AcademicYear", "Semester", "AuditLog", "Plan", "Subscription", "University",
    "PasswordResetToken", "Permission", "RefreshToken", "Role", "RolePermission", "User", "UserRole",
]
