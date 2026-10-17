"""Boshqaruv buyruqlari.

    python -m app.cli bootstrap   # ruxsatlar katalogi, tizim rollari, tariflar (idempotent)
    python -m app.cli seed        # DEMO ma’lumotlar (faqat dev/test)

Ikkalasi ham jadval egasi (`UNILOAD_MIGRATION_DATABASE_URL`) bilan ishlaydi.
Demo parol `UNILOAD_SEED_PASSWORD` dan olinadi (sukut: .env.example’dagi qiymat).
"""

import os
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.permissions import PERMISSIONS, SYSTEM_ROLES
from app.core.security import hash_password
from app.demo_seed import seed_reference
from app.modules.academic_years import domain
from app.modules.academic_years.models import AcademicYear, Semester
from app.modules.curricula.service import ensure_lesson_types
from app.modules.tenants.models import Plan, Subscription, University
from app.modules.users.models import Permission, Role, RolePermission, User, UserRole

DEFAULT_PLANS = [
    ("trial", "Sinov (30 kun)", {"max_users": 20, "max_teachers": 100}, None),
    ("standard", "Standart", {"max_users": 200, "max_teachers": 1500}, None),
]

DEMO_UNIVERSITIES = [
    ("demo-tu", "DEMO Texnika universiteti", "DEMO-TU"),
    ("demo-pu", "DEMO Pedagogika universiteti", "DEMO-PU"),
]
# (rol kodi, login prefiksi, F.I.Sh.) — login: <prefiks>.<universitet qisqa kodi>
DEMO_USERS = [
    ("university_admin", "admin", "Demo Universitet Admini"),
    ("academic_office", "oquv", "Demo O‘quv bo‘limi xodimi"),
    ("department_head", "kafedra", "Demo Kafedra mudiri"),
    ("teacher", "oqituvchi", "Demo Professor-o‘qituvchi"),
]


def _owner_session() -> Session:
    return Session(create_engine(get_settings().migration_database_url))


def bootstrap(db: Session) -> None:
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, (module, desc) in PERMISSIONS.items():
        if code in existing:
            existing[code].module, existing[code].description = module, desc
        else:
            db.add(Permission(code=code, module=module, description=desc))
    db.flush()
    perm_ids = {p.code: p.id for p in db.scalars(select(Permission))}

    for role_def in SYSTEM_ROLES.values():
        role = db.scalar(select(Role).where(Role.university_id.is_(None), Role.code == role_def.code))
        if role is None:
            role = Role(university_id=None, code=role_def.code, name=role_def.name,
                        default_scope=role_def.default_scope, is_system=True)
            db.add(role)
            db.flush()
        role.name, role.default_scope, role.is_system = role_def.name, role_def.default_scope, True
        db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        db.add_all([RolePermission(role_id=role.id, permission_id=perm_ids[c]) for c in role_def.permissions])

    for uni_id in db.scalars(select(University.id)):
        ensure_lesson_types(db, uni_id)

    for code, name, limits, price in DEFAULT_PLANS:
        if db.scalar(select(Plan).where(Plan.code == code)) is None:
            db.add(Plan(code=code, name=name, limits=limits, price_monthly=price))
    db.commit()
    print(f"bootstrap: {len(PERMISSIONS)} ruxsat, {len(SYSTEM_ROLES)} tizim roli, {len(DEFAULT_PLANS)} tarif")


def seed(db: Session, password: str) -> None:
    if get_settings().env == "prod":
        raise SystemExit("Demo ma’lumotlarni production’ga yozib bo‘lmaydi")
    roles = {r.code: r for r in db.scalars(select(Role).where(Role.university_id.is_(None)))}
    if not roles:
        raise SystemExit("Avval `python -m app.cli bootstrap` ni ishga tushiring")
    pw_hash = hash_password(password)

    if db.scalar(select(User).where(User.username == "superadmin")) is None:
        sa_user = User(university_id=None, username="superadmin", full_name="Demo Super Admin",
                       password_hash=pw_hash, is_platform_admin=True)
        db.add(sa_user)
        db.flush()
        db.add(UserRole(university_id=None, user_id=sa_user.id, role_id=roles["super_admin"].id,
                        scope_type="platform"))

    trial = db.scalar(select(Plan).where(Plan.code == "standard"))
    now = datetime.now(UTC)
    start_year = 2026
    for code, name, short in DEMO_UNIVERSITIES:
        uni = db.scalar(select(University).where(University.code == code))
        if uni is None:
            uni = University(code=code, name=name, short_name=short)
            db.add(uni)
            db.flush()
            db.add(Subscription(university_id=uni.id, plan_id=trial.id, status="active", starts_at=now,
                                ends_at=now + timedelta(days=365)))
        for role_code, prefix, full_name in DEMO_USERS:
            username = f"{prefix}.{code.removeprefix('demo-')}"
            if db.scalar(select(User).where(User.username == username)) is not None:
                continue
            user = User(university_id=uni.id, username=username, full_name=full_name, password_hash=pw_hash)
            db.add(user)
            db.flush()
            # Kafedra ko‘lami 2-bosqichda haqiqiy kafedra ID’siga bog‘lanadi; hozircha "self".
            scope = "self" if role_code in ("teacher", "department_head") else "university"
            db.add(UserRole(university_id=uni.id, user_id=user.id, role_id=roles[role_code].id, scope_type=scope))
        if db.scalar(select(AcademicYear).where(AcademicYear.university_id == uni.id,
                                                AcademicYear.start_year == start_year)) is None:
            starts_on, ends_on = domain.default_year_dates(start_year)
            year = AcademicYear(university_id=uni.id, start_year=start_year, end_year=start_year + 1,
                                status="draft", is_current=True, starts_on=starts_on, ends_on=ends_on)
            db.add(year)
            db.flush()
            for s in domain.default_semesters(start_year):
                db.add(Semester(university_id=uni.id, academic_year_id=year.id, term=s.term, name=s.name,
                                starts_on=s.starts_on, ends_on=s.ends_on))
            db.flush()
        year = db.scalar(select(AcademicYear).where(AcademicYear.university_id == uni.id,
                                                    AcademicYear.start_year == start_year))
        ensure_lesson_types(db, uni.id)
        seed_reference(db, uni.id, year)
    db.commit()
    print("seed: demo ma’lumotlar tayyor (loginlar: README.md, Demo foydalanuvchilar)")


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1] not in ("bootstrap", "seed"):
        print(__doc__)
        raise SystemExit(2)
    with _owner_session() as db:
        if argv[1] == "bootstrap":
            bootstrap(db)
        else:
            seed(db, os.environ.get("UNILOAD_SEED_PASSWORD", "Demo12345!"))


if __name__ == "__main__":
    main(sys.argv)
