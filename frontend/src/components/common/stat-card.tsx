import type { LucideIcon } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface StatCardProps {
  label: string
  value: string | number | null | undefined
  icon: LucideIcon
  hint?: string
  tone?: "default" | "warning" | "danger" | "success"
}

const tones = {
  default: "bg-primary/10 text-primary",
  success: "bg-success/12 text-success",
  warning: "bg-warning/15 text-warning",
  danger: "bg-destructive/10 text-destructive",
}

/** `value === null` — ko‘rsatkich hali hisoblanmagan: soxta 0 o‘rniga “—” va izoh ko‘rsatiladi. */
export function StatCard({ label, value, icon: Icon, hint, tone = "default" }: StatCardProps) {
  const missing = value === null || value === undefined
  return (
    <Card className="gap-0 py-0">
      <CardContent className="flex items-start gap-4 p-5">
        <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-lg", tones[tone])}>
          <Icon className="size-5" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm text-muted-foreground">{label}</p>
          <p className={cn("mt-1 text-2xl font-semibold tabular-nums", missing && "text-muted-foreground/60")}>
            {missing ? "—" : value}
          </p>
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
      </CardContent>
    </Card>
  )
}
