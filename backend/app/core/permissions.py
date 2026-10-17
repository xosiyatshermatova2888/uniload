"""Ruxsatlar katalogi va tizim rollari (docs/04-rollar-ruxsatlar.md).

Katalog — kodning yagona manbasi. `python -m app.cli bootstrap` uni bazaga sinxronlaydi.
"""

from dataclasses import dataclass

PERMISSIONS: dict[str, tuple[str, str]] = {
    # code: (module, description)
    "platform.tenants.manage": ("platform", "Universitetlarni yaratish va boshqarish"),
    "platform.subscriptions.manage": ("platform", "Tarif va obunalarni boshqarish"),
    "platform.subscriptions.view": ("platform", "O‘z obunasini ko‘rish"),
    "platform.system.manage": ("platform", "Texnik sozlamalar va tizim holati"),
    "settings.view": ("settings", "Universitet sozlamalarini ko‘rish"),
    "settings.manage": ("settings", "Universitet profili va sozlamalarini o‘zgartirish"),
    "settings.workflow.manage": ("settings", "Tasdiqlash zanjirini sozlash"),
    "users.manage": ("users", "Foydalanuvchilar va rollarni boshqarish"),
    "dashboard.view": ("dashboard", "Boshqaruv panelini ko‘rish"),
    "org.view": ("org", "Fakultet va kafedralarni ko‘rish"),
    "org.manage": ("org", "Fakultet va kafedralarni boshqarish"),
    "programs.view": ("programs", "Ta’lim yo‘nalishlarini ko‘rish"),
    "programs.manage": ("programs", "Ta’lim yo‘nalishlarini boshqarish"),
    "academic_year.view": ("academic_year", "O‘quv yillarini ko‘rish"),
    "academic_year.create": ("academic_year", "O‘quv yilini yaratish, nusxalash va tahrirlash"),
    "academic_year.transition": ("academic_year", "O‘quv yili holatini o‘zgartirish"),
    "academic_year.archive": ("academic_year", "O‘quv yilini arxivlash"),
    "curriculum.view": ("curriculum", "O‘quv rejalarini ko‘rish"),
    "curriculum.manage": ("curriculum", "O‘quv rejalarini yuklash va tahrirlash"),
    "curriculum.approve": ("curriculum", "O‘quv reja versiyasini tasdiqlash"),
    "subjects.view": ("subjects", "Fanlar katalogini ko‘rish"),
    "subjects.manage": ("subjects", "Fanlar katalogini boshqarish"),
    "groups.view": ("groups", "Akademik guruhlarni ko‘rish"),
    "groups.manage": ("groups", "Guruhlar, kontingent va oqimlarni boshqarish"),
    "teachers.view": ("teachers", "O‘qituvchilarni ko‘rish"),
    "teachers.manage": ("teachers", "O‘qituvchilar va yillik bandlikni boshqarish"),
    "imports.run": ("imports", "Excel import"),
    "imports.pdf": ("imports", "PDF tahlil"),
    "rules.draft": ("rules", "Hisoblash qoidasi qoralamasini yaratish"),
    "rules.activate": ("rules", "Hisoblash qoidasini faollashtirish"),
    "workload.view": ("workload", "Hisoblangan yuklamani ko‘rish"),
    "workload.calculate": ("workload", "Yuklamani hisoblashni ishga tushirish"),
    "workload.distribute": ("workload", "Yuklamani taqsimlash"),
    "workload.submit": ("workload", "Taqsimotni tasdiqlashga yuborish"),
    "workload.override": ("workload", "Tasdiqlangan yuklamani o‘zgartirish"),
    "approval.department": ("approval", "Kafedra taqsimotini tasdiqlash"),
    "approval.final": ("approval", "Universitet yuklamasini yakuniy tasdiqlash"),
    "reports.view": ("reports", "Hisobotlarni ko‘rish"),
    "reports.export": ("reports", "Hisobotlarni eksport qilish"),
    "reports.templates": ("reports", "Hisobot shablonlarini sozlash"),
    "integrations.view": ("integrations", "Integratsiyalarni ko‘rish"),
    "integrations.manage": ("integrations", "ESPOS sozlash va sinxronlash"),
    "audit.view": ("audit", "Audit logni ko‘rish"),
    "self.workload.view": ("self", "O‘z yuklamasi va tarixini ko‘rish"),
}


@dataclass(frozen=True)
class SystemRole:
    code: str
    name: str
    default_scope: str
    permissions: frozenset[str]


# Matritsadagi ⚙️ ("sozlamaga bog‘liq") ruxsatlar sukut bo‘yicha berilmaydi — universitet
# admin ularni maxsus rol orqali beradi. Istisno: tizim ishlashi uchun UA yakuniy tasdiq va
# override’ga, O‘quv bo‘limi qoidani faollashtirishga ega (ikki kalit qoidasi servisda).
_KM_VIEW = {"dashboard.view", "org.view", "programs.view", "academic_year.view", "curriculum.view",
            "subjects.view", "groups.view", "teachers.view"}

SYSTEM_ROLES: dict[str, SystemRole] = {
    "super_admin": SystemRole("super_admin", "Super Admin", "platform", frozenset({
        "platform.tenants.manage", "platform.subscriptions.manage", "platform.system.manage",
        "users.manage", "audit.view",
    })),
    "university_admin": SystemRole("university_admin", "Universitet Admin", "university", frozenset({
        "platform.subscriptions.view", "settings.view", "settings.manage", "settings.workflow.manage",
        "users.manage", "dashboard.view", "org.view", "org.manage", "programs.view", "programs.manage",
        "academic_year.view", "academic_year.archive", "curriculum.view", "subjects.view", "groups.view",
        "teachers.view", "teachers.manage", "imports.run", "workload.view", "approval.final",
        "workload.override", "reports.view", "reports.export", "reports.templates",
        "integrations.view", "integrations.manage", "audit.view",
    })),
    "academic_office": SystemRole("academic_office", "O‘quv bo‘limi", "university", frozenset({
        "settings.view", "dashboard.view", "org.view", "programs.view", "programs.manage",
        "academic_year.view", "academic_year.create", "academic_year.transition",
        "curriculum.view", "curriculum.manage", "curriculum.approve", "subjects.view", "subjects.manage",
        "groups.view", "groups.manage", "teachers.view", "teachers.manage", "imports.run", "imports.pdf",
        "rules.draft", "rules.activate", "workload.view", "workload.calculate", "workload.distribute",
        "workload.submit", "approval.department", "reports.view", "reports.export", "reports.templates",
        "integrations.view", "audit.view",
    })),
    "department_head": SystemRole("department_head", "Kafedra mudiri", "department", frozenset(_KM_VIEW | {
        "workload.view", "workload.distribute", "workload.submit", "reports.view", "reports.export",
        "audit.view", "self.workload.view",
    })),
    "teacher": SystemRole("teacher", "Professor-o‘qituvchi", "self", frozenset({
        "dashboard.view", "academic_year.view", "workload.view", "reports.view", "reports.export",
        "self.workload.view",
    })),
}

SCOPE_TYPES = ("platform", "university", "faculty", "department", "self")


def _validate_catalog() -> None:
    for role in SYSTEM_ROLES.values():
        unknown = role.permissions - PERMISSIONS.keys()
        if unknown:
            raise RuntimeError(f"{role.code} rolida noma’lum ruxsatlar: {sorted(unknown)}")


_validate_catalog()
