from tests.conftest import PASSWORD, login, login_for

LOGIN = "/api/v1/auth/login"


def _create_user(client, admin_headers, username, password="Boshlang1ch", email=None):
    r = client.post("/api/v1/users", headers=admin_headers, json={
        "username": username, "email": email, "full_name": "Test Foydalanuvchi", "initial_password": password, "roles": []})
    assert r.status_code == 201, r.text
    return r.json()


def test_login_returns_profile_and_sets_refresh_cookie(client):
    r = client.post(LOGIN, json={"username": f"  {login_for('oquv').upper()} ", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["university"]["code"] == "demo-tu"
    assert "academic_year.create" in body["user"]["permissions"]
    assert "academic_office" in body["user"]["roles"]
    cookie = r.headers["set-cookie"]
    assert "uniload_refresh=" in cookie and "HttpOnly" in cookie and "samesite=strict" in cookie.lower()


def test_wrong_password_and_unknown_login_give_same_error(client):
    a = client.post(LOGIN, json={"username": login_for("oquv"), "password": "notogri123"})
    b = client.post(LOGIN, json={"username": "yoq.tu", "password": "notogri123"})
    assert a.status_code == b.status_code == 401
    assert a.json()["code"] == b.json()["code"] == "INVALID_CREDENTIALS"
    assert a.json()["detail"] == b.json()["detail"]


def test_lockout_after_repeated_failures(client, tu_admin, unique):
    username = f"lock-{unique}"
    _create_user(client, tu_admin, username)
    for _ in range(5):
        assert client.post(LOGIN, json={"username": username, "password": "xato12345"}).status_code == 401
    r = client.post(LOGIN, json={"username": username, "password": "Boshlang1ch"})
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
    first = c.post(LOGIN, json={"username": login_for("kafedra"), "password": PASSWORD})
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
    c.post(LOGIN, json={"username": login_for("oqituvchi"), "password": PASSWORD})
    assert c.post("/api/v1/auth/logout").status_code == 204
    assert c.post("/api/v1/auth/refresh").status_code == 401


def test_new_user_must_change_password(client, tu_admin, unique):
    username = f"new-{unique}"
    _create_user(client, tu_admin, username)
    headers = login(client, username, "Boshlang1ch")
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"] is True
    weak = client.post("/api/v1/auth/password/change", headers=headers,
                       json={"current_password": "Boshlang1ch", "new_password": "faqatharf"})
    assert weak.status_code == 422 and weak.json()["code"] == "WEAK_PASSWORD"
    ok = client.post("/api/v1/auth/password/change", headers=headers,
                     json={"current_password": "Boshlang1ch", "new_password": "YangiParol2026"})
    assert ok.status_code == 204
    headers = login(client, username, "YangiParol2026")
    assert client.get("/api/v1/auth/me", headers=headers).json()["must_change_password"] is False


def test_deactivated_user_loses_access(client, tu_admin, unique):
    username = f"off-{unique}"
    user = _create_user(client, tu_admin, username)
    headers = login(client, username, "Boshlang1ch")
    r = client.patch(f"/api/v1/users/{user['id']}", headers=tu_admin,
                     json={"row_version": user["row_version"], "is_active": False})
    assert r.status_code == 200, r.text
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post(LOGIN, json={"username": username, "password": "Boshlang1ch"}).status_code == 401


def test_password_reset_flow(client, tu_admin, unique, owner_db, caplog):
    username = f"reset-{unique}"
    _create_user(client, tu_admin, username, email=f"reset-{unique}@demo-tu.uniload.example")
    with caplog.at_level("WARNING", logger="uniload.auth"):
        assert client.post("/api/v1/auth/password/forgot", json={"username": username}).status_code == 204
    token = caplog.records[-1].getMessage().rsplit(" ", 1)[-1]
    assert client.post("/api/v1/auth/password/forgot", json={"username": "yoq"}).status_code == 204
    r = client.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "Tiklangan2026"})
    assert r.status_code == 204
    login(client, username, "Tiklangan2026")
    again = client.post("/api/v1/auth/password/reset", json={"token": token, "new_password": "Boshqa2026xx"})
    assert again.status_code == 400


def test_email_is_not_a_login(client, tu_admin, unique):
    _create_user(client, tu_admin, f"mail-{unique}", email=f"mail-{unique}@demo-tu.uniload.example")
    assert client.post(LOGIN, json={"email": f"mail-{unique}@demo-tu.uniload.example",
                                    "password": "Boshlang1ch"}).status_code == 422
    r = client.post(LOGIN, json={"username": f"mail-{unique}@demo-tu.uniload.example", "password": "Boshlang1ch"})
    assert r.status_code == 401
    login(client, f"mail-{unique}", "Boshlang1ch")


def test_invalid_username_rejected(client, tu_admin):
    for bad in ["ab", "-start", "bo sh", "o‘quv", "a" * 65]:
        r = client.post("/api/v1/users", headers=tu_admin, json={
            "username": bad, "full_name": "Xato", "initial_password": "Boshlang1ch"})
        assert r.status_code == 422, bad


def test_reset_needs_email(client, tu_admin, unique, caplog):
    _create_user(client, tu_admin, f"nomail-{unique}")
    with caplog.at_level("WARNING", logger="uniload.auth"):
        assert client.post("/api/v1/auth/password/forgot", json={"username": f"nomail-{unique}"}).status_code == 204
    assert not any("tokeni" in r.getMessage() for r in caplog.records)
