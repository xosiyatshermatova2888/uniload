# 8. Backend API endpointlari

## 8.1. Konvensiyalar

- Asosiy yo‘l: `/api/v1`. OpenAPI: `/api/v1/openapi.json`, Swagger UI: `/docs`.
- **Yilga bog‘liq resurslar yo‘lda yil bilan:** `/api/v1/years/{year_id}/groups` — so‘rov tanasida yil ID’si qabul qilinmaydi, aralashib ketish ehtimoli yo‘q.
- Ro‘yxatlar: `?page=1&size=50&sort=-created_at&q=...&filter[department_id]=...` → `{items, total, page, size}`.
- Xatolar: RFC 7807 `application/problem+json` — `{type, title, status, code, detail, errors[]}`; `code` (masalan `YEAR_LOCKED`) frontend’da tarjima qilinadi.
- Tahrirlash: `PATCH` tanasida `row_version` → mos kelmasa `409 CONCURRENT_UPDATE` (optimistik qulf).
- Uzoq amallar: `202 Accepted` + `{job_id}` → `GET /jobs/{job_id}`.
- Takroriy so‘rovdan himoya: `Idempotency-Key` sarlavhasi (yil yaratish, import commit, hisoblash).
- Boshqa tenant resursi → har doim `404` (mavjudligini oshkor qilmaslik uchun).

## 8.2. Endpointlar

### Auth
| Metod | Yo‘l | Tavsif |
|---|---|---|
| POST | `/auth/login` | Email + parol → access token, refresh cookie |
| POST | `/auth/refresh` | Refresh rotatsiyasi |
| POST | `/auth/logout` | Sessiyani bekor qilish |
| POST | `/auth/password/forgot` · `/auth/password/reset` | Parolni tiklash |
| GET | `/auth/me` | Joriy foydalanuvchi, rollar, ruxsatlar, universitet |
| POST | `/auth/password/change` | Parolni almashtirish |

### Platforma (Super Admin)
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/POST | `/platform/universities` | Ro‘yxat / yaratish (birinchi admin taklifi bilan) |
| GET/PATCH | `/platform/universities/{id}` | Ko‘rish / tahrirlash, bloklash |
| GET/POST | `/platform/plans` | Tariflar |
| GET/POST/PATCH | `/platform/universities/{id}/subscriptions` | Obunalar |
| POST | `/platform/universities/{id}/support-access` | Muddatli support-kirish so‘rovi |
| GET | `/platform/health` | Tizim holati |

### Universitet, foydalanuvchilar, rollar
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/PATCH | `/university` | O‘z universiteti profili va sozlamalari |
| GET/POST | `/users` | Ro‘yxat / taklif qilish |
| GET/PATCH/DELETE | `/users/{id}` | Tahrirlash, bloklash (o‘chirish = deaktivatsiya) |
| PUT | `/users/{id}/roles` | Rollar va ko‘lamlarni belgilash |
| GET/POST | `/roles` · GET/PATCH/DELETE `/roles/{id}` | Rollar |
| GET | `/permissions` | Ruxsatlar katalogi |

### Dashboard
| GET | `/years/{year_id}/dashboard` | Kartalar, grafiklar, ogohlantirishlar (Redis kesh) |
|---|---|---|

### O‘quv yillari
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET | `/academic-years` | Ro‘yxat |
| POST | `/academic-years` | Yaratish: `{start_year, mode: "empty"\|"copy", source_year_id, options}` → `202 {job_id}` |
| POST | `/academic-years/preview` | Nusxalash oldindan ko‘rish (hech narsa yozmaydi) |
| GET/PATCH | `/academic-years/{id}` | Ko‘rish / sana, nom tahriri |
| POST | `/academic-years/{id}/transitions` | `{to: "distributing", comment}` — holat o‘tishi |
| POST | `/academic-years/{id}/set-current` | Joriy yil qilish |
| GET | `/academic-years/{id}/compare?with={id}` | Yillarni solishtirish |
| GET/PUT | `/years/{year_id}/semesters` | Semestrlar |
| GET/PUT | `/years/{year_id}/position-norms` | Lavozim me’yorlari |
| GET | `/jobs/{job_id}` | Fon vazifasi holati |

### Tashkiliy tuzilma va yo‘nalishlar
| Metod | Yo‘l |
|---|---|
| GET/POST, GET/PATCH/DELETE | `/faculties`, `/faculties/{id}` |
| GET/POST, GET/PATCH/DELETE | `/departments`, `/departments/{id}` |
| GET/POST, GET/PATCH/DELETE | `/programs`, `/programs/{id}` |

### Fanlar va o‘quv rejalari
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/POST, GET/PATCH/DELETE | `/subjects`, `/subjects/{id}` | Fanlar katalogi |
| GET/POST, GET/PATCH/DELETE | `/lesson-types`, `/lesson-types/{id}` | Mashg‘ulot turlari |
| GET/POST | `/curricula` | Ro‘yxat / yaratish |
| GET/PATCH | `/curricula/{id}` | Faqat `draft` holatda tahrir |
| POST | `/curricula/{id}/approve` | Versiyani tasdiqlash |
| POST | `/curricula/{id}/new-version` | Tasdiqlangan rejadan yangi qoralama versiya |
| GET/POST | `/curricula/{id}/subjects` | Reja fanlari |
| PATCH/DELETE | `/curricula/{id}/subjects/{cs_id}` | Fan va soatlar (`hours: {lecture: 30, practice: 30, ...}`) |

### Guruhlar va oqimlar (yilga bog‘liq)
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/POST | `/years/{year_id}/groups` | Ro‘yxat / yaratish |
| GET/PATCH/DELETE | `/years/{year_id}/groups/{id}` | |
| PATCH | `/years/{year_id}/groups:bulk` | Kontingentni ommaviy yangilash |
| GET/POST, PATCH/DELETE | `/years/{year_id}/streams`, `/years/{year_id}/streams/{id}` | Oqimlar va ularning guruhlari |

### O‘qituvchilar
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/POST, GET/PATCH | `/teachers`, `/teachers/{id}` | Profil (tenant darajasi) |
| GET | `/teachers/{id}/history` | Yillar bo‘yicha bandlik va yuklama tarixi |
| GET/POST | `/years/{year_id}/employment` | Yillik bandlik |
| PATCH/DELETE | `/years/{year_id}/employment/{id}` | |

### Import
| Metod | Yo‘l | Tavsif |
|---|---|---|
| POST | `/imports` | Fayl yuklash + `import_type` → `job_id` |
| GET | `/imports` · `/imports/{id}` | Tarix va holat |
| GET | `/imports/{id}/columns` | Aniqlangan ustunlar + taklif qilingan moslik |
| PUT | `/imports/{id}/mapping` | Ustunlar mosligini saqlash → validatsiya |
| GET | `/imports/{id}/rows?status=invalid` | Oldindan ko‘rish va xatolar |
| PATCH | `/imports/{id}/rows/{row_no}` | Qatorni qo‘lda tuzatish |
| POST | `/imports/{id}/commit` | Importni tasdiqlash (tranzaksiya) |
| POST | `/imports/{id}/cancel` | Bekor qilish |
| GET | `/imports/{id}/rule-candidates` | PDF’dan topilgan gipotezalar |
| POST | `/rule-candidates/{id}/convert` · `/reject` | Qoralama qoidaga aylantirish / rad etish |

### Hisoblash qoidalari
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/POST | `/rules` | Ro‘yxat / qoralama yaratish |
| GET/PATCH | `/rules/{id}` | Faqat `draft`/`testing` tahrirlanadi |
| POST | `/rules/validate-formula` | Formula sintaksis va o‘zgaruvchilarni tekshirish |
| POST | `/rules/{id}/test` | Sandbox: berilgan kontekst yoki golden to‘plamda sinash |
| POST | `/rules/{id}/activate` · `/retire` | Faollashtirish (ikki kalit) / to‘xtatish |
| POST | `/rules/{id}/new-version` | Yangi versiya |

### Yuklamani hisoblash
| Metod | Yo‘l | Tavsif |
|---|---|---|
| POST | `/years/{year_id}/calculations` | Hisoblashni boshlash `{scope_type, scope_id, dry_run}` → `202` |
| GET | `/years/{year_id}/calculations` · `/{calc_id}` | Yugurishlar tarixi, natija, xatolar |
| GET | `/years/{year_id}/workload-items` | Bo‘laklar (filtr: kafedra, fan, tur, semestr, `unassigned=true`) |
| GET | `/years/{year_id}/workload-items/{id}/trace` | Hisoblash izohi |
| POST | `/years/{year_id}/golden-tests/run` | Hisoblashni PDF natijalari bilan solishtirish |

### Taqsimlash
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET | `/years/{year_id}/distribution/board?department_id=` | Taqsimot oynasi uchun yig‘ma ma’lumot (bo‘laklar + o‘qituvchilar + yuklama) |
| POST | `/years/{year_id}/assignments` | Biriktirish `{workload_item_id, teacher_employment_id, hours}` |
| PATCH/DELETE | `/years/{year_id}/assignments/{id}` | Soatni o‘zgartirish / olib tashlash |
| POST | `/years/{year_id}/assignments:batch` | Bir nechta o‘zgarish atomik |
| GET | `/years/{year_id}/distribution/validate?department_id=` | Validatsiya hisoboti |
| GET | `/years/{year_id}/distribution/suggestions?department_id=` | Oldingi yil / greedy tavsiyalari |
| POST | `/years/{year_id}/departments/{dep_id}/submit` | Tasdiqlashga yuborish |

### Tasdiqlash
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET | `/approvals?status=pending&mine=true` | Kiruvchi |
| GET | `/approvals/{id}` | Tafsilot va snapshot |
| POST | `/approvals/{id}/approve` · `/reject` · `/return` | Qaror (`comment` majburiy rad/qaytarishda) |
| GET/PUT | `/settings/approval-workflows` | Zanjirni sozlash |
| POST | `/years/{year_id}/overrides` | Tasdiqlangan yuklamani o‘zgartirish so‘rovi (sabab, hujjat) |

### Hisobotlar
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET | `/reports` | Katalog |
| GET | `/years/{year_id}/reports/{code}` | JSON ko‘rinishda (`code`: `university_total`, `by_faculty`, `by_department`, `by_teacher`, `by_subject`, `by_semester`, `unassigned`, `overload`, `year_comparison`) |
| POST | `/years/{year_id}/reports/{code}/export` | `{format: "xlsx"\|"pdf", template_id}` → `202 {job_id}` |
| GET | `/files/{id}/download` | Imzolangan, muddatli havola |
| GET/POST/PATCH | `/report-templates` | Universitet shablonlari |

### Professor-o‘qituvchi
| GET | `/me/workload?year_id=` · `/me/history` | O‘z yuklamasi va tarixi |
|---|---|---|

### ESPOS integratsiyasi
| Metod | Yo‘l | Tavsif |
|---|---|---|
| GET/PUT | `/integrations/espos/settings` | Ulanish sozlamalari (mock / real) |
| POST | `/integrations/espos/test-connection` | Ulanishni tekshirish |
| GET/PUT | `/integrations/espos/mappings` | Ichki ID ↔ ESPOS ID |
| POST | `/years/{year_id}/integrations/espos/sync` | Tasdiqlangan yuklamani navbatga qo‘yish |
| GET | `/integrations/espos/events?status=` | Outbox jurnali |
| POST | `/integrations/espos/events/{id}/retry` | Qayta urinish |
| POST | `/integrations/espos/webhook` | ESPOS’dan tasdiqnoma (HMAC imzo bilan) |

### Audit
| GET | `/audit-logs?entity_type=&entity_id=&user_id=&from=&to=` | Jurnal |
|---|---|---|
