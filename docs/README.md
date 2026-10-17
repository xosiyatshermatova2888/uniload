# UniLoad — Academic Workload Management System

O‘zbekiston oliy ta’lim muassasalari uchun o‘quv yuklamalarini shakllantirish, taqsimlash, tasdiqlash va arxivlash platformasi (multi-tenant SaaS).

**Hujjat holati:** arxitektura loyihasi, tasdiqlash kutilmoqda · 2026-10-17

| # | Hujjat | Mazmuni |
|---|---|---|
| 1 | [Umumiy arxitektura](01-arxitektura.md) | Komponentlar, Clean Architecture qatlamlari, repozitoriya tuzilmasi, tenant va yil izolyatsiyasi, audit, backup |
| 2 | [Modullar](02-modullar.md) | 21 ta modul, bog‘liqliklar, bosqichlar |
| 3 | [ER model](03-er-model.md) | ER diagrammalar, barcha jadvallar: kalitlar, cheklovlar, indekslar, triggerlar |
| 4 | [Rollar va ruxsatlar](04-rollar-ruxsatlar.md) | 5 rol, ko‘lamlar, ruxsatlar matritsasi |
| 5 | [O‘quv yilini yaratish](05-oquv-yili-algoritmi.md) | Holatlar diagrammasi, nusxalash ustasi, algoritm, yillarni solishtirish |
| 6 | [Hisoblash va taqsimlash](06-hisoblash-taqsimlash.md) | BPMN flowchart, Rules Engine, PDF asosida formulalarni aniqlash, taqsimot validatsiyalari |
| 7 | [Frontend](07-frontend.md) | Layout, umumiy komponentlar, barcha sahifalar |
| 8 | [API endpointlar](08-api-endpointlar.md) | REST konvensiyalari va endpointlar ro‘yxati |
| 9 | [ESPOS kontrakti](09-espos-kontrakti.md) | Adapter, outbox, payload, idempotentlik, savollar |
| 10 | [MVP rejasi](10-mvp-reja.md) | 5 bosqich, qabul mezonlari, **tasdiqlash uchun savollar** |

## Asosiy qarorlar qisqacha

- **Modulli monolit** (FastAPI) + alohida Next.js frontend + Celery worker.
- **Tenant izolyatsiyasi 3 qatlamda:** JWT konteksti → repository filtri → PostgreSQL RLS; kompozit FK’lar.
- **O‘quv yillari mustaqil:** yangi yil = yangi qatorlar; o‘quv rejalari versiyalanadi; hisoblash natijasi snapshot; tasdiqlangan yil DB trigger bilan qulflanadi.
- **Hisoblash faqat Rules Engine orqali:** versiyali qoidalar, xavfsiz DSL, har bir soat uchun izoh. Haqiqiy formulalar PDF va me’yoriy hujjatlar tahlilidan keyin, golden testlar bilan tasdiqlanib kiritiladi.
- **ESPOS:** adapter + mock + outbox; `record_key` + `revision` orqali dublikatsiz sinxronlash.
