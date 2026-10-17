"""DEMO ma’lumotnomalar: fakultetlar, kafedralar, yo‘nalishlar, fanlar, o‘quv rejalar, guruhlar, o‘qituvchilar.

Barcha qiymatlar namunaviy (real universitet ma’lumoti emas). O‘quv reja soatlari faqat interfeys va
testlar uchun; lavozim me’yorlari ataylab bo‘sh qoldiriladi — ular universitet hujjatidan kiritiladi.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.academic_years.models import AcademicYear, Semester
from app.modules.curricula.models import Curriculum, CurriculumSubject, CurriculumSubjectHours, LessonType, Subject
from app.modules.groups.models import Stream, StreamGroup, StudentGroup
from app.modules.org.models import Department, EducationProgram, Faculty
from app.modules.teachers.models import POSITIONS, PositionNorm, Teacher, TeacherEmployment
from app.modules.users.models import Role, User, UserRole

FACULTIES = [("AKT", "DEMO Axborot-kommunikatsiya texnologiyalari fakulteti"), ("IQT", "DEMO Iqtisodiyot fakulteti")]
DEPARTMENTS = [  # code, name, faculty
    ("DI", "Dasturiy injiniring kafedrasi", "AKT"),
    ("AT", "Axborot texnologiyalari kafedrasi", "AKT"),
    ("OM", "Oliy matematika kafedrasi", "AKT"),
    ("IQ", "Iqtisodiyot nazariyasi kafedrasi", "IQT"),
]
PROGRAMS = [  # code, name, department, years
    ("60610600", "Dasturiy injiniring", "DI", 4),
    ("60410100", "Iqtisodiyot (tarmoqlar va sohalar bo‘yicha)", "IQ", 4),
]
SUBJECTS = [  # code, name, department
    ("OM101", "Oliy matematika", "OM"), ("OM201", "Ehtimollar nazariyasi va matematik statistika", "OM"),
    ("DI101", "Dasturlash asoslari", "DI"), ("DI201", "Ma’lumotlar tuzilmasi va algoritmlar", "DI"),
    ("DI301", "Veb-dasturlash", "DI"), ("DI490", "Malakaviy amaliyot", "DI"),
    ("AT201", "Ma’lumotlar bazasi", "AT"), ("AT301", "Kompyuter tarmoqlari", "AT"),
    ("AT401", "Axborot xavfsizligi", "AT"), ("IQ101", "Iqtisodiyot nazariyasi", "IQ"),
]
# Dasturiy injiniring: semestr → [(fan, kredit, {tur: soat})]  — DEMO qiymatlar
SE_PLAN = {
    1: [("OM101", 6, {"lecture": 30, "practice": 60}), ("DI101", 6, {"lecture": 30, "lab": 60})],
    2: [("OM201", 5, {"lecture": 30, "practice": 30}), ("IQ101", 4, {"lecture": 30, "seminar": 30})],
    3: [("DI201", 6, {"lecture": 30, "lab": 60})],
    4: [("AT201", 6, {"lecture": 30, "lab": 60, "course_work": 0})],
    5: [("AT301", 5, {"lecture": 30, "lab": 30})],
    6: [("DI301", 6, {"lecture": 30, "lab": 60})],
    7: [("AT401", 5, {"lecture": 30, "practice": 30})],
    8: [("DI490", 12, {"internship": 0})],
}
ECON_PLAN = {1: [("IQ101", 6, {"lecture": 30, "seminar": 60}), ("OM101", 6, {"lecture": 30, "practice": 60})]}
# guruh kodi, yo‘nalish, qabul yili, talabalar
GROUPS = [("DI-23", "60610600", 2023, 24), ("DI-24", "60610600", 2024, 27), ("DI-25a", "60610600", 2025, 25),
          ("DI-25b", "60610600", 2025, 23), ("DI-26a", "60610600", 2026, 26), ("DI-26b", "60610600", 2026, 25),
          ("IQ-26", "60410100", 2026, 30)]
TEACHERS = [  # familiya, ism, kafedra, lavozim, stavka, daraja, unvon
    ("Karimov", "Akmal", "DI", "department_head", "1.00", "phd", "docent"),
    ("Rahimova", "Dilnoza", "DI", "docent", "1.00", "phd", "docent"),
    ("Toshpo‘latov", "Jasur", "DI", "senior_teacher", "1.00", "none", "none"),
    ("Yusupova", "Malika", "DI", "assistant", "0.50", "none", "none"),
    ("Saidov", "Bekzod", "AT", "docent", "1.00", "phd", "docent"),
    ("Nazarova", "Gulnora", "AT", "senior_teacher", "1.25", "none", "none"),
    ("Ergashev", "Sardor", "OM", "professor", "1.00", "dsc", "professor"),
    ("Qodirova", "Nigora", "IQ", "docent", "1.00", "phd", "docent"),
]


def seed_reference(db: Session, university_id: uuid.UUID, year: AcademicYear) -> bool:
    """Idempotent: universitetda fakultet bo‘lsa, hech narsa qilmaydi."""
    if db.scalar(select(Faculty.id).where(Faculty.university_id == university_id).limit(1)):
        return False
    u = university_id
    lt = {t.code: t.id for t in db.scalars(select(LessonType).where(LessonType.university_id == u))}

    fac = {}
    for code, name in FACULTIES:
        fac[code] = Faculty(university_id=u, code=code, name=name)
        db.add(fac[code])
    db.flush()
    dep = {}
    for code, name, f in DEPARTMENTS:
        dep[code] = Department(university_id=u, code=code, name=name, faculty_id=fac[f].id)
        db.add(dep[code])
    db.flush()
    prog = {}
    for code, name, d, years in PROGRAMS:
        prog[code] = EducationProgram(university_id=u, code=code, name=name, department_id=dep[d].id,
                                      degree="bachelor", duration_years=years)
        db.add(prog[code])
    subj = {}
    for code, name, d in SUBJECTS:
        subj[code] = Subject(university_id=u, code=code, name_uz=name, default_department_id=dep[d].id)
        db.add(subj[code])
    db.flush()

    def curriculum(program_code: str, admission_year: int, plan: dict) -> Curriculum:
        c = Curriculum(university_id=u, education_program_id=prog[program_code].id, education_form="full_time",
                       admission_year=admission_year, version=1, status="draft",
                       title=f"DEMO o‘quv reja ({admission_year}-yil qabuli)")
        db.add(c)
        db.flush()
        for semester_no, items in plan.items():
            for code, credits, hours in items:
                cs = CurriculumSubject(university_id=u, curriculum_id=c.id, subject_id=subj[code].id,
                                       semester_no=semester_no, credits=Decimal(credits),
                                       department_id=subj[code].default_department_id,
                                       control_type="credit_test" if code == "DI490" else "exam")
                db.add(cs)
                db.flush()
                db.add_all([CurriculumSubjectHours(university_id=u, curriculum_subject_id=cs.id,
                                                   lesson_type_id=lt[t], hours=Decimal(h))
                            for t, h in hours.items() if h > 0])
        db.flush()
        c.status, c.approval_doc, c.approved_at = "approved", "DEMO: namunaviy buyruq", datetime.now(UTC)
        return c

    curricula = {("60610600", y): curriculum("60610600", y, SE_PLAN) for y in (2023, 2024, 2025, 2026)}
    curricula[("60410100", 2026)] = curriculum("60410100", 2026, ECON_PLAN)
    db.flush()

    groups = {}
    for code, program_code, admission, students in GROUPS:
        course = year.start_year - admission + 1
        groups[code] = StudentGroup(university_id=u, academic_year_id=year.id,
                                    curriculum_id=curricula[(program_code, admission)].id, code=code, course=course,
                                    student_count=students, subgroup_count=2 if students > 24 else 1)
        db.add(groups[code])
    db.flush()

    autumn = db.scalar(select(Semester).where(Semester.academic_year_id == year.id, Semester.term == 1))
    stream = Stream(university_id=u, academic_year_id=year.id, semester_id=autumn.id, subject_id=subj["DI101"].id,
                    lesson_type_id=lt["lecture"], name="DI-26 oqimi: Dasturlash asoslari (ma’ruza)")
    db.add(stream)
    db.flush()
    db.add_all([StreamGroup(university_id=u, academic_year_id=year.id, stream_id=stream.id, group_id=groups[g].id)
                for g in ("DI-26a", "DI-26b")])

    for code in POSITIONS:
        db.add(PositionNorm(university_id=u, academic_year_id=year.id, position_code=code, needs_review=True,
                            source_document="Kiritilmagan — universitet me’yoriy hujjati asosida to‘ldiriladi"))
    teachers = []
    for i, (last, first, d, position, rate, degree, title) in enumerate(TEACHERS, start=1):
        t = Teacher(university_id=u, last_name=last, first_name=first, employee_no=f"DEMO-{i:03d}",
                    academic_degree=degree, academic_title=title)
        db.add(t)
        db.flush()
        teachers.append(t)
        db.add(TeacherEmployment(university_id=u, academic_year_id=year.id, teacher_id=t.id,
                                 department_id=dep[d].id, position_code=position, rate=Decimal(rate)))
    db.flush()

    # Demo kafedra mudiri — DI kafedrasi ko‘lamida; demo PO — birinchi o‘qituvchi profiliga bog‘lanadi.
    head_role = db.scalar(select(Role).where(Role.university_id.is_(None), Role.code == "department_head"))
    for user in db.scalars(select(User).where(User.university_id == u)):
        prefix = user.email.split("@")[0]
        if prefix == "kafedra":
            for ur in db.scalars(select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == head_role.id)):
                ur.scope_type, ur.scope_id = "department", dep["DI"].id
            dep["DI"].head_user_id = user.id
        if prefix == "oqituvchi":
            user.teacher_id = teachers[2].id
    db.flush()
    return True
