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

Faqat demo ma’lumotlar (real shaxsiy ma’lumot yo‘q). Parol — `backend/.env.example` dagi `UNILOAD_SEED_PASSWORD`.

| Rol | Email |
|---|---|
| Super Admin | `superadmin@uniload.example` |
| Universitet Admin | `admin@demo-tu.uniload.example` |
| O‘quv bo‘limi | `oquv@demo-tu.uniload.example` |
| Kafedra mudiri | `kafedra@demo-tu.uniload.example` |
| Professor-o‘qituvchi | `oqituvchi@demo-tu.uniload.example` |

Ikkinchi demo universitet (`demo-pu`) xuddi shu prefikslar bilan — tenant izolyatsiyasini sinash uchun.

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
