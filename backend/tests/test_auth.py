from tests.conftest import PASSWORD, email_for, login

LOGIN = "/api/v1/auth/login"


def _create_user(client, admin_headers, email, password="Boshlang1ch"):
    r = client.post("/api/v1/users", headers=admin_headers, json={
        "email": email, "full_name": "Test Foydalanuvchi", "initial_password": password, "roles": []})
    assert r.status_code == 201, r.text
    return r.json()


def test_login_returns_profile_and_sets_refresh_cookie(client):
    r = client.post(LOGIN, json={"email": email_for("oquv").upper(), "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["university"]["code"] == "demo-tu"
    assert "academic_year.create" in body["user"]["permissions"]
    assert "academic_office" in body["user"]["roles"]
    cookie = r.headers["set-cookie"]
    assert "uniload_refresh=" in cookie and "HttpOnly" in cookie and "samesite=strict" in cookie.lower()


def test_wrong_password_and_unknown_email_give_same_error(client):
    a = client.post(LOGIN, json={"email": email_for("oquv"), "password": "notogri123"})
    b = client.post(LOGIN, json={"email": "yoq@demo-tu.uniload.example", "password": "notogri123"})
    assert a.status_code == b.status_code == 401
    assert a.json()["code"] == b.json()["code"] == "INVALID_CREDENTIALS"
    assert a.json()["detail"] == b.json()["detail"]


def test_lockout_after_repeated_failures(client, tu_admin, unique):
    email = f"lock-{unique}@demo-tu.uniload.example"
    _create_user(client, tu_admin, email)
    for _ in range(5):
        assert client.post(LOGIN, json={"email": email, "password": "xato12345"}).status_code == 401
    r = client.post(LOGIN, json={"email": email, "password": "Boshlang1ch"})
    assert r.status_code == 429 and r.json()["code"] == "ACCOUNT_LOCKED"


def test_me_requires_token(client, tu_teacher):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).json()["code"] == "TOKEN_INVALID"
    me = client.get("/api/v1/auth/me", headers=tu_teacher).json()
    assert me["roles"] == ["teacher"]
    assert "users.manage" not in me["permissions"]


def test_refresh_rotation_and_reuse_detection(client):
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    first = c.post(LOGIN, json={"email": email_for("kafedra"), "password": PASSWORD})
    old_refresh = first.cookies.get("uniload_refresh")
    r = c.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    new_refresh = r.cookies.get("uniload_refresh")
    assert new_refresh and new_refresh != old_refresh

    # Eski tokenni qayta ishlatish — butun zanjir bekor qilinadi.
    c2 = TestClient(app)
    c2.cookies.set("uniload_refresh", old_refresh, path="/api/v1/auth")
    reused = c2.post("/api/v1/auth/refresh")
    assert reused.status_code == 401 and reused.json()["code"] == "SESSION_REVOKED"
    c.cookies.set("uniload_refresh", new_refresh, path="/api/v1/auth")
    assert c.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_refresh(client):
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    c.post(LOGIN, json={"email": email_for("oqituvchi"), "password": PASSWORD})
    assert c.post("/api/v1/auth/logout").status_code == 204
    assert c.post("/api/v1/auth/refresh").status_code == 401


def test_new_user_must_change_password(client, tu_admin, unique):
    email = f"new-{unique}@demo-tu.uniload.example"
    _create_user(client, tu_admin, email)
    headers = login(client, email, "Boshlang1ch")
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"] is True
    weak = client.post("/api/v1/auth/password/change", headers=headers,
                       json={"current_password": "Boshlang1ch", "new_password": "faqatharf"})
    assert weak.status_code == 422 and weak.json()["code"] == "WEAK_PASSWORD"
    ok = client.post("/api/v1/auth/password/change", headers=headers,
                     json={"current_password": "Boshlang1ch", "new_password": "YangiParol2026"})
    assert ok.status_code == 204
    headers = login(client, email, "YangiParol2026")
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"] is False


def test_deactivated_user_loses_access(client, tu_admin, unique):
    email = f"off-{unique}@demo-tu.uniload.example"
    user = _create_user(client, tu_admin, email)
    headers = login(client, email, "Boshlang1ch")
    r = client.patch(f"/api/v1/users/{user['id']}", headers=tu_admin,
                     json={"row_version": user["row_version"], "is_active": False})
    assert r.status_code == 200, r.text
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post(LOGIN, json={"email": email, "password": "Boshlang1ch"}).status_code == 401


def test_password_reset_flow(client, tu_admin, unique, owner_db, caplog):
    email = f"reset-{unique}@demo-tu.uniload.example"
    _create_user(client, tu_admin, email)
    with caplog.at_level("WARNING", logger="uniload.auth"):
        assert client.post("/api/v1/auth/password/forgot", json={"email": email}).status_code == 204
    token = caplog.records[-1].getMessage().rsplit(" ", 1)[-1]
    assert client.post("/api/v1/auth/password/forgot", json={"email": "yoq@x.uz"}).status_code == 204
    r = client.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "Tiklangan2026"})
    assert r.status_code == 204
    login(client, email, "Tiklangan2026")
    again = client.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "Boshqa2026xx"})
    assert again.status_code == 400
