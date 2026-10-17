import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.session import TenantScope, open_session
from tests.conftest import login, university_id


def _role_id(client, headers, code):
    return next(r["id"] for r in client.get("/api/v1/roles", headers=headers).json() if r["code"] == code)


# ----------------------------------------------------------------- foydalanuvchilar va rollar

def test_admin_creates_user_with_role(client, tu_admin, unique):
    office_role = _role_id(client, tu_admin, "academic_office")
    r = client.post("/api/v1/users", headers=tu_admin, json={
        "username": f" Yangi-{unique} ", "email": f"Yangi-{unique}@demo-tu.uniload.example",
        "full_name": "Yangi Xodim",
        "initial_password": "Boshlang1ch", "roles": [{"role_id": office_role, "scope_type": "university"}]})
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["username"] == f"yangi-{unique}"  # login kichik harfga keltiriladi
    assert user["email"] == f"yangi-{unique}@demo-tu.uniload.example"
    assert [a["role_code"] for a in user["roles"]] == ["academic_office"]
    headers = login(client, user["username"], "Boshlang1ch")
    assert "academic_year.create" in client.get("/api/v1/auth/me", headers=headers).json()["permissions"]


def test_duplicate_username_conflict(client, tu_admin):
    r = client.post("/api/v1/users", headers=tu_admin, json={
        "username": "oquv.tu", "full_name": "Takror", "initial_password": "Boshlang1ch"})
    assert r.status_code == 409 and r.json()["code"] == "DUPLICATE"


def test_non_admins_cannot_manage_users(client, tu_office, tu_teacher):
    for headers in (tu_office, tu_teacher):
        assert client.get("/api/v1/users", headers=headers).status_code == 403


def test_custom_role_lifecycle(client, tu_admin, unique):
    r = client.post("/api/v1/roles", headers=tu_admin, json={
        "code": f"prorektor_{unique}", "name": "Prorektor", "permissions": ["approval.final", "academic_year.view"]})
    assert r.status_code == 201, r.text
    role = r.json()
    assert role["permissions"] == ["academic_year.view", "approval.final"] and not role["is_system"]

    r = client.patch(f"/api/v1/roles/{role['id']}", headers=tu_admin,
                     json={"row_version": role["row_version"], "permissions": ["academic_year.view"]})
    assert r.status_code == 200 and r.json()["permissions"] == ["academic_year.view"]

    bad = client.post("/api/v1/roles", headers=tu_admin, json={
        "code": f"hack_{unique}", "name": "Hack", "permissions": ["platform.tenants.manage"]})
    assert bad.status_code == 403
    unknown = client.post("/api/v1/roles", headers=tu_admin, json={
        "code": f"unk_{unique}", "name": "Unk", "permissions": ["nope.nope"]})
    assert unknown.status_code == 422

    user = client.post("/api/v1/users", headers=tu_admin, json={
        "username": f"pr-{unique}", "full_name": "Prorektor", "initial_password": "Boshlang1ch",
        "roles": [{"role_id": role["id"], "scope_type": "university"}]}).json()
    assert client.delete(f"/api/v1/roles/{role['id']}", headers=tu_admin).json()["code"] == "ROLE_IN_USE"
    client.put(f"/api/v1/users/{user['id']}/roles", headers=tu_admin, json={"roles": []})
    assert client.delete(f"/api/v1/roles/{role['id']}", headers=tu_admin).status_code == 204


def test_system_roles_are_read_only(client, tu_admin):
    role_id = _role_id(client, tu_admin, "teacher")
    role = client.get(f"/api/v1/roles/{role_id}", headers=tu_admin).json()
    r = client.patch(f"/api/v1/roles/{role_id}", headers=tu_admin,
                     json={"row_version": role["row_version"], "permissions": ["users.manage"]})
    assert r.status_code == 403 and r.json()["code"] == "SYSTEM_ROLE"
    assert client.delete(f"/api/v1/roles/{role_id}", headers=tu_admin).status_code == 403
    assert "super_admin" not in {r["code"] for r in client.get("/api/v1/roles", headers=tu_admin).json()}


def test_admin_cannot_lock_themselves_out(client, tu_admin):
    me = client.get("/api/v1/auth/me", headers=tu_admin).json()
    detail = client.get(f"/api/v1/users/{me['id']}", headers=tu_admin).json()
    r = client.put(f"/api/v1/users/{me['id']}/roles", headers=tu_admin, json={"roles": []})
    assert r.status_code == 409 and r.json()["code"] == "SELF_LOCKOUT"
    r = client.patch(f"/api/v1/users/{me['id']}", headers=tu_admin,
                     json={"row_version": detail["row_version"], "is_active": False})
    assert r.status_code == 409


def test_department_scope_requires_scope_id(client, tu_admin, unique):
    head_role = _role_id(client, tu_admin, "department_head")
    r = client.post("/api/v1/users", headers=tu_admin, json={
        "username": f"km-{unique}", "full_name": "KM", "initial_password": "Boshlang1ch",
        "roles": [{"role_id": head_role, "scope_type": "department"}]})
    assert r.status_code == 422 and r.json()["code"] == "SCOPE_INVALID"


def test_university_settings_update(client, tu_admin, tu_office):
    uni = client.get("/api/v1/university", headers=tu_admin).json()
    r = client.patch("/api/v1/university", headers=tu_admin, json={
        "row_version": uni["row_version"], "short_name": "DTU", "settings": {"overload_tolerance_pct": 10}})
    assert r.status_code == 200 and r.json()["settings"]["overload_tolerance_pct"] == 10
    r = client.patch("/api/v1/university", headers=tu_admin, json={
        "row_version": r.json()["row_version"], "settings": {"unknown_key": 1}})
    assert r.status_code == 422
    assert client.patch("/api/v1/university", headers=tu_office, json={"row_version": 1}).status_code == 403


# ----------------------------------------------------------------- platforma

def test_super_admin_creates_university(client, super_admin, unique):
    r = client.post("/api/v1/platform/universities", headers=super_admin, json={
        "code": f"new-{unique}", "name": "DEMO Yangi universitet", "plan_code": "trial",
        "first_admin": {"username": f"admin.new-{unique}", "full_name": "Admin",
                        "initial_password": "Boshlang1ch"}})
    assert r.status_code == 201, r.text
    uni = r.json()
    assert uni["subscription_status"] == "trial" and uni["users_count"] == 1
    admin = login(client, f"admin.new-{unique}", "Boshlang1ch")
    me = client.get("/api/v1/auth/me", headers=admin).json()
    assert me["university"]["code"] == f"new-{unique}" and "users.manage" in me["permissions"]
    assert client.get("/api/v1/academic-years", headers=admin).json() == []

    # Universitetni to‘xtatish — kirish bloklanadi.
    r = client.patch(f"/api/v1/platform/universities/{uni['id']}", headers=super_admin,
                     json={"row_version": uni["row_version"], "status": "suspended"})
    assert r.status_code == 200
    blocked = client.post("/api/v1/auth/login", json={"username": f"admin.new-{unique}",
                                                       "password": "Boshlang1ch"})
    assert blocked.status_code == 403 and blocked.json()["code"] == "TENANT_SUSPENDED"


def test_platform_lists(client, super_admin):
    unis = client.get("/api/v1/platform/universities", headers=super_admin).json()
    assert {"demo-tu", "demo-pu"} <= {u["code"] for u in unis}
    plans = client.get("/api/v1/platform/plans", headers=super_admin).json()
    assert {"trial", "standard"} <= {p["code"] for p in plans}
    assert client.get("/api/v1/platform/health", headers=super_admin).json() == {"database": "ok"}


# ----------------------------------------------------------------- audit

def test_audit_records_changes(client, tu_admin, tu_office, free_year):
    year = client.post("/api/v1/academic-years", headers=tu_office, json={"start_year": free_year}).json()
    logs = client.get("/api/v1/audit-logs", headers=tu_admin,
                      params={"entity_type": "academic_year", "entity_id": year["id"]}).json()
    assert logs["total"] == 1
    entry = logs["items"][0]
    assert entry["action"] == "academic_year.created" and entry["after"]["start_year"] == free_year
    assert entry["request_id"]
    assert client.get("/api/v1/audit-logs", headers=tu_admin, params={"action": "auth.login"}).json()["total"] > 0


def test_audit_log_is_append_only(owner_db):
    uni = university_id(owner_db, "demo-tu")
    with open_session(TenantScope(uni)) as db:
        with pytest.raises(DBAPIError) as e:
            db.execute(text("DELETE FROM audit_logs"))
        assert e.value.orig.sqlstate == "42501"
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE audit_logs SET action = 'x'"))
        db.rollback()


def test_problem_json_format(client, tu_office):
    r = client.get("/api/v1/academic-years/00000000-0000-0000-0000-000000000000", headers=tu_office)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert {"type", "title", "status", "code", "detail", "request_id"} <= body.keys()
    assert r.headers["x-request-id"] == body["request_id"]
