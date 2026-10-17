"use client"

import { Lock } from "lucide-react"

import { useT } from "@/i18n"
import { cn } from "@/lib/utils"

const styles: Record<string, string> = {
  draft: "bg-muted text-muted-foreground ring-border",
  approved: "bg-success/12 text-emerald-700 ring-success/25 dark:text-emerald-300",
  archived: "bg-zinc-500/10 text-zinc-600 ring-zinc-500/20 dark:text-zinc-300",
}

export function CurriculumStatusBadge({ status }: { status: string }) {
  const t = useT()
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset", styles[status])}>
      {status !== "draft" && <Lock className="size-3" />}
      {t(`curricula.statuses.${status}`)}
    </span>
  )
}
