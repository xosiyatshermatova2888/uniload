# UniLoad — Academic Workload Management System

O‘zbekiston oliy ta’lim muassasalari uchun o‘quv yuklamalarini shakllantirish, taqsimlash va tasdiqlash platformasi (multi-tenant SaaS).

- Arxitektura va reja: [docs/README.md](docs/README.md)
- **Joriy holat: 2-bosqich** — 1-bosqich (auth, RBAC, tenantlar, o‘quv yillari) + fakultetlar, kafedralar, ta’lim yo‘nalishlari, fanlar, o‘quv rejalari (versiyalash), akademik guruhlar va oqimlar, professor-o‘qituvchilar, yillik bandlik, lavozim me’yorlari, o‘quv yilini nusxalash (kursni ko‘tarish bilan).

## Tuzilma

```
backend/    FastAPI + SQLAlchemy 2 + Alembic (Python 3.11+)
frontend/   Next.js 15 + React 19 + Tailwind 4 + shadcn/ui (Base UI)
docker/     PostgreSQL init skriptlari (ilova roli)
docs/       Arxitektura hujjatlari
```

## Ishga tushirish (Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- API / Swagger: http://localhost:8000/docs

`api` konteyneri ishga tushganda migratsiyalar, `bootstrap` (ruxsatlar, tizim rollari, tariflar) va demo `seed` avtomatik bajariladi.

## Ishga tushirish (Docker’siz)

PostgreSQL 16 (port 5433) va `docker/postgres/init/01-roles.sql` dagi rollar kerak.

```bash
cd backend && python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
```

```bash
cd backend && .venv/Scripts/alembic upgrade head && .venv/Scripts/python -m app.cli bootstrap && .venv/Scripts/python -m app.cli seed
```

```bash
cd backend && .venv/Scripts/uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install --legacy-peer-deps && npm run dev
```

## Demo foydalanuvchilar

Tizimga **login va parol** bilan kiriladi (email ixtiyoriy — faqat parolni tiklash uchun). Faqat demo ma’lumotlar,
real shaxsiy ma’lumot yo‘q. Parol — `backend/.env.example` dagi `UNILOAD_SEED_PASSWORD`.

| Rol | Login |
|---|---|
| Super Admin | `superadmin` |
| Universitet Admin | `admin.tu` |
| O‘quv bo‘limi | `oquv.tu` |
| Kafedra mudiri (DI kafedrasi) | `kafedra.tu` |
| Professor-o‘qituvchi | `oqituvchi.tu` |

Ikkinchi demo universitet uchun xuddi shu loginlar `.pu` bilan (`oquv.pu`, `admin.pu`, …) — tenant izolyatsiyasini sinash uchun.

## Testlar

Testlar alohida `uniload_test` bazasida ishlaydi va har safar sxemani noldan quradi.

```bash
cd backend && .venv/Scripts/python -m pytest
```

```bash
cd frontend && npm run typecheck && npm run lint
```

Backend API o‘zgarsa, frontend tiplarini yangilash: `npm run gen:api` (backend virtual muhiti faollashtirilgan holda).

## Xavfsizlik bo‘yicha asosiy qarorlar

- Tenant izolyatsiyasi 3 qatlamda: JWT konteksti → servisdagi filtr → PostgreSQL RLS (ilova `uniload_app` roli bilan, `BYPASSRLS`siz ulanadi). Kompozit FK’lar yilni boshqa tenantga bog‘lashni DB darajasida taqiqlaydi.
- Tasdiqlangan/arxivlangan o‘quv yili DB triggeri bilan qulflanadi; o‘zgartirish faqat `app.override_reason` bilan (4-bosqichda maxsus ruxsat va audit orqali).
- Access token faqat xotirada; refresh token `httpOnly` + `SameSite=Strict` cookie’da, rotatsiya va qayta ishlatishni aniqlash bilan.
- Audit log faqat qo‘shiladi (ilova roliga `UPDATE/DELETE` berilmagan).
