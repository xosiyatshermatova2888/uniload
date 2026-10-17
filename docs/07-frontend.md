# 7. Frontend sahifalari va komponentlari

## 7.1. Umumiy layout

```
┌───────────────┬───────────────────────────────────────────────────────────┐
│  UniLoad      │ [O‘quv yili: 2026–2027 ▾] [Holat: Taqsimlanmoqda]  🔔 🌓 UZ 👤 │
│               ├───────────────────────────────────────────────────────────┤
│ ▣ Boshqaruv   │  Breadcrumb / Sahifa sarlavhasi            [Asosiy amal]  │
│ 📅 O‘quv yil. │                                                           │
│ 🏛 Fakultetlar │   kontent                                                 │
│ ...           │                                                           │
│ ⚙ Sozlamalar  │                                                           │
└───────────────┴───────────────────────────────────────────────────────────┘
```

- **YearSwitcher** — global tanlangan o‘quv yili (URL’da `?year=` emas, yo‘l segmentida yoki cookie’da saqlanadi). Barcha yilga bog‘liq sahifalar shu yil bo‘yicha ishlaydi; arxiv yil tanlansa — sariq “Faqat o‘qish rejimi” banneri.
- Sidebar menyusi foydalanuvchi ruxsatlari bo‘yicha filtrlanadi (PO faqat “Mening yuklamam”, “Hisobotlar”ni ko‘radi).
- Mavzu: oq/och kulrang fon, asosiy rang to‘q ko‘k (`--primary: 222 64% 28%`), shadcn tokenlari orqali Light/Dark.

## 7.2. Umumiy komponentlar (`components/common`)

| Komponent | Vazifasi |
|---|---|
| `AppSidebar`, `Topbar`, `YearSwitcher`, `ThemeToggle`, `LocaleSwitcher`, `UserMenu` | Layout |
| `DataTable` | TanStack Table: server pagination, saralash, filtr, ustun ko‘rinishi, qator tanlash, inline edit, Excel eksport |
| `StatCard`, `TrendBadge`, `ProgressStat` | Dashboard kartalari |
| `ConfirmDialog` | Barcha muhim amallar uchun (o‘chirish, holat o‘tishi, tasdiqlash) — xavfli amalda nom yozib tasdiqlash |
| `FormSheet` / `FormDialog` | React Hook Form + Zod; yon panelda yaratish/tahrirlash |
| `StatusBadge`, `YearStatusStepper` | Holatlar |
| `FileDropzone`, `ImportWizard` | Import oqimi |
| `AuditTimeline` | Yozuv tarixi |
| `EmptyState`, `ErrorState`, `PageSkeleton` | Holatlar |
| `PermissionGate` | Ruxsat bo‘lmasa elementni yashiradi |
| `HoursInput` | 2 kasr aniqlikdagi soat maydoni |

## 7.3. Sahifalar

| # | Sidebar | Yo‘l | Asosiy komponentlar | Bosqich |
|---|---|---|---|---|
| — | Kirish | `/login`, `/forgot-password`, `/reset-password` | `LoginForm`, `PasswordResetForm` | 1 |
| 1 | Boshqaruv paneli | `/dashboard` | `StatCard` ×4 (jami soat, taqsimlangan %, taqsimlanmagan soat, ortiqcha yuklamali o‘qituvchilar), `DepartmentLoadChart` (Recharts bar), `YearStatusStepper`, `WarningsList`, `RecentActivity` | 1 |
| 2 | O‘quv yillari | `/academic-years` | `DataTable`, `CreateYearWizard` (4 qadam: yil → rejim → nimalarni ko‘chirish → ko‘rib chiqish), `CopyJobProgress` | 1 |
| | | `/academic-years/[id]` | `YearStatusStepper`, `TransitionActions`, `SemesterEditor`, `CopyReport`, `AuditTimeline` | 1 |
| | | `/academic-years/[id]/compare` | `YearCompareView` (fanlar, soatlar, kontingent, yuklama Δ) | 3 |
| 3 | Fakultetlar | `/faculties` | `DataTable`, `FacultyForm` | 2 |
| 4 | Kafedralar | `/departments`, `/departments/[id]` | `DataTable`, `DepartmentForm`, `DepartmentTeachersTab`, `DepartmentWorkloadTab` | 2 |
| 5 | Ta’lim yo‘nalishlari | `/programs` | `DataTable`, `ProgramForm` | 2 |
| 6 | O‘quv rejalari | `/curricula` | `DataTable` (yo‘nalish, shakl, qabul yili, versiya, holat) | 2 |
| | | `/curricula/[id]` | `CurriculumGrid` (semestrlar × fanlar × mashg‘ulot turlari soatlari), `CurriculumVersionBar`, `CreateNewVersionDialog` | 2 |
| | | `/curricula/import` | `ImportWizard` (fayl → ustunlarni moslashtirish → xatolar → ko‘rish → tasdiq) | 3 |
| 7 | Fanlar | `/subjects` | `DataTable`, `SubjectForm`, `SubjectUsageDrawer` | 2 |
| 8 | Akademik guruhlar | `/groups` | `DataTable` (inline kontingent tahriri, `needs_review` filtr), `GroupForm`, `BulkCountEditor` | 2 |
| | | `/groups/streams` | `StreamBuilder` (guruhlarni oqimga sudrab qo‘shish) | 2 |
| 9 | Professor-o‘qituvchilar | `/teachers` | `DataTable`, `TeacherForm` | 2 |
| | | `/teachers/[id]` | `TeacherProfile`, `EmploymentTable` (yil bo‘yicha), `WorkloadHistoryChart`, `AssignmentsTab` | 2 / 3 |
| 10 | Yuklamalarni shakllantirish | `/workload/calculation` | `CalculationRunPanel`, `RunHistoryTable`, `WorkloadItemsTable`, `CalcTraceDrawer` (“bu soat qanday hisoblandi”), `ValidationErrorsList` | 3 |
| | | `/workload/rules`, `/workload/rules/[id]` | `RulesTable`, `RuleEditor` (shartlar, formula muharriri sintaksis tekshiruvi bilan), `RuleSandbox` (test ma’lumotda sinash), `RuleVersionHistory` | 3 |
| | | `/workload/rule-candidates` | `CandidateReviewTable` (PDF’dan topilgan gipotezalar) | 3/4 |
| 11 | Yuklamalarni taqsimlash | `/workload/distribution` | **`DistributionBoard`**: chapda `WorkloadItemsPanel` (fan, tur, jami/taqsimlangan/qolgan, filtrlar), o‘ngda `TeachersPanel` (lavozim, stavka, me’yor, biriktirilgan, bo‘sh hajm progress-bar); dnd-kit; `AssignHoursDialog`; `ValidationPanel`; `SuggestionsDrawer`; `TableModeToggle` | 3 |
| 12 | Tasdiqlash | `/approvals`, `/approvals/[id]` | `ApprovalInbox`, `ApprovalDetail` (taqsimot snapshot, farqlar), `ApproveRejectDialog` (izoh majburiy), `ApprovalTimeline`, `OverrideRequestDialog` | 4 |
| 13 | Hisobotlar | `/reports`, `/reports/[code]` | `ReportCatalog` (9 hisobot), `ReportFilters`, `ReportViewer`, `ExportMenu` (Excel/PDF), `ReportJobStatus` | 4 |
| 14 | ESPOS integratsiyasi | `/integrations/espos` | `ConnectionSettings`, `MappingTable` (o‘qituvchi ↔ ESPOS ID), `SyncQueueTable`, `EventDetailDrawer`, `RetryButton` | 5 |
| 15 | Sozlamalar | `/settings/university` | `UniversityProfileForm`, `CalendarSettings`, `RoundingSettings` | 1 |
| | | `/settings/users`, `/settings/roles` | `UsersTable`, `InviteUserDialog`, `RoleEditor` (ruxsat matritsasi katakchalari), `ScopePicker` | 1 |
| | | `/settings/norms` | `PositionNormsTable` (yil bo‘yicha) | 2 |
| | | `/settings/lesson-types` | `LessonTypesTable` | 2 |
| | | `/settings/workflow` | `ApprovalWorkflowEditor` | 4 |
| | | `/settings/imports` | `ImportHistoryTable` | 3 |
| | | `/settings/audit` | `AuditLogTable` (filtr: foydalanuvchi, obyekt, sana) | 4 |
| — | Mening yuklamam (PO) | `/me/workload` | `MyWorkloadSummary`, `MyAssignmentsTable`, `MyHistoryChart` | 3 |
| — | Platforma (SA) | `/platform/universities`, `/platform/subscriptions`, `/platform/plans`, `/platform/health` | `TenantsTable`, `CreateTenantWizard`, `SubscriptionForm` | 1 (minimal) / 5 |

## 7.4. Frontend tamoyillari

- Har bir modul `features/<modul>/` ichida: `api.ts` (TanStack Query hook’lari), `schemas.ts` (Zod — backend Pydantic bilan mos), `components/`.
- Formalar validatsiyasi frontend’da (Zod) **va** backend’da (Pydantic) — frontend faqat qulaylik uchun.
- Barcha matnlar `i18n/uz.json`’da; komponentlarda qattiq yozilgan o‘zbekcha matn bo‘lmaydi.
- Katta jadvallar (minglab bo‘laklar) — server pagination + virtualizatsiya.
- Accessibility: klaviatura bilan drag-and-drop, kontrast WCAG AA.
