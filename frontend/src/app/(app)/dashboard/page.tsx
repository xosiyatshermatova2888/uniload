"use client"

import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, BarChart3, CalendarRange, Clock, Gauge, UserCheck, UserX } from "lucide-react"
import Link from "next/link"

import { PageHeader } from "@/components/common/page-header"
import { StatCard } from "@/components/common/stat-card"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { YearStatusBadge } from "@/components/common/status-badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useT } from "@/i18n"
import { api, unwrap } from "@/lib/api/client"
import { formatDate, formatDateTime } from "@/lib/format"
import { useYear } from "@/lib/year"

const LIFECYCLE = ["draft", "calculated", "distributing", "in_review", "approved", "archived"] as const

export default function DashboardPage() {
  const t = useT()
  const { year, isLoading: yearLoading } = useYear()
  const query = useQuery({
    queryKey: ["dashboard", year?.id],
    queryFn: () => unwrap(api.GET("/api/v1/years/{year_id}/dashboard", { params: { path: { year_id: year!.id } } })),
    enabled: !!year,
  })

  if (yearLoading || (year && query.isLoading)) return <TableSkeleton rows={6} />
  if (!year) {
    return (
      <>
        <PageHeader title={t("dashboard.title")} />
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">
          {t("year.none")}. <Link href="/academic-years" className="text-primary underline">{t("years.create")}</Link>
        </CardContent></Card>
      </>
    )
  }
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const data = query.data!
  const stage = LIFECYCLE.indexOf(data.year.status)
  const hint = t("dashboard.phaseHint")

  return (
    <>
      <PageHeader
        title={t("dashboard.title")}
        description={`${t("year.selector")}: ${data.year.label} · ${formatDate(data.year.starts_on)} — ${formatDate(data.year.ends_on)}`}
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label={t("dashboard.totalHours")} value={data.stats.total_hours} icon={Clock} hint={hint} />
        <StatCard label={t("dashboard.assigned")} value={data.stats.assigned_pct} icon={Gauge} hint={hint} tone="success" />
        <StatCard label={t("dashboard.unassigned")} value={data.stats.unassigned_hours} icon={AlertTriangle} hint={hint} tone="warning" />
        <StatCard label={t("dashboard.overloaded")} value={data.stats.overloaded_teachers} icon={UserX} hint={hint} tone="danger" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">{t("years.lifecycle")}</CardTitle>
            <CardDescription>{data.year.label}</CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="grid grid-cols-3 gap-2 sm:grid-cols-6">
              {LIFECYCLE.map((s, i) => (
                <li key={s} className="flex flex-col gap-2">
                  <div className={`h-1.5 rounded-full ${i <= stage ? "bg-primary" : "bg-muted"}`} />
                  <span className={`text-xs ${i === stage ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                    {t(`year.statuses.${s}`)}
                  </span>
                </li>
              ))}
            </ol>
            <div className="mt-6 flex min-h-40 flex-col items-center justify-center gap-2 rounded-lg border border-dashed text-center">
              <BarChart3 className="size-6 text-muted-foreground/60" />
              <p className="text-sm font-medium">{t("dashboard.byDepartment")}</p>
              <p className="max-w-sm text-xs text-muted-foreground">{t("dashboard.byDepartmentEmpty")}</p>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-4">
            <StatCard label={t("dashboard.activeUsers")} value={data.stats.active_users} icon={UserCheck} />
            <StatCard label={t("dashboard.years")} value={data.stats.academic_years} icon={CalendarRange} />
          </div>
          <Card>
            <CardHeader><CardTitle className="text-base">{t("dashboard.warnings")}</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              {data.warnings.length ? data.warnings.map((w) => (
                <div key={w} className="flex gap-2 rounded-lg bg-warning/10 p-3 text-sm">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" />
                  <span>{w}</span>
                </div>
              )) : <p className="text-sm text-muted-foreground">—</p>}
              <div className="pt-1"><YearStatusBadge status={data.year.status} /></div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card className="mt-4">
        <CardHeader><CardTitle className="text-base">{t("dashboard.activity")}</CardTitle></CardHeader>
        <CardContent>
          {data.recent_activity.length ? (
            <ul className="divide-y">
              {data.recent_activity.map((a, i) => (
                <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                  <span>
                    <span className="font-medium">{a.actor_name ?? "—"}</span>{" "}
                    <span className="text-muted-foreground">
                      {t(`audit.${a.action}`).startsWith("audit.") ? a.action : t(`audit.${a.action}`)}
                    </span>
                  </span>
                  <span className="text-xs text-muted-foreground tabular-nums">{formatDateTime(a.occurred_at)}</span>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted-foreground">{t("dashboard.noActivity")}</p>}
        </CardContent>
      </Card>
    </>
  )
}
