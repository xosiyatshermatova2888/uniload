"use client"

import { Lock } from "lucide-react"

import { useT } from "@/i18n"
import { cn } from "@/lib/utils"

const styles: Record<string, string> = {
  draft: "bg-muted text-muted-foreground ring-border",
  calculated: "bg-sky-500/10 text-sky-700 ring-sky-500/20 dark:text-sky-300",
  distributing: "bg-primary/10 text-primary ring-primary/20",
  in_review: "bg-warning/15 text-amber-700 ring-warning/30 dark:text-amber-300",
  approved: "bg-success/12 text-emerald-700 ring-success/25 dark:text-emerald-300",
  archived: "bg-zinc-500/10 text-zinc-600 ring-zinc-500/20 dark:text-zinc-300",
}

export function YearStatusBadge({ status, className }: { status: string; className?: string }) {
  const t = useT()
  const locked = status === "approved" || status === "archived"
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset whitespace-nowrap",
        styles[status] ?? styles.draft,
        className,
      )}
    >
      {locked && <Lock className="size-3" />}
      {t(`year.statuses.${status}`)}
    </span>
  )
}

export function ActiveBadge({ active }: { active: boolean }) {
  const t = useT()
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-xs font-medium",
        active ? "text-emerald-700 dark:text-emerald-300" : "text-muted-foreground",
      )}
    >
      <span className={cn("size-1.5 rounded-full", active ? "bg-success" : "bg-muted-foreground/50")} />
      {active ? t("common.active") : t("common.inactive")}
    </span>
  )
}
