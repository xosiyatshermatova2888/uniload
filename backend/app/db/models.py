"""Alembic va bootstrap uchun barcha modellarni bir joyda import qiladi."""

from app.db.base import Base
from app.modules.academic_years.models import AcademicYear, Semester
from app.modules.audit.models import AuditLog
from app.modules.curricula.models import Curriculum, CurriculumSubject, CurriculumSubjectHours, LessonType, Subject
from app.modules.groups.models import Stream, StreamGroup, StudentGroup
from app.modules.org.models import Department, EducationProgram, Faculty
from app.modules.teachers.models import PositionNorm, Teacher, TeacherEmployment
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
    "Curriculum", "CurriculumSubject", "CurriculumSubjectHours", "LessonType", "Subject", "Stream", "StreamGroup",
    "StudentGroup", "Department", "EducationProgram", "Faculty", "PositionNorm", "Teacher", "TeacherEmployment",
]
