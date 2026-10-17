"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, ArrowRight, Lock, Pencil, Star, Undo2 } from "lucide-react"
import Link from "next/link"
import { use, useState } from "react"
import { toast } from "sonner"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { Field } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { YearStatusBadge } from "@/components/common/status-badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { formatDate, formatDateTime } from "@/lib/format"
import { yearsQueryKey } from "@/lib/year"

type YearStatus = Schemas["AcademicYearOut"]["status"]
type SemesterIn = Schemas["SemesterIn"]

const ORDER: YearStatus[] = ["draft", "calculated", "distributing", "in_review", "approved", "archived"]
const BACKWARD = new Set(["calculated>draft", "distributing>calculated", "in_review>distributing"])
const PERMISSION: Partial<Record<YearStatus, string>> = { approved: "approval.final", archived: "academic_year.archive" }

export default function AcademicYearDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const t = useT()
  const { can } = useAuth()
  const queryClient = useQueryClient()
  const key = ["academic-year", id]
  const query = useQuery({
    queryKey: key,
    queryFn: () => unwrap(api.GET("/api/v1/academic-years/{year_id}", { params: { path: { year_id: id } } })),
  })
  const history = useQuery({
    queryKey: ["audit", "academic_year", id],
    queryFn: () => unwrap(api.GET("/api/v1/audit-logs", {
      params: { query: { entity_type: "academic_year", entity_id: id, size: 20 } },
    })),
    enabled: can("audit.view"),
  })

  const [target, setTarget] = useState<YearStatus | null>(null)
  const [comment, setComment] = useState("")
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<SemesterIn[]>([])

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: key }),
      queryClient.invalidateQueries({ queryKey: yearsQueryKey }),
      queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["audit", "academic_year", id] }),
    ])
  }

  const onError = (e: unknown) => toast.error(e instanceof ApiError ? e.message : String(e))

  const transition = useMutation({
    mutationFn: (to: YearStatus) => unwrap(api.POST("/api/v1/academic-years/{year_id}/transitions", {
      params: { path: { year_id: id } },
      body: { to, comment: comment || null, row_version: query.data!.row_version },
    })),
    onSuccess: async () => {
      toast.success(t("years.transitionDone"))
      setComment("")
      await refresh()
    },
    onError,
  })

  const setCurrent = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/academic-years/{year_id}/set-current", { params: { path: { year_id: id } } })),
    onSuccess: refresh,
    onError,
  })

  const saveSemesters = useMutation({
    mutationFn: () => unwrap(api.PUT("/api/v1/years/{year_id}/semesters", {
      params: { path: { year_id: id } }, body: { semesters: draft },
    })),
    onSuccess: async () => {
      toast.success(t("common.saved"))
      setEditing(false)
      await refresh()
    },
    onError,
  })

  if (query.isLoading) return <TableSkeleton rows={6} />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const year = query.data!
  const stage = ORDER.indexOf(year.status)
  const canEdit = can("academic_year.create") && !year.is_locked
  const backward = target ? BACKWARD.has(`${year.status}>${target}`) : false

  return (
    <>
      <Link href="/academic-years" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {t("years.title")}
      </Link>
      <PageHeader
        title={`${t("years.label")} ${year.label}`}
        description={`${formatDate(year.starts_on)} — ${formatDate(year.ends_on)}${year.source_label ? ` · ${t("years.source")}: ${year.source_label}` : ""}`}
        actions={
          <>
            <YearStatusBadge status={year.status} className="self-center text-sm" />
            {!year.is_current && can("academic_year.create") && year.status !== "archived" && (
              <Button variant="outline" onClick={() => setCurrent.mutate()} disabled={setCurrent.isPending}>
                <Star /> {t("years.setCurrent")}
              </Button>
            )}
          </>
        }
      />

      {year.is_locked && (
        <Alert className="mb-4">
          <Lock />
          <AlertTitle>{t("year.locked")}</AlertTitle>
          <AlertDescription>{t("year.lockedHint", { status: t(`year.statuses.${year.status}`) })}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">{t("years.lifecycle")}</CardTitle></CardHeader>
          <CardContent>
            <ol className="flex flex-wrap items-center gap-2">
              {ORDER.map((s, i) => (
                <li key={s} className="flex items-center gap-2">
                  <span className={`flex size-6 items-center justify-center rounded-full text-xs font-semibold ${
                    i < stage ? "bg-primary/15 text-primary" : i === stage ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                    {i + 1}
                  </span>
                  <span className={`text-sm ${i === stage ? "font-semibold" : "text-muted-foreground"}`}>{t(`year.statuses.${s}`)}</span>
                  {i < ORDER.length - 1 && <ArrowRight className="size-3.5 text-muted-foreground/50" />}
                </li>
              ))}
            </ol>
            <div className="mt-5">
              <p className="mb-2 text-sm font-medium">{t("years.allowedActions")}</p>
              {year.allowed_transitions.length ? (
                <div className="flex flex-wrap gap-2">
                  {year.allowed_transitions.map((to) => {
                    const back = BACKWARD.has(`${year.status}>${to}`)
                    const permission = PERMISSION[to] ?? "academic_year.transition"
                    return (
                      <Button key={to} variant={back ? "outline" : "default"} disabled={!can(permission)}
                        title={!can(permission) ? permission : undefined}
                        onClick={() => { setComment(""); setTarget(to) }}>
                        {back ? <Undo2 /> : <ArrowRight />} {t(`year.transitionsTo.${to}`)}
                      </Button>
                    )
                  })}
                </div>
              ) : <p className="text-sm text-muted-foreground">{t("years.noActions")}</p>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">{t("years.history")}</CardTitle></CardHeader>
          <CardContent>
            {!can("audit.view") ? <p className="text-sm text-muted-foreground">{t("common.noAccess")}</p> : (
              <ul className="space-y-3">
                {(history.data?.items ?? []).map((h) => (
                  <li key={h.id} className="border-l-2 border-primary/30 pl-3 text-sm">
                    <p className="font-medium">
                      {t(`audit.${h.action}`).startsWith("audit.") ? h.action : t(`audit.${h.action}`)}
                      {h.action === "academic_year.status_changed" && h.after && (
                        <span className="font-normal text-muted-foreground">
                          {" "}— {t(`year.statuses.${String(h.before?.status)}`)} → {t(`year.statuses.${String(h.after.status)}`)}
                        </span>
                      )}
                    </p>
                    {h.reason && <p className="text-muted-foreground">“{h.reason}”</p>}
                    <p className="text-xs text-muted-foreground tabular-nums">{formatDateTime(h.occurred_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">{t("years.semesters")}</CardTitle>
          {canEdit && !editing && (
            <CardAction>
              <Button variant="outline" size="sm" onClick={() => {
                setDraft(year.semesters.map(({ term, name, starts_on, ends_on, weeks }) => ({ term: term as 1 | 2, name, starts_on, ends_on, weeks })))
                setEditing(true)
              }}><Pencil /> {t("years.editSemesters")}</Button>
            </CardAction>
          )}
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("years.semesterName")}</TableHead>
                  <TableHead>{t("years.startsOn")}</TableHead>
                  <TableHead>{t("years.endsOn")}</TableHead>
                  <TableHead>{t("years.weeks")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {editing ? draft.map((s, i) => {
                  const update = (patch: Partial<SemesterIn>) => setDraft((d) => d.map((x, j) => (j === i ? { ...x, ...patch } : x)))
                  return (
                    <TableRow key={s.term}>
                      <TableCell><Input value={s.name} onChange={(e) => update({ name: e.target.value })} /></TableCell>
                      <TableCell><Input type="date" value={s.starts_on} onChange={(e) => update({ starts_on: e.target.value })} /></TableCell>
                      <TableCell><Input type="date" value={s.ends_on} onChange={(e) => update({ ends_on: e.target.value })} /></TableCell>
                      <TableCell><Input type="number" min={1} max={30} className="w-24" value={s.weeks ?? ""}
                        onChange={(e) => update({ weeks: e.target.value ? Number(e.target.value) : null })} /></TableCell>
                    </TableRow>
                  )
                }) : year.semesters.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell className="tabular-nums">{formatDate(s.starts_on)}</TableCell>
                    <TableCell className="tabular-nums">{formatDate(s.ends_on)}</TableCell>
                    <TableCell className="tabular-nums">{s.weeks ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {editing && (
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditing(false)}>{t("common.cancel")}</Button>
              <Button onClick={() => saveSemesters.mutate()} disabled={saveSemesters.isPending}>{t("common.save")}</Button>
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={target !== null}
        onOpenChange={(o) => !o && setTarget(null)}
        title={target ? t(`year.transitionsTo.${target}`) : ""}
        description={target ? t("years.transitionConfirm", {
          label: year.label, from: t(`year.statuses.${year.status}`), to: t(`year.statuses.${target}`),
        }) : undefined}
        destructive={target === "archived"}
        confirmDisabled={backward && !comment.trim()}
        onConfirm={() => target && transition.mutateAsync(target)}
      >
        <Field label={t("years.comment")} htmlFor="transition-comment" hint={backward ? t("years.commentRequired") : undefined}>
          <Textarea id="transition-comment" value={comment} onChange={(e) => setComment(e.target.value)} rows={3} />
        </Field>
      </ConfirmDialog>
    </>
  )
}
