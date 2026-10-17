import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import TenantScope, open_session
from app.modules.academic_years.models import AcademicYear, Semester
from tests.conftest import university_id

YEARS = "/api/v1/academic-years"


def _create(client, headers, start_year, **extra):
    r = client.post(YEARS, headers=headers, json={"start_year": start_year, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _move(client, headers, year, to, comment=None):
    r = client.post(f"{YEARS}/{year['id']}/transitions", headers=headers,
                    json={"to": to, "comment": comment, "row_version": year["row_version"]})
    return r


def _walk(client, office, admin, year, until):
    path = ["draft", "calculated", "distributing", "in_review", "approved", "archived"]
    for status in path[path.index(year["status"]) + 1:]:
        headers = admin if status in ("approved", "archived") else office
        r = _move(client, headers, year, status)
        assert r.status_code == 200, r.text
        year = r.json()
        if status == until:
            return year
    return year


def test_create_empty_year(client, tu_office, free_year):
    year = _create(client, tu_office, free_year)
    assert year["label"] == f"{free_year}–{free_year + 1}"
    assert year["status"] == "draft" and year["status_label"] == "Loyiha"
    assert year["is_current"] is False  # demo seed’da joriy yil allaqachon bor
    assert [s["term"] for s in year["semesters"]] == [1, 2]
    assert year["allowed_transitions"] == ["calculated"]


def test_duplicate_year_conflict(client, tu_office, free_year):
    _create(client, tu_office, free_year)
    r = client.post(YEARS, headers=tu_office, json={"start_year": free_year})
    assert r.status_code == 409 and r.json()["code"] == "YEAR_EXISTS"


def test_copy_year_shifts_semesters_and_keeps_source(client, tu_office, free_year):
    source = _create(client, tu_office, free_year)
    custom = [
        {"term": 1, "name": "Kuzgi", "starts_on": f"{free_year}-09-02", "ends_on": f"{free_year + 1}-01-20",
         "weeks": 16},
        {"term": 2, "name": "Bahorgi", "starts_on": f"{free_year + 1}-02-05", "ends_on": f"{free_year + 1}-06-15",
         "weeks": 18},
    ]
    r = client.put(f"/api/v1/years/{source['id']}/semesters", headers=tu_office, json={"semesters": custom})
    assert r.status_code == 200, r.text
    before = client.get(f"{YEARS}/{source['id']}", headers=tu_office).json()

    preview = client.post(f"{YEARS}/preview", headers=tu_office, json={
        "start_year": free_year + 1, "mode": "copy", "source_year_id": source["id"]})
    assert preview.status_code == 200
    assert preview.json()["will_copy"] == {"semesters": 2}
    assert preview.json()["not_yet_available"]
    # Preview hech narsa yozmaydi.
    ids = [y["start_year"] for y in client.get(YEARS, headers=tu_office).json()]
    assert free_year + 1 not in ids

    target = client.post(YEARS, headers=tu_office, json={
        "start_year": free_year + 1, "mode": "copy", "source_year_id": source["id"]})
    assert target.status_code == 201, target.text
    t = target.json()
    assert t["source_year_id"] == source["id"] and t["source_label"] == source["label"]
    assert t["semesters"][0]["starts_on"] == f"{free_year + 1}-09-02"
    assert t["semesters"][1]["weeks"] == 18
    assert {s["id"] for s in t["semesters"]}.isdisjoint({s["id"] for s in before["semesters"]})

    after = client.get(f"{YEARS}/{source['id']}", headers=tu_office).json()
    assert after == before  # manba yil o‘zgarmadi


def test_copy_requires_earlier_source(client, tu_office, free_year):
    src = _create(client, tu_office, free_year)
    r = client.post(YEARS, headers=tu_office, json={
        "start_year": free_year, "mode": "copy", "source_year_id": src["id"]})
    assert r.status_code == 422 and r.json()["code"] == "SOURCE_AFTER_TARGET"


def test_full_lifecycle_and_permissions(client, tu_office, tu_admin, free_year):
    year = _create(client, tu_office, free_year)
    year = _walk(client, tu_office, tu_admin, year, "in_review")

    # O‘quv bo‘limida approval.final yo‘q.
    r = _move(client, tu_office, year, "approved")
    assert r.status_code == 403
    # Orqaga qaytarishda izoh majburiy.
    r = _move(client, tu_office, year, "distributing")
    assert r.status_code == 409 and r.json()["code"] == "COMMENT_REQUIRED"
    r = _move(client, tu_office, year, "distributing", "Kafedra soatlari tekshirilsin")
    assert r.status_code == 200
    year = _walk(client, tu_office, tu_admin, r.json(), "approved")
    assert year["is_locked"] and year["approved_at"]
    assert year["allowed_transitions"] == ["archived"]

    r = _move(client, tu_office, year, "draft")
    assert r.status_code == 409 and r.json()["code"] == "INVALID_TRANSITION"
    r = client.patch(f"{YEARS}/{year['id']}", headers=tu_office,
                     json={"row_version": year["row_version"], "ends_on": f"{free_year + 1}-08-30"})
    assert r.status_code == 409 and r.json()["code"] == "YEAR_LOCKED"
    r = client.put(f"/api/v1/years/{year['id']}/semesters", headers=tu_office,
                   json={"semesters": year["semesters"]})
    assert r.status_code == 409 and r.json()["code"] == "YEAR_LOCKED"

    archived = _move(client, tu_admin, year, "archived")
    assert archived.status_code == 200 and archived.json()["archived_at"]


def test_stale_row_version_rejected(client, tu_office, free_year):
    year = _create(client, tu_office, free_year)
    ok = _move(client, tu_office, year, "calculated")
    assert ok.status_code == 200
    stale = _move(client, tu_office, year, "draft", "qayta")  # eski row_version
    assert stale.status_code == 409 and stale.json()["code"] == "CONCURRENT_UPDATE"


def test_set_current(client, tu_office, free_year):
    year = _create(client, tu_office, free_year)
    r = client.post(f"{YEARS}/{year['id']}/set-current", headers=tu_office)
    assert r.status_code == 200 and r.json()["is_current"]
    current = [y for y in client.get(YEARS, headers=tu_office).json() if y["is_current"]]
    assert [y["id"] for y in current] == [year["id"]]
    # Seed’dagi 2026–2027 ni yana joriy qilib qo‘yamiz.
    seed_year = next(y for y in client.get(YEARS, headers=tu_office).json() if y["start_year"] == 2026)
    assert client.post(f"{YEARS}/{seed_year['id']}/set-current", headers=tu_office).status_code == 200


def test_role_permissions_on_years(client, tu_teacher, tu_head, tu_admin, free_year):
    assert client.get(YEARS, headers=tu_teacher).status_code == 200
    assert client.get(YEARS, headers=tu_head).status_code == 200
    for headers in (tu_teacher, tu_head, tu_admin):
        r = client.post(YEARS, headers=headers, json={"start_year": free_year})
        assert r.status_code == 403, headers


def test_semesters_validation(client, tu_office, free_year):
    year = _create(client, tu_office, free_year)
    bad = [
        {"term": 1, "name": "Kuzgi", "starts_on": f"{free_year}-09-01", "ends_on": f"{free_year + 1}-03-01"},
        {"term": 2, "name": "Bahorgi", "starts_on": f"{free_year + 1}-02-01", "ends_on": f"{free_year + 1}-06-30"},
    ]
    r = client.put(f"/api/v1/years/{year['id']}/semesters", headers=tu_office, json={"semesters": bad})
    assert r.status_code == 422 and r.json()["code"] == "SEMESTERS_INVALID"


def test_db_trigger_blocks_changes_in_approved_year(client, tu_office, tu_admin, free_year, owner_db):
    year = _walk(client, tu_office, tu_admin, _create(client, tu_office, free_year), "approved")
    uni = university_id(owner_db, "demo-tu")

    # Servisni chetlab, to‘g‘ridan-to‘g‘ri SQL bilan ham o‘zgartirib bo‘lmaydi.
    with open_session(TenantScope(uni)) as db:
        with pytest.raises(DBAPIError) as e:
            db.execute(text("UPDATE semesters SET weeks = 10 WHERE academic_year_id = :y"), {"y": year["id"]})
            db.flush()
        assert e.value.orig.sqlstate == "UL001"
        db.rollback()

    with open_session(TenantScope(uni)) as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE academic_years SET status = 'draft' WHERE id = :y"), {"y": year["id"]})
        db.rollback()

    # Override sababi bilan — ruxsat (4-bosqichda maxsus ruxsat + audit orqali ishlatiladi).
    with open_session(TenantScope(uni, override_reason="Test: buyruq №1")) as db:
        db.execute(text("UPDATE semesters SET weeks = 10 WHERE academic_year_id = :y"), {"y": year["id"]})
        db.rollback()


def test_year_label_is_generated(owner_db, client, tu_office, free_year):
    year = _create(client, tu_office, free_year)
    row = owner_db.scalar(select(AcademicYear).where(AcademicYear.id == year["id"]))
    assert row.label == f"{free_year}–{free_year + 1}"
    assert owner_db.scalar(select(Semester.university_id).where(Semester.academic_year_id == row.id).limit(1)) \
        == row.university_id
