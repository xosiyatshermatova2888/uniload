"use client"

import { AlertTriangle, Inbox, ShieldOff } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useT } from "@/i18n"
import { ApiError } from "@/lib/api/client"

export function EmptyState({ title, description, action }: { title?: string; description?: string; action?: ReactNode }) {
  const t = useT()
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed px-6 py-12 text-center">
      <Inbox className="size-8 text-muted-foreground/60" />
      <p className="font-medium">{title ?? t("common.empty")}</p>
      {description && <p className="max-w-md text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useT()
  const forbidden = error instanceof ApiError && error.status === 403
  const Icon = forbidden ? ShieldOff : AlertTriangle
  const message = forbidden ? t("common.noAccess") : error instanceof Error ? error.message : String(error)
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border px-6 py-12 text-center">
      <Icon className="size-8 text-destructive/70" />
      <p className="max-w-md text-sm">{message}</p>
      {onRetry && !forbidden && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-2">
          {t("common.retry")}
        </Button>
      )}
    </div>
  )
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  )
}
