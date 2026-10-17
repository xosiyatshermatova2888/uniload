"""Unit testlar: DB’siz toza domen mantiqi."""

import uuid
from datetime import date

import pytest

from app.core.permissions import PERMISSIONS, SYSTEM_ROLES
from app.core.principal import Grant, Principal
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.modules.academic_years import domain


def _req(current, target, comment=None):
    return domain.TransitionRequest(current, target, comment)


@pytest.mark.parametrize("current,target", [
    ("draft", "calculated"), ("calculated", "distributing"), ("distributing", "in_review"),
    ("in_review", "approved"), ("approved", "archived"),
])
def test_forward_transitions_allowed(current, target):
    domain.check_transition(_req(current, target))


@pytest.mark.parametrize("current,target", [
    ("draft", "approved"), ("draft", "archived"), ("approved", "draft"), ("archived", "draft"),
    ("archived", "approved"), ("calculated", "in_review"),
])
def test_invalid_transitions_rejected(current, target):
    with pytest.raises(domain.TransitionError) as e:
        domain.check_transition(_req(current, target))
    assert e.value.code == "INVALID_TRANSITION"


def test_backward_transition_requires_comment():
    with pytest.raises(domain.TransitionError) as e:
        domain.check_transition(_req("in_review", "distributing", "  "))
    assert e.value.code == "COMMENT_REQUIRED"
    domain.check_transition(_req("in_review", "distributing", "Kafedra soatlarini qayta ko‘rib chiqing"))


def test_guards_are_called():
    calls = []

    def guard(req, ctx):
        calls.append((req.current, req.target))
        raise domain.TransitionError("NOT_CALCULATED", "Hisoblash bajarilmagan")

    domain.register_guard("draft", "calculated", guard)
    try:
        with pytest.raises(domain.TransitionError):
            domain.check_transition(_req("draft", "calculated"))
        assert calls == [("draft", "calculated")]
    finally:
        domain._GUARDS.pop(("draft", "calculated"))


def test_required_permission_per_target():
    assert domain.required_permission("approved") == "approval.final"
    assert domain.required_permission("archived") == "academic_year.archive"
    assert domain.required_permission("distributing") == "academic_year.transition"


def test_label_and_default_dates():
    assert domain.label(2027) == "2027–2028"
    assert domain.default_year_dates(2027) == (date(2027, 9, 1), date(2028, 8, 31))


def test_shift_year_handles_leap_day():
    assert domain.shift_year(date(2028, 2, 29)) == date(2029, 2, 28)
    assert domain.shift_year(date(2026, 9, 1)) == date(2027, 9, 1)


def test_validate_semesters():
    start, end = domain.default_year_dates(2026)
    assert domain.validate_semesters(domain.default_semesters(2026), start, end) == []
    overlapping = [domain.SemesterSpec(1, "K", date(2026, 9, 1), date(2027, 3, 1)),
                   domain.SemesterSpec(2, "B", date(2027, 2, 1), date(2027, 6, 30))]
    assert domain.validate_semesters(overlapping, start, end)
    outside = [domain.SemesterSpec(1, "K", date(2026, 8, 1), date(2027, 1, 31)),
               domain.SemesterSpec(2, "B", date(2027, 2, 1), date(2027, 6, 30))]
    assert domain.validate_semesters(outside, start, end)
    assert domain.validate_semesters(outside[:1], start, end)


def test_system_roles_use_known_permissions():
    for role in SYSTEM_ROLES.values():
        assert role.permissions <= PERMISSIONS.keys()
    # PO tizim sozlamalariga ham, foydalanuvchilarga ham ega emas.
    assert "users.manage" not in SYSTEM_ROLES["teacher"].permissions
    assert "academic_year.create" not in SYSTEM_ROLES["teacher"].permissions


def test_principal_scopes():
    dep_a, dep_b = uuid.uuid4(), uuid.uuid4()
    p = Principal(uuid.uuid4(), uuid.uuid4(), False, "x@y.uz", "X", grants=[
        Grant("workload.distribute", "department", dep_a),
        Grant("academic_year.create", "university", None),
    ])
    assert p.has("workload.distribute")
    assert p.has("workload.distribute", department_id=dep_a)
    assert not p.has("workload.distribute", department_id=dep_b)
    assert not p.has("workload.distribute", university_wide=True)
    assert p.has("academic_year.create", university_wide=True)
    assert p.has("academic_year.create", department_id=dep_b)
    assert not p.has("users.manage")


def test_password_hashing():
    h = hash_password("Parol123")
    assert verify_password("Parol123", h)
    assert not verify_password("parol123", h)
    assert not verify_password("Parol123", None)


def test_access_token_roundtrip():
    uid, uni = uuid.uuid4(), uuid.uuid4()
    token, ttl = create_access_token(user_id=uid, university_id=uni, is_platform_admin=False)
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid) and payload["uni"] == str(uni) and ttl > 0
