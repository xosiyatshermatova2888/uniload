"""2-bosqich: tuzilma, yo‘nalishlar, fanlar, o‘quv rejalari, guruhlar, oqimlar, o‘qituvchilar, yil nusxalash."""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.db.session import TenantScope, open_session
from app.modules.curricula.models import Subject
from tests.conftest import login, university_id

API = "/api/v1"


def ok(r, status=200):
    assert r.status_code == status, r.text
    return r.json()


@pytest.fixture(scope="module")
def tu_year(client, tu_office):
    return next(y for y in ok(client.get(f"{API}/academic-years", headers=tu_office)) if y["start_year"] == 2026)


@pytest.fixture(scope="module")
def refs(client, tu_office):
    deps = {d["code"]: d for d in ok(client.get(f"{API}/departments", headers=tu_office))}
    subjects = {s["code"]: s for s in ok(client.get(f"{API}/subjects", headers=tu_office))}
    programs = {p["code"]: p for p in ok(client.get(f"{API}/programs", headers=tu_office))}
    lesson_types = {t["code"]: t for t in ok(client.get(f"{API}/lesson-types", headers=tu_office))}
    return {"deps": deps, "subjects": subjects, "programs": programs, "lt": lesson_types}


# ------------------------------------------------------------------ tuzilma

def test_demo_reference_data_seeded(refs):
    assert {"DI", "AT", "OM", "IQ"} <= refs["deps"].keys()
    assert "60610600" in refs["programs"]
    assert {"lecture", "practice", "lab", "seminar", "course_work", "internship"} <= refs["lt"].keys()


def test_org_management_permissions_and_duplicates(client, tu_admin, tu_office, unique):
    assert client.post(f"{API}/faculties", headers=tu_office, json={"code": f"F{unique}", "name": "Test"}).status_code == 403
    fac = ok(client.post(f"{API}/faculties", headers=tu_admin, json={"code": f"F{unique}", "name": "Test fakulteti"}), 201)
    dup = client.post(f"{API}/faculties", headers=tu_admin, json={"code": f"f{unique}".lower(), "name": "Takror"})
    assert dup.status_code == 409 and dup.json()["code"] == "DUPLICATE"  # kod katta-kichik harfga sezgir emas
    dep = ok(client.post(f"{API}/departments", headers=tu_admin,
                         json={"faculty_id": fac["id"], "code": f"K{unique}", "name": "Test kafedrasi"}), 201)
    # Kafedrasi bor fakultetni o‘chirib bo‘lmaydi.
    r = client.delete(f"{API}/faculties/{fac['id']}", headers=tu_admin)
    assert r.status_code == 409 and r.json()["code"] == "REFERENCE_ERROR"
    # Birlashtirish kafedrani nofaol qiladi.
    other = ok(client.post(f"{API}/departments", headers=tu_admin,
                           json={"faculty_id": fac["id"], "code": f"M{unique}", "name": "Asosiy kafedra"}), 201)
    merged = ok(client.patch(f"{API}/departments/{dep['id']}", headers=tu_admin,
                             json={"row_version": dep["row_version"], "merged_into_id": other["id"]}))
    assert merged["is_active"] is False and merged["merged_into_id"] == other["id"]
    faculties = ok(client.get(f"{API}/faculties", headers=tu_office))
    assert next(f for f in faculties if f["id"] == fac["id"])["departments_count"] == 2


def test_null_in_required_field_is_422(client, tu_admin, refs):
    dep = refs["deps"]["OM"]
    r = client.patch(f"{API}/departments/{dep['id']}", headers=tu_admin,
                     json={"row_version": dep["row_version"], "faculty_id": None})
    assert r.status_code == 422


# ------------------------------------------------------------------ o‘quv rejalari

def _new_curriculum(client, headers, refs, admission_year=2030):
    return ok(client.post(f"{API}/curricula", headers=headers, json={
        "education_program_id": refs["programs"]["60610600"]["id"], "admission_year": admission_year,
        "title": "Test reja"}), 201)


def test_curriculum_lifecycle(client, tu_office, refs):
    c = _new_curriculum(client, tu_office, refs)
    assert c["status"] == "draft" and c["version"] == 1 and c["duration_years"] == 4
    om = refs["subjects"]["OM101"]["id"]
    base = f"{API}/curricula/{c['id']}/subjects"

    r = client.post(base, headers=tu_office, json={"subject_id": om, "semester_no": 9, "hours": {"lecture": 30}})
    assert r.status_code == 422 and r.json()["code"] == "SEMESTER_OUT_OF_RANGE"
    r = client.post(base, headers=tu_office, json={"subject_id": om, "semester_no": 1, "hours": {"nope": 30}})
    assert r.status_code == 422 and r.json()["code"] == "UNKNOWN_LESSON_TYPE"
    r = client.post(f"{API}/curricula/{c['id']}/approve", headers=tu_office,
                    json={"row_version": c["row_version"], "approval_doc": "Buyruq №1"})
    assert r.status_code == 422 and r.json()["code"] == "CURRICULUM_EMPTY"

    c = ok(client.post(base, headers=tu_office, json={
        "subject_id": om, "semester_no": 1, "credits": "6", "hours": {"lecture": "30", "practice": "45.5"}}), 201)
    entry = c["subjects"][0]
    assert entry["department_id"] == refs["deps"]["OM"]["id"]  # fanning asosiy kafedrasi
    assert entry["hours"] == {"lecture": "30.00", "practice": "45.50"}
    assert c["totals_by_semester"]["1"]["practice"] == "45.50"
    c = ok(client.patch(f"{base}/{entry['id']}", headers=tu_office,
                        json={"row_version": entry["row_version"], "hours": {"lecture": "36"}}))
    assert c["subjects"][0]["hours"] == {"lecture": "36.00"}

    approved = ok(client.post(f"{API}/curricula/{c['id']}/approve", headers=tu_office,
                              json={"row_version": c["row_version"], "approval_doc": "Buyruq №1, 01.09.2030"}))
    assert approved["status"] == "approved" and approved["approved_at"]
    r = client.post(base, headers=tu_office, json={"subject_id": refs["subjects"]["DI101"]["id"], "semester_no": 1})
    assert r.status_code == 409 and r.json()["code"] == "CURRICULUM_LOCKED"
    assert client.delete(f"{API}/curricula/{c['id']}", headers=tu_office).status_code == 409

    v2 = ok(client.post(f"{API}/curricula/{c['id']}/new-version", headers=tu_office), 201)
    assert v2["version"] == 2 and v2["status"] == "draft" and v2["based_on_id"] == c["id"]
    assert v2["subjects"][0]["hours"] == {"lecture": "36.00"}
    ok(client.patch(f"{API}/curricula/{v2['id']}/subjects/{v2['subjects'][0]['id']}", headers=tu_office,
                    json={"row_version": v2["subjects"][0]["row_version"], "hours": {"lecture": "40"}}))
    # Eski versiya o‘zgarmadi.
    assert ok(client.get(f"{API}/curricula/{c['id']}", headers=tu_office))["subjects"][0]["hours"] == {"lecture": "36.00"}


def test_curriculum_db_lock(client, tu_office, refs, owner_db):
    approved = next(c for c in ok(client.get(f"{API}/curricula", headers=tu_office, params={"status": "approved"})))
    uni = university_id(owner_db, "demo-tu")
    with open_session(TenantScope(uni)) as db:
        with pytest.raises(DBAPIError) as e:
            db.execute(text("UPDATE curriculum_subject_hours SET hours = 1 WHERE curriculum_subject_id IN "
                            "(SELECT id FROM curriculum_subjects WHERE curriculum_id = :c)"), {"c": approved["id"]})
        assert e.value.orig.sqlstate == "UL002"
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE curricula SET admission_year = 2000 WHERE id = :c"), {"c": approved["id"]})
        db.rollback()


def test_curriculum_permissions(client, tu_head, tu_teacher, refs):
    assert client.get(f"{API}/curricula", headers=tu_head).status_code == 200
    assert client.post(f"{API}/curricula", headers=tu_head, json={
        "education_program_id": refs["programs"]["60610600"]["id"], "admission_year": 2031}).status_code == 403
    assert client.get(f"{API}/curricula", headers=tu_teacher).status_code == 403


# ------------------------------------------------------------------ guruhlar va oqimlar

def _curriculum_for(client, headers, admission_year):
    return next(c for c in ok(client.get(f"{API}/curricula", headers=headers, params={
        "admission_year": admission_year, "status": "approved"})) if c["title"] and "DEMO" in c["title"])


def test_groups_crud_and_validation(client, tu_office, tu_year, unique):
    c = _curriculum_for(client, tu_office, 2026)
    base = f"{API}/years/{tu_year['id']}/groups"
    r = client.post(base, headers=tu_office, json={"curriculum_id": c["id"], "code": f"G{unique}", "course": 5})
    assert r.status_code == 422 and r.json()["code"] == "COURSE_OUT_OF_RANGE"
    r = client.post(base, headers=tu_office, json={"curriculum_id": c["id"], "code": f"G{unique}", "course": 1,
                                                    "student_count": 25, "budget_count": 10, "contract_count": 10})
    assert r.status_code == 422
    g = ok(client.post(base, headers=tu_office, json={"curriculum_id": c["id"], "code": f"G{unique}", "course": 1,
                                                       "student_count": 25, "budget_count": 15, "contract_count": 10}), 201)
    dup = client.post(base, headers=tu_office, json={"curriculum_id": c["id"], "code": f"g{unique}", "course": 1})
    assert dup.status_code == 409
    bad = client.patch(base, headers=tu_office, json={"items": [
        {"id": g["id"], "row_version": g["row_version"], "student_count": 28}]})
    assert bad.status_code == 422 and bad.json()["code"] == "CONTINGENT_MISMATCH"
    upd = ok(client.patch(base, headers=tu_office, json={"items": [
        {"id": g["id"], "row_version": g["row_version"], "student_count": 28, "budget_count": 18,
         "contract_count": 10}]}))
    assert upd[0]["student_count"] == 28 and upd[0]["needs_review"] is False
    listed = ok(client.get(base, headers=tu_office, params={"q": unique}))
    assert [x["id"] for x in listed] == [g["id"]]
    assert client.delete(f"{base}/{g['id']}", headers=tu_office).status_code == 204


def test_streams_validate_curriculum(client, tu_office, tu_year, refs):
    groups = {g["code"]: g for g in ok(client.get(f"{API}/years/{tu_year['id']}/groups", headers=tu_office))}
    autumn = next(s for s in tu_year_detail(client, tu_office, tu_year)["semesters"] if s["term"] == 1)
    base = f"{API}/years/{tu_year['id']}/streams"
    body = {"name": "Test oqim", "semester_id": autumn["id"], "subject_id": refs["subjects"]["OM101"]["id"],
            "lesson_type_id": refs["lt"]["lecture"]["id"], "group_ids": [groups["DI-26a"]["id"], groups["IQ-26"]["id"]]}
    stream = ok(client.post(base, headers=tu_office, json=body), 201)
    assert stream["student_count"] == groups["DI-26a"]["student_count"] + groups["IQ-26"]["student_count"]
    # DI-24 (3-kurs) kuzgi semestrda 5-semestr fanlarini o‘qiydi — Oliy matematika u yerda yo‘q.
    r = client.post(base, headers=tu_office, json={**body, "group_ids": [groups["DI-24"]["id"]]})
    assert r.status_code == 422 and r.json()["code"] == "SUBJECT_NOT_IN_CURRICULUM"
    r = client.patch(f"{base}/{stream['id']}", headers=tu_office,
                     json={"row_version": stream["row_version"], "group_ids": [groups["DI-26a"]["id"]] * 2})
    assert r.status_code == 422
    assert client.delete(f"{base}/{stream['id']}", headers=tu_office).status_code == 204


def tu_year_detail(client, headers, year):
    return ok(client.get(f"{API}/academic-years/{year['id']}", headers=headers))


def test_stream_group_cannot_cross_years(owner_db):
    """DB darajasida: boshqa yildagi guruhni oqimga qo‘shib bo‘lmaydi (kompozit FK)."""
    stream = owner_db.execute(text("SELECT id, academic_year_id, university_id FROM streams LIMIT 1")).first()
    other_group = owner_db.execute(text("SELECT id FROM student_groups WHERE academic_year_id <> :y LIMIT 1"),
                                   {"y": stream.academic_year_id}).scalar()
    if other_group is None:
        pytest.skip("Boshqa yilda guruh yo‘q")
    try:
        with pytest.raises(DBAPIError) as e:
            owner_db.execute(text("INSERT INTO stream_groups (university_id, academic_year_id, stream_id, group_id) "
                                  "VALUES (:u, :y, :s, :g)"), {"u": stream.university_id, "y": stream.academic_year_id,
                                                               "s": stream.id, "g": other_group})
        assert e.value.orig.sqlstate == "23503"
    finally:
        owner_db.rollback()


# ------------------------------------------------------------------ o‘qituvchilar

def test_teachers_employment_and_norms(client, tu_admin, tu_office, refs, free_year, unique):
    year = ok(client.post(f"{API}/academic-years", headers=tu_office, json={"start_year": free_year}), 201)
    t = ok(client.post(f"{API}/teachers", headers=tu_office, json={
        "last_name": "Test", "first_name": unique, "employee_no": f"T-{unique}", "academic_degree": "phd"}), 201)
    assert t["full_name"] == f"Test {unique}"
    base = f"{API}/years/{year['id']}/employment"
    e = ok(client.post(base, headers=tu_office, json={
        "teacher_id": t["id"], "department_id": refs["deps"]["AT"]["id"], "position_code": "docent", "rate": "1.5"}), 201)
    assert e["norm_hours"] is None  # me’yor kiritilmagan — tizim taxmin qilmaydi
    r = client.post(base, headers=tu_office, json={
        "teacher_id": t["id"], "department_id": refs["deps"]["AT"]["id"], "position_code": "docent", "rate": "0.5"})
    assert r.status_code == 409  # bir kafedrada bir xil bandlik turi takrorlanmaydi

    norms = ok(client.put(f"{API}/years/{year['id']}/position-norms", headers=tu_office, json={
        "norms": [{"position_code": "docent", "norm_hours_per_rate": "600", "source_document": "Test hujjat"}]}))
    assert next(n for n in norms if n["position_code"] == "docent")["norm_hours_per_rate"] == "600.00"
    listed = ok(client.get(base, headers=tu_office, params={"teacher_id": t["id"]}))
    assert listed[0]["norm_hours"] == "900.00"  # 1.5 × 600, snapshot qayta hisoblandi

    history = ok(client.get(f"{API}/teachers/{t['id']}/history", headers=tu_office))
    assert [h["year_label"] for h in history] == [year["label"]]


def test_department_scope_for_heads(client, tu_admin, tu_head, tu_year, refs, unique):
    di, at = refs["deps"]["DI"]["id"], refs["deps"]["AT"]["id"]
    visible = ok(client.get(f"{API}/years/{tu_year['id']}/employment", headers=tu_head))
    assert visible and {e["department_id"] for e in visible} == {di}
    # Sukut bo‘yicha kafedra mudirida bandlikni boshqarish ruxsati yo‘q.
    teacher = ok(client.get(f"{API}/teachers", headers=tu_admin))[0]
    body = {"teacher_id": teacher["id"], "department_id": di, "position_code": "assistant",
            "employment_type": "hourly", "rate": "0.25"}
    assert client.post(f"{API}/years/{tu_year['id']}/employment", headers=tu_head, json=body).status_code == 403

    # Maxsus rol: AT kafedrasi ko‘lamida teachers.manage.
    role = ok(client.post(f"{API}/roles", headers=tu_admin, json={
        "code": f"at_manager_{unique}", "name": "AT kadrlar", "default_scope": "department",
        "permissions": ["teachers.view", "teachers.manage"]}), 201)
    user = ok(client.post(f"{API}/users", headers=tu_admin, json={
        "username": f"at-{unique}", "full_name": "AT kadr", "initial_password": "Boshlang1ch",
        "roles": [{"role_id": role["id"], "scope_type": "department", "scope_id": at}]}), 201)
    headers = login(client, user["username"], "Boshlang1ch")
    assert client.post(f"{API}/years/{tu_year['id']}/employment", headers=headers, json=body).status_code == 403
    created = ok(client.post(f"{API}/years/{tu_year['id']}/employment", headers=headers,
                             json={**body, "department_id": at}), 201)
    assert created["department_id"] == at
    assert client.delete(f"{API}/years/{tu_year['id']}/employment/{created['id']}", headers=headers).status_code == 204

    bad = client.post(f"{API}/users", headers=tu_admin, json={
        "username": f"bad-{unique}", "full_name": "Xato", "initial_password": "Boshlang1ch",
        "roles": [{"role_id": role["id"], "scope_type": "department", "scope_id": str(uuid.uuid4())}]})
    assert bad.status_code == 422 and bad.json()["code"] == "SCOPE_NOT_FOUND"


def test_faculty_scope_expands_to_departments(client, tu_admin, refs, unique):
    faculty_id = refs["deps"]["IQ"]["faculty_id"]
    role = next(r for r in ok(client.get(f"{API}/roles", headers=tu_admin)) if r["code"] == "department_head")
    user = ok(client.post(f"{API}/users", headers=tu_admin, json={
        "username": f"dekan-{unique}", "full_name": "Dekan", "initial_password": "Boshlang1ch",
        "roles": [{"role_id": role["id"], "scope_type": "faculty", "scope_id": faculty_id}]}), 201)
    headers = login(client, user["username"], "Boshlang1ch")
    year = next(y for y in ok(client.get(f"{API}/academic-years", headers=headers)) if y["start_year"] == 2026)
    visible = ok(client.get(f"{API}/years/{year['id']}/employment", headers=headers))
    assert visible and {e["department_id"] for e in visible} == {refs["deps"]["IQ"]["id"]}


# ------------------------------------------------------------------ qulflangan yil

def test_locked_year_blocks_reference_changes(client, tu_office, tu_admin, refs, free_year, owner_db):
    year = ok(client.post(f"{API}/academic-years", headers=tu_office, json={"start_year": free_year}), 201)
    c = _curriculum_for(client, tu_office, 2026)
    g = ok(client.post(f"{API}/years/{year['id']}/groups", headers=tu_office,
                       json={"curriculum_id": c["id"], "code": "LOCK-1", "course": 1}), 201)
    owner_db.execute(text("UPDATE academic_years SET status = 'approved' WHERE id = :y"), {"y": year["id"]})
    owner_db.commit()
    r = client.patch(f"{API}/years/{year['id']}/groups/{g['id']}", headers=tu_office,
                     json={"row_version": g["row_version"], "student_count": 5})
    assert r.status_code == 409 and r.json()["code"] == "YEAR_LOCKED"
    r = client.put(f"{API}/years/{year['id']}/position-norms", headers=tu_office, json={"norms": []})
    assert r.status_code == 409
    uni = university_id(owner_db, "demo-tu")
    with open_session(TenantScope(uni)) as db:
        with pytest.raises(DBAPIError) as e:
            db.execute(text("UPDATE student_groups SET student_count = 1 WHERE id = :g"), {"g": g["id"]})
        assert e.value.orig.sqlstate == "UL001"
        db.rollback()


# ------------------------------------------------------------------ yil nusxalash

def test_copy_year_promotes_groups_and_keeps_source(client, tu_office, tu_year):
    groups_before = ok(client.get(f"{API}/years/{tu_year['id']}/groups", headers=tu_office))
    employment_before = ok(client.get(f"{API}/years/{tu_year['id']}/employment", headers=tu_office))
    body = {"start_year": 2027, "mode": "copy", "source_year_id": tu_year["id"]}

    preview = ok(client.post(f"{API}/academic-years/preview", headers=tu_office, json=body))
    assert preview["graduates_skipped"] == ["DI-23"]
    assert preview["will_copy"]["groups"] == len(groups_before) - 1
    assert preview["will_copy"]["employment"] == len(employment_before)
    assert preview["will_copy"]["norms"] == 5

    target = ok(client.post(f"{API}/academic-years", headers=tu_office, json=body), 201)
    new_groups = {g["code"]: g for g in ok(client.get(f"{API}/years/{target['id']}/groups", headers=tu_office))}
    old_groups = {g["code"]: g for g in groups_before}
    assert "DI-23" not in new_groups
    for code, g in new_groups.items():
        assert g["course"] == old_groups[code]["course"] + 1
        assert g["needs_review"] is True and g["source_group_id"] == old_groups[code]["id"]
        assert g["id"] != old_groups[code]["id"]
    assert ok(client.get(f"{API}/years/{target['id']}/streams", headers=tu_office)) == []  # oqimlar ko‘chirilmaydi
    new_emp = ok(client.get(f"{API}/years/{target['id']}/employment", headers=tu_office))
    assert len(new_emp) == len(employment_before)
    assert {e["id"] for e in new_emp}.isdisjoint({e["id"] for e in employment_before})

    # Manba yil o‘zgarmagan.
    assert ok(client.get(f"{API}/years/{tu_year['id']}/groups", headers=tu_office)) == groups_before
    assert ok(client.get(f"{API}/years/{tu_year['id']}/employment", headers=tu_office)) == employment_before

    # Yangi yilda kontingentni o‘zgartirish manba yilga ta’sir qilmaydi.
    g = new_groups["DI-24"]
    ok(client.patch(f"{API}/years/{target['id']}/groups/{g['id']}", headers=tu_office,
                    json={"row_version": g["row_version"], "student_count": 3}))
    assert next(x for x in ok(client.get(f"{API}/years/{tu_year['id']}/groups", headers=tu_office))
                if x["code"] == "DI-24")["student_count"] == old_groups["DI-24"]["student_count"]


# ------------------------------------------------------------------ tenant izolyatsiyasi

def test_reference_data_isolated_between_tenants(client, tu_office, pu_office, refs, tu_year, owner_db):
    pu_subjects = {s["id"] for s in ok(client.get(f"{API}/subjects", headers=pu_office))}
    assert pu_subjects.isdisjoint({s["id"] for s in refs["subjects"].values()})
    dep_id = refs["deps"]["DI"]["id"]
    r = client.patch(f"{API}/departments/{dep_id}", headers=login(client, "admin.pu"),
                     json={"row_version": 1, "name": "Hack"})
    assert r.status_code == 404
    assert client.get(f"{API}/years/{tu_year['id']}/groups", headers=pu_office).status_code == 404
    curriculum = _curriculum_for(client, tu_office, 2026)
    assert client.get(f"{API}/curricula/{curriculum['id']}", headers=pu_office).status_code == 404
    # Boshqa tenant fani bilan o‘quv reja to‘ldirib bo‘lmaydi.
    pu_curriculum = _curriculum_for(client, pu_office, 2026)
    pu_draft = ok(client.post(f"{API}/curricula/{pu_curriculum['id']}/new-version", headers=pu_office), 201)
    r = client.post(f"{API}/curricula/{pu_draft['id']}/subjects", headers=pu_office,
                    json={"subject_id": refs["subjects"]["OM101"]["id"], "semester_no": 1})
    assert r.status_code == 404

    tu = university_id(owner_db, "demo-tu")
    with open_session(TenantScope(tu)) as db:
        assert {s.university_id for s in db.scalars(select(Subject))} == {tu}


def test_new_university_gets_lesson_types(client, super_admin, unique):
    ok(client.post(f"{API}/platform/universities", headers=super_admin, json={
        "code": f"lt-{unique}", "name": "DEMO LT universiteti", "first_admin": {
            "username": f"admin.lt-{unique}", "full_name": "Admin", "initial_password": "Boshlang1ch"}}),
       201)
    admin = login(client, f"admin.lt-{unique}", "Boshlang1ch")
    # Universitet admini o‘quv rejani ko‘ra olmaydi (curriculum.view bor) — mashg‘ulot turlari yaratilgan.
    types = ok(client.get(f"{API}/lesson-types", headers=admin))
    assert len(types) == 11 and all(t["is_system"] for t in types)
