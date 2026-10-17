"""Tenant izolyatsiyasi: API darajasida va to‘g‘ridan-to‘g‘ri DB (RLS) darajasida."""

import uuid
from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import TenantScope, open_session
from app.modules.academic_years.models import AcademicYear
from app.modules.audit.models import AuditLog
from app.modules.users.models import Role, User
from tests.conftest import university_id

YEARS = "/api/v1/academic-years"


@pytest.fixture(scope="module")
def pu_year(client, pu_office):
    return next(y for y in client.get(YEARS, headers=pu_office).json() if y["start_year"] == 2026)


def test_list_shows_only_own_years(client, tu_office, pu_year):
    ids = {y["id"] for y in client.get(YEARS, headers=tu_office).json()}
    assert pu_year["id"] not in ids


@pytest.mark.parametrize("method,path,body", [
    ("get", "/api/v1/academic-years/{id}", None),
    ("patch", "/api/v1/academic-years/{id}", {"row_version": 1}),
    ("post", "/api/v1/academic-years/{id}/transitions", {"to": "calculated", "row_version": 1}),
    ("post", "/api/v1/academic-years/{id}/set-current", None),
    ("get", "/api/v1/years/{id}/semesters", None),
    ("put", "/api/v1/years/{id}/semesters", {"semesters": [
        {"term": 1, "name": "Kuzgi", "starts_on": "2026-09-01", "ends_on": "2027-01-31"},
        {"term": 2, "name": "Bahorgi", "starts_on": "2027-02-01", "ends_on": "2027-06-30"}]}),
    ("get", "/api/v1/years/{id}/dashboard", None),
])
def test_other_tenant_year_is_not_found(client, tu_office, pu_year, method, path, body):
    r = getattr(client, method)(path.format(id=pu_year["id"]), headers=tu_office,
                                **({"json": body} if body is not None else {}))
    assert r.status_code == 404, r.text


def test_copy_from_other_tenant_year_not_found(client, tu_office, pu_year):
    r = client.post(YEARS, headers=tu_office, json={"start_year": 2099, "mode": "copy",
                                                    "source_year_id": pu_year["id"]})
    assert r.status_code == 404


def test_users_and_roles_are_isolated(client, tu_admin, pu_admin, owner_db, unique):
    pu_users = client.get("/api/v1/users?size=200", headers=pu_admin).json()["items"]
    tu_users = client.get("/api/v1/users?size=200", headers=tu_admin).json()["items"]
    assert {u["username"].rsplit(".", 1)[1] for u in tu_users if "." in u["username"]} == {"tu"}
    assert client.get(f"/api/v1/users/{pu_users[0]['id']}", headers=tu_admin).status_code == 404

    role = client.post("/api/v1/roles", headers=pu_admin, json={
        "code": f"dekanat_{unique}", "name": "Dekanat", "permissions": ["academic_year.view"]}).json()
    assert role["id"] not in {r["id"] for r in client.get("/api/v1/roles", headers=tu_admin).json()}
    assert client.get(f"/api/v1/roles/{role['id']}", headers=tu_admin).status_code == 404
    # Boshqa tenant rolini o‘z foydalanuvchisiga berib bo‘lmaydi.
    me = next(u for u in tu_users if u["username"] == "oqituvchi.tu")
    r = client.put(f"/api/v1/users/{me['id']}/roles", headers=tu_admin,
                   json={"roles": [{"role_id": role["id"], "scope_type": "university"}]})
    assert r.status_code == 422 and r.json()["code"] == "ROLE_NOT_FOUND"


def test_university_endpoint_returns_own(client, tu_admin, pu_admin):
    assert client.get("/api/v1/university", headers=tu_admin).json()["code"] == "demo-tu"
    assert client.get("/api/v1/university", headers=pu_admin).json()["code"] == "demo-pu"


def test_rls_hides_rows_without_where_clause(owner_db):
    tu, pu = university_id(owner_db, "demo-tu"), university_id(owner_db, "demo-pu")
    with open_session(TenantScope(tu)) as db:
        unis = {y.university_id for y in db.scalars(select(AcademicYear))}
        assert unis == {tu}
        assert {u.university_id for u in db.scalars(select(User))} == {tu}
        assert all(r.university_id in (None, tu) for r in db.scalars(select(Role)))
        assert all(a.university_id == tu for a in db.scalars(select(AuditLog)))
        visible = db.execute(text("SELECT count(*) FROM universities")).scalar()
        assert visible == 1
    with open_session(TenantScope(None)) as db:  # kontekst o‘rnatilmagan — hech narsa ko‘rinmaydi
        assert db.execute(text("SELECT count(*) FROM academic_years")).scalar() == 0
        assert db.execute(text("SELECT count(*) FROM users")).scalar() == 0
    assert pu is not None


def test_rls_blocks_writing_into_other_tenant(owner_db):
    tu, pu = university_id(owner_db, "demo-tu"), university_id(owner_db, "demo-pu")
    with open_session(TenantScope(tu)) as db:
        db.add(AcademicYear(id=uuid.uuid4(), university_id=pu, start_year=2098, end_year=2099,
                            starts_on=date(2098, 9, 1), ends_on=date(2099, 8, 31)))
        with pytest.raises(DBAPIError) as e:
            db.flush()
        assert e.value.orig.sqlstate == "42501"
        db.rollback()


def test_composite_fk_prevents_cross_tenant_semester(owner_db):
    """RLS’dan tashqari: DB darajasida ham semestr boshqa tenant yiliga bog‘lanmaydi."""
    tu, pu = university_id(owner_db, "demo-tu"), university_id(owner_db, "demo-pu")
    pu_year_id = owner_db.execute(text(
        "INSERT INTO academic_years (id, university_id, start_year, end_year, starts_on, ends_on) "
        "VALUES (gen_random_uuid(), :pu, 2097, 2098, '2097-09-01', '2098-08-31') RETURNING id"), {"pu": pu}).scalar()
    try:
        with pytest.raises(DBAPIError) as e:
            owner_db.execute(text(
                "INSERT INTO semesters (id, university_id, academic_year_id, term, name, starts_on, ends_on) "
                "VALUES (gen_random_uuid(), :tu, :y, 1, 'x', '2097-09-01', '2098-01-01')"),
                {"tu": tu, "y": pu_year_id})
        assert e.value.orig.sqlstate == "23503"
    finally:
        owner_db.rollback()


def test_tenant_users_cannot_use_platform_api(client, tu_admin, super_admin):
    assert client.get("/api/v1/platform/universities", headers=tu_admin).status_code == 403
    # Super Admin universitet ma’lumotlariga sukut bo‘yicha kira olmaydi.
    r = client.get(YEARS, headers=super_admin)
    assert r.status_code == 403 and r.json()["code"] == "TENANT_REQUIRED"
