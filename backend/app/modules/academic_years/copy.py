"""O‘quv yilini oldingi yildan nusxalash (docs/05-oquv-yili-algoritmi.md, 5.2–5.3).

Manba yil faqat o‘qiladi. Har bir ko‘chirilgan yozuv yangi `id` va yangi `academic_year_id` oladi —
yillar o‘rtasida qatorlar bo‘lishilmaydi. Taqsimot va hisoblangan yuklama hech qachon ko‘chirilmaydi.
Oqimlar ham ko‘chirilmaydi: kursi ko‘tarilgan guruhlar keyingi yilda boshqa fanlarni o‘qiydi, shuning
uchun oqimlar har yili o‘quv reja bo‘yicha qayta tuziladi.
"""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.academic_years.models import AcademicYear
from app.modules.curricula.models import Curriculum
from app.modules.groups.models import StudentGroup
from app.modules.org.models import EducationProgram
from app.modules.teachers.models import PositionNorm, Teacher, TeacherEmployment


@dataclass
class CopyReport:
    norms: int = 0
    employment: int = 0
    employment_skipped_inactive: int = 0
    groups: int = 0
    graduates_skipped: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"norms": self.norms, "employment": self.employment,
                "employment_skipped_inactive": self.employment_skipped_inactive, "groups": self.groups,
                "graduates_skipped": self.graduates_skipped}


def _durations(db: Session, curriculum_ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not curriculum_ids:
        return {}
    rows = db.execute(select(Curriculum.id, EducationProgram.duration_years)
                      .join(EducationProgram, EducationProgram.id == Curriculum.education_program_id)
                      .where(Curriculum.id.in_(curriculum_ids)))
    return dict(rows.all())


def run(db: Session, *, university_id: uuid.UUID, source: AcademicYear, target: AcademicYear | None,
        norms: bool, employment: bool, groups: bool) -> CopyReport:
    """`target=None` — faqat hisoblash (oldindan ko‘rish), hech narsa yozilmaydi."""
    report = CopyReport()
    write = target is not None

    norm_map: dict[str, PositionNorm] = {}
    if norms:
        for n in db.scalars(select(PositionNorm).where(PositionNorm.academic_year_id == source.id)):
            report.norms += 1
            if write:
                copy = PositionNorm(university_id=university_id, academic_year_id=target.id,
                                    position_code=n.position_code, norm_hours_per_rate=n.norm_hours_per_rate,
                                    max_overload_pct=n.max_overload_pct, source_document=n.source_document,
                                    needs_review=True)
                db.add(copy)
                norm_map[n.position_code] = copy

    if employment:
        rows = db.execute(select(TeacherEmployment, Teacher.is_active)
                          .join(Teacher, Teacher.id == TeacherEmployment.teacher_id)
                          .where(TeacherEmployment.academic_year_id == source.id)).all()
        for e, active in rows:
            if not active:
                report.employment_skipped_inactive += 1
                continue
            report.employment += 1
            if write:
                norm = norm_map.get(e.position_code)
                norm_hours = None
                if norm is not None and norm.norm_hours_per_rate is not None:
                    norm_hours = (e.rate * norm.norm_hours_per_rate).quantize(Decimal("0.01"))
                db.add(TeacherEmployment(university_id=university_id, academic_year_id=target.id,
                                         teacher_id=e.teacher_id, department_id=e.department_id,
                                         position_code=e.position_code, employment_type=e.employment_type,
                                         rate=e.rate, norm_hours=norm_hours))

    group_map: dict[uuid.UUID, uuid.UUID] = {}
    if groups:
        source_groups = list(db.scalars(select(StudentGroup).where(StudentGroup.academic_year_id == source.id)
                                        .order_by(StudentGroup.code)))
        durations = _durations(db, {g.curriculum_id for g in source_groups})
        for g in source_groups:
            if g.course >= durations.get(g.curriculum_id, 0):
                report.graduates_skipped.append(g.code)  # bitiruvchi guruh yangi yilga o‘tmaydi
                continue
            report.groups += 1
            if write:
                new = StudentGroup(university_id=university_id, academic_year_id=target.id,
                                   curriculum_id=g.curriculum_id, code=g.code, course=g.course + 1,
                                   language=g.language, student_count=g.student_count, budget_count=g.budget_count,
                                   contract_count=g.contract_count, subgroup_count=g.subgroup_count,
                                   source_group_id=g.id, needs_review=True)
                db.add(new)
                db.flush()
                group_map[g.id] = new.id

    if write:
        db.flush()
    return report
