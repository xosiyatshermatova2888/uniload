"""O‘quv yili domeni: holat mashinasi va kalendar qoidalari (framework’siz toza Python).

docs/05-oquv-yili-algoritmi.md, 5.1.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

YEAR_STATUSES = ("draft", "calculated", "distributing", "in_review", "approved", "archived")
LOCKED_STATUSES = frozenset({"approved", "archived"})

STATUS_LABELS = {
    "draft": "Loyiha",
    "calculated": "Hisoblangan",
    "distributing": "Taqsimlanmoqda",
    "in_review": "Tekshiruvda",
    "approved": "Tasdiqlangan",
    "archived": "Arxivlangan",
}

TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"calculated"}),
    "calculated": frozenset({"draft", "distributing"}),
    "distributing": frozenset({"calculated", "in_review"}),
    "in_review": frozenset({"distributing", "approved"}),
    "approved": frozenset({"archived"}),
    "archived": frozenset(),
}

# Maqsad holat uchun maxsus ruxsat; qolganlari `academic_year.transition`.
TARGET_PERMISSION = {
    "approved": "approval.final",
    "archived": "academic_year.archive",
}

# Orqaga qaytarishda izoh majburiy.
COMMENT_REQUIRED = frozenset({("in_review", "distributing"), ("distributing", "calculated"),
                              ("calculated", "draft")})


class TransitionError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TransitionRequest:
    current: str
    target: str
    comment: str | None


# Keyingi bosqich modullari (hisoblash, taqsimot, tasdiqlash) bu yerga old shartlarni
# ro‘yxatdan o‘tkazadi, masalan: draft → calculated faqat muvaffaqiyatli hisoblashdan keyin.
# Guard xato bo‘lsa TransitionError ko‘taradi.
Guard = Callable[[TransitionRequest, object], None]
_GUARDS: dict[tuple[str, str], list[Guard]] = {}


def register_guard(current: str, target: str, guard: Guard) -> None:
    _GUARDS.setdefault((current, target), []).append(guard)


def required_permission(target: str) -> str:
    return TARGET_PERMISSION.get(target, "academic_year.transition")


def allowed_targets(current: str) -> list[str]:
    return [s for s in YEAR_STATUSES if s in TRANSITIONS.get(current, frozenset())]


def check_transition(req: TransitionRequest, context: object = None) -> None:
    if req.target not in YEAR_STATUSES:
        raise TransitionError("UNKNOWN_STATUS", f"Noma’lum holat: {req.target}")
    if req.target not in TRANSITIONS.get(req.current, frozenset()):
        raise TransitionError(
            "INVALID_TRANSITION",
            f"“{STATUS_LABELS[req.current]}” holatidan “{STATUS_LABELS[req.target]}” holatiga o‘tib bo‘lmaydi",
        )
    if (req.current, req.target) in COMMENT_REQUIRED and not (req.comment or "").strip():
        raise TransitionError("COMMENT_REQUIRED", "Orqaga qaytarishda izoh yozish majburiy")
    for guard in _GUARDS.get((req.current, req.target), []):
        guard(req, context)


def label(start_year: int) -> str:
    return f"{start_year}–{start_year + 1}"


def default_year_dates(start_year: int) -> tuple[date, date]:
    return date(start_year, 9, 1), date(start_year + 1, 8, 31)


@dataclass(frozen=True)
class SemesterSpec:
    term: int
    name: str
    starts_on: date
    ends_on: date
    weeks: int | None = None


def default_semesters(start_year: int) -> list[SemesterSpec]:
    """Sukut kalendar. Universitet o‘z sanalarini keyin tahrirlaydi."""
    return [
        SemesterSpec(1, "Kuzgi semestr", date(start_year, 9, 1), date(start_year + 1, 1, 31)),
        SemesterSpec(2, "Bahorgi semestr", date(start_year + 1, 2, 1), date(start_year + 1, 6, 30)),
    ]


def shift_year(d: date, years: int = 1) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29-fevral
        return d.replace(year=d.year + years, day=28)


def validate_semesters(specs: list[SemesterSpec], year_start: date, year_end: date) -> list[str]:
    errors: list[str] = []
    terms = sorted(s.term for s in specs)
    if terms != [1, 2]:
        errors.append("Aynan ikkita semestr bo‘lishi kerak: kuzgi (1) va bahorgi (2)")
        return errors
    by_term = {s.term: s for s in specs}
    for s in specs:
        if s.ends_on <= s.starts_on:
            errors.append(f"{s.term}-semestr: tugash sanasi boshlanishidan keyin bo‘lishi kerak")
        if s.starts_on < year_start or s.ends_on > year_end:
            errors.append(f"{s.term}-semestr o‘quv yili chegarasidan tashqarida")
    if by_term[1].ends_on >= by_term[2].starts_on:
        errors.append("Kuzgi semestr bahorgi semestrdan oldin tugashi kerak")
    return errors
