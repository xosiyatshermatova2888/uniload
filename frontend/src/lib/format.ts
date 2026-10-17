const pad = (n: number) => String(n).padStart(2, "0")

/** ISO sana (YYYY-MM-DD) → DD.MM.YYYY, vaqt zonasi siljishisiz. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  const [y, m, d] = value.slice(0, 10).split("-")
  return `${d}.${m}.${y}`
}

/** ISO vaqt → DD.MM.YYYY HH:MM (foydalanuvchining mahalliy vaqtida). */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—"
  const dt = new Date(value)
  return `${pad(dt.getDate())}.${pad(dt.getMonth() + 1)}.${dt.getFullYear()} ${pad(dt.getHours())}:${pad(dt.getMinutes())}`
}
