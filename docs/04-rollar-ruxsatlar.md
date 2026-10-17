# 4. Foydalanuvchi rollari va ruxsatlar matritsasi

## 4.1. Model

- **Ruxsat (permission)** — atomar huquq kodi: `modul.amal` (masalan `workload.distribute`).
- **Rol** — ruxsatlar to‘plami. 5 ta tizim roli shablon sifatida beriladi; universitet admin ularni nusxalab o‘z rollarini yarata oladi (masalan “Dekanat”, “Prorektor”).
- **Ko‘lam (scope)** — rol qayerda amal qiladi: `platform`, `university`, `faculty:<id>`, `department:<id>`, `self`.
  Bitta foydalanuvchi bir nechta rolga ega bo‘lishi mumkin (masalan, kafedra mudiri ayni paytda professor-o‘qituvchi).
- **Tekshiruv:** `has_permission(user, "workload.distribute", resource)` → foydalanuvchining shu ruxsatni beruvchi rollaridan birining ko‘lami resursni (kafedra → fakultet → universitet ierarxiyasi bo‘yicha) qamrab olishi kerak.
- Tasdiqlash vakolatlari universitet sozlamalaridagi `approval_workflows` orqali moslashtiriladi.

## 4.2. Rollar

| Kod | Rol | Ko‘lam |
|---|---|---|
| `SA` | Super Admin | platform |
| `UA` | Universitet Admin | university |
| `OB` | O‘quv bo‘limi | university (yoki faculty) |
| `KM` | Kafedra mudiri | department |
| `PO` | Professor-o‘qituvchi | self |

> **Super Admin va maxfiylik:** SA universitetlar, tariflar va texnik holatni boshqaradi, lekin universitetning o‘quv ma’lumotlarini **sukut bo‘yicha ko‘rmaydi**. Texnik yordam uchun “support-kirish” universitet admini ruxsati bilan, muddatli (masalan 24 soat) va audit qaydi bilan beriladi.

## 4.3. Ruxsatlar matritsasi

Belgilar: ✅ to‘liq · 🏛 faqat o‘z kafedrasi · 👤 faqat o‘ziga tegishli · 👁 faqat ko‘rish · ⚙️ universitet sozlamasiga bog‘liq · ❌ yo‘q

| Modul / amal | Ruxsat kodi | SA | UA | OB | KM | PO |
|---|---|:-:|:-:|:-:|:-:|:-:|
| Universitetlarni yaratish/boshqarish | `platform.tenants.manage` | ✅ | ❌ | ❌ | ❌ | ❌ |
| Tarif va obunalar | `platform.subscriptions.manage` | ✅ | 👁 | ❌ | ❌ | ❌ |
| Texnik sozlamalar, tizim holati | `platform.system.manage` | ✅ | ❌ | ❌ | ❌ | ❌ |
| Universitet profili va sozlamalari | `settings.manage` | ❌ | ✅ | 👁 | ❌ | ❌ |
| Foydalanuvchilar va rollarni boshqarish | `users.manage` | ✅¹ | ✅ | ❌ | ❌ | ❌ |
| Tasdiqlash zanjirini sozlash | `settings.workflow.manage` | ❌ | ✅ | ❌ | ❌ | ❌ |
| Fakultet / kafedra CRUD | `org.manage` | ❌ | ✅ | 👁 | 👁 | ❌ |
| Ta’lim yo‘nalishlari CRUD | `programs.manage` | ❌ | ✅ | ✅ | 👁 | ❌ |
| O‘quv yilini yaratish / nusxalash | `academic_year.create` | ❌ | ⚙️ | ✅ | ❌ | ❌ |
| O‘quv yili holatini o‘zgartirish | `academic_year.transition` | ❌ | ⚙️ | ✅ | ❌ | ❌ |
| O‘quv yilini arxivlash | `academic_year.archive` | ❌ | ✅ | ⚙️ | ❌ | ❌ |
| O‘quv rejalarini yuklash / tahrirlash | `curriculum.manage` | ❌ | ❌ | ✅ | 👁🏛 | ❌ |
| O‘quv rejasini tasdiqlash (versiya) | `curriculum.approve` | ❌ | ⚙️ | ✅ | ❌ | ❌ |
| Fanlar katalogi | `subjects.manage` | ❌ | ❌ | ✅ | 👁 | ❌ |
| Akademik guruhlar, kontingent, oqimlar | `groups.manage` | ❌ | ❌ | ✅ | 👁 | ❌ |
| O‘qituvchilar va yillik bandlik | `teachers.manage` | ❌ | ✅ | ✅ | 🏛⚙️ | ❌ |
| Excel import | `imports.run` | ❌ | ✅ | ✅ | 🏛⚙️ | ❌ |
| PDF tahlil | `imports.pdf` | ❌ | ❌ | ✅ | ❌ | ❌ |
| Hisoblash qoidasi (qoralama) yaratish | `rules.draft` | ❌ | ❌ | ✅ | ❌ | ❌ |
| Hisoblash qoidasini faollashtirish | `rules.activate` | ❌ | ⚙️ | ⚙️² | ❌ | ❌ |
| Yuklamani hisoblash (ishga tushirish) | `workload.calculate` | ❌ | ❌ | ✅ | ❌ | ❌ |
| Hisoblangan yuklamani ko‘rish | `workload.view` | ❌ | ✅ | ✅ | 🏛 | 👤 |
| Yuklamani taqsimlash | `workload.distribute` | ❌ | ❌ | ✅ | 🏛⚙️ | ❌ |
| Taqsimotni tasdiqlashga yuborish | `workload.submit` | ❌ | ❌ | ✅ | 🏛 | ❌ |
| Kafedra taqsimotini tasdiqlash | `approval.department` | ❌ | ❌ | ✅ | ⚙️ | ❌ |
| Universitet yuklamasini yakuniy tasdiqlash | `approval.final` | ❌ | ⚙️ | ⚙️ | ❌ | ❌ |
| Tasdiqlangan yuklamani o‘zgartirish (override) | `workload.override` | ❌ | ⚙️ | ⚙️ | ❌ | ❌ |
| Hisobotlarni ko‘rish | `reports.view` | ❌ | ✅ | ✅ | 🏛 | 👤 |
| Hisobotlarni eksport qilish (Excel/PDF) | `reports.export` | ❌ | ✅ | ✅ | 🏛 | 👤 |
| Hisobot shablonlarini sozlash | `reports.templates` | ❌ | ✅ | ✅ | ❌ | ❌ |
| ESPOS sozlash va sinxronlash | `integrations.manage` | ❌ | ✅ | 👁 | ❌ | ❌ |
| Audit logni ko‘rish | `audit.view` | ✅¹ | ✅ | 👁 | 🏛 | ❌ |
| O‘z yuklamasi va tarixini ko‘rish | `self.workload.view` | ❌ | ❌ | ❌ | ✅ | ✅ |

¹ Faqat platforma darajasidagi yozuvlar yoki support-kirish davrida.
² Sukut bo‘yicha “ikki kalit” qoidasi: qoidani yaratgan xodim uni o‘zi faollashtira olmaydi.

## 4.4. Muhim cheklovlar

- Har bir yozish amali (`create/update/delete/approve`) ruxsat + ko‘lam + **o‘quv yili holati** bo‘yicha tekshiriladi. Masalan, `workload.distribute` faqat yil `calculated` yoki `distributing` holatida ishlaydi.
- Kafedra mudiri o‘z kafedrasiga tegishli bo‘lmagan `workload_item`ga o‘qituvchi biriktira olmaydi; boshqa kafedra o‘qituvchisini (o‘rindosh) biriktirish ⚙️ sozlamaga bog‘liq.
- O‘z taqsimotini o‘zi tasdiqlash taqiqlanadi (submit qilgan foydalanuvchi shu bosqichni tasdiqlay olmaydi).
- Override har doim: sabab matni + (ixtiyoriy) asoslovchi hujjat + audit + ESPOS’ga yangi revision.
