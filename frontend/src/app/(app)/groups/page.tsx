"use client"

import { useQuery } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { AlertTriangle, Plus, Save } from "lucide-react"
import { useCallback, useMemo, useState } from "react"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { EntityFormDialog, toBody, type FieldDef } from "@/components/common/entity-form-dialog"
import { Field, NativeSelect } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { RowActions } from "@/components/common/row-actions"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { curriculumLabel, useCurricula, useLessonTypes, useNameMap, usePrograms, useSubjects } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"
import { useYear } from "@/lib/year"

type Group = Schemas["GroupOut"]
type Stream = Schemas["StreamOut"]
const LANGS = ["uz", "ru", "en", "kk", "tj", "tk", "kaa"] as const

export default function GroupsPage() {
  const t = useT()
  const { year } = useYear()
  if (!year) return <><PageHeader title={t("groups.title")} /><EmptyState title={t("year.none")} /></>
  return (
    <>
      <PageHeader title={t("groups.title")} description={`${t("groups.subtitle")} · ${year.label}`} />
      {year.is_locked && (
        <Alert className="mb-4"><AlertDescription>{t("year.lockedHint", { status: t(`year.statuses.${year.status}`) })}</AlertDescription></Alert>
      )}
      <Tabs defaultValue="groups">
        <TabsList className="mb-4">
          <TabsTrigger value="groups">{t("groups.list")}</TabsTrigger>
          <TabsTrigger value="streams">{t("groups.streams")}</TabsTrigger>
        </TabsList>
        <TabsContent value="groups"><GroupsTab yearId={year.id} locked={year.is_locked} /></TabsContent>
        <TabsContent value="streams"><StreamsTab yearId={year.id} locked={year.is_locked} /></TabsContent>
      </Tabs>
    </>
  )
}

function GroupsTab({ yearId, locked }: { yearId: string; locked: boolean }) {
  const t = useT()
  const { can } = useAuth()
  const manage = can("groups.manage") && !locked
  const key = ["groups", yearId]
  const query = useQuery({ queryKey: key, queryFn: () => unwrap(api.GET("/api/v1/years/{year_id}/groups", { params: { path: { year_id: yearId } } })) })
  const curricula = useCurricula()
  const programs = usePrograms()
  const programName = useNameMap(programs.data, useCallback((p: Schemas["ProgramOut"]) => p.name, []))
  const curriculumName = useMemo(() => new Map((curricula.data ?? []).map((c) => [c.id, curriculumLabel(c, programName, t)])), [curricula.data, programName, t])
  const run = useRun(key)
  const [course, setCourse] = useState("")
  const [reviewOnly, setReviewOnly] = useState(false)
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [form, setForm] = useState<{ item?: Group } | null>(null)
  const [removing, setRemoving] = useState<Group | null>(null)

  const data = useMemo(() => (query.data ?? []).filter((g) => (!course || g.course === Number(course)) && (!reviewOnly || g.needs_review)), [query.data, course, reviewOnly])
  const reviewCount = (query.data ?? []).filter((g) => g.needs_review).length

  const fields: FieldDef[] = [
    { name: "code", label: t("groups.code"), required: true },
    { name: "course", label: t("groups.course"), type: "number", required: true, min: 1, max: 6 },
    { name: "curriculum_id", label: t("groups.curriculum"), type: "select", required: true, wide: true,
      options: (curricula.data ?? []).filter((c) => c.status !== "archived").map((c) => ({ value: c.id, label: curriculumName.get(c.id) ?? "" })) },
    { name: "language", label: t("groups.language"), type: "select", required: true, options: LANGS.map((l) => ({ value: l, label: t(`groups.languages.${l}`) })) },
    { name: "subgroup_count", label: t("groups.subgroups"), type: "number", min: 1, max: 10 },
    { name: "student_count", label: t("groups.students"), type: "number", min: 0 },
    { name: "budget_count", label: t("groups.budget"), type: "number", min: 0 },
    { name: "contract_count", label: t("groups.contract"), type: "number", min: 0 },
  ]

  const columns: ColumnDef<Group, unknown>[] = [
    { accessorKey: "code", header: t("groups.code"), cell: ({ row }) => (
      <span className="flex items-center gap-1.5 font-medium">
        {row.original.code}
        {row.original.needs_review && <AlertTriangle className="size-3.5 text-warning" aria-label={t("groups.needsReview")} />}
      </span>
    ) },
    { accessorKey: "course", header: t("groups.course"), cell: ({ row }) => <span className="tabular-nums">{row.original.course}</span> },
    { accessorKey: "curriculum_id", header: t("groups.curriculum"), enableSorting: false,
      cell: ({ row }) => <span className="text-xs text-muted-foreground">{curriculumName.get(row.original.curriculum_id) ?? "—"}</span> },
    { accessorKey: "language", header: t("groups.language"), cell: ({ row }) => t(`groups.languages.${row.original.language}`) },
    { accessorKey: "student_count", header: t("groups.students"), cell: ({ row }) => manage ? (
      <Input type="number" min={0} className="h-7 w-20 tabular-nums" value={edits[row.original.id] ?? String(row.original.student_count)}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => setEdits((x) => ({ ...x, [row.original.id]: e.target.value }))} />
    ) : <span className="tabular-nums">{row.original.student_count}</span> },
    { id: "bc", header: `${t("groups.budget")} / ${t("groups.contract")}`, enableSorting: false,
      cell: ({ row }) => <span className="text-muted-foreground tabular-nums">{row.original.budget_count ?? "—"} / {row.original.contract_count ?? "—"}</span> },
    { accessorKey: "subgroup_count", header: t("groups.subgroups"), cell: ({ row }) => <span className="tabular-nums">{row.original.subgroup_count}</span> },
    { id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} onDelete={() => setRemoving(row.original)} /> },
  ]

  const changed = Object.entries(edits).filter(([id, v]) => {
    const g = query.data?.find((x) => x.id === id)
    return g && v !== "" && Number(v) !== g.student_count
  })

  async function saveCounts() {
    const items = changed.map(([id, v]) => {
      const g = query.data!.find((x) => x.id === id)!
      // Umumiy son o‘zgarganda byudjet/kontrakt taqsimoti endi mos kelmaydi — tozalanadi.
      return { id, row_version: g.row_version, student_count: Number(v), budget_count: null, contract_count: null }
    })
    await run(() => unwrap(api.PATCH("/api/v1/years/{year_id}/groups", { params: { path: { year_id: yearId } }, body: { items } })))
    setEdits({})
  }

  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  return (
    <>
      {reviewCount > 0 && (
        <Alert className="mb-3"><AlertTriangle /><AlertDescription>{t("groups.needsReviewHint")} ({reviewCount})</AlertDescription></Alert>
      )}
      <DataTable columns={columns} data={data} toolbar={<>
        <NativeSelect value={course} onChange={(e) => setCourse(e.target.value)} className="w-36">
          <option value="">{t("groups.allCourses")}</option>
          {[1, 2, 3, 4, 5, 6].map((c) => <option key={c} value={c}>{c}-{t("groups.course").toLowerCase()}</option>)}
        </NativeSelect>
        <label className="flex items-center gap-2 text-sm"><Checkbox checked={reviewOnly} onCheckedChange={(v) => setReviewOnly(v === true)} /> {t("groups.needsReview")}</label>
        {manage && changed.length > 0 && <Button variant="outline" onClick={saveCounts}><Save /> {t("groups.saveCounts", { n: changed.length })}</Button>}
        {manage && <Button onClick={() => setForm({})}><Plus /> {t("groups.create")}</Button>}
      </>} />
      <EntityFormDialog open={!!form} onOpenChange={(o) => !o && setForm(null)} title={form?.item ? t("groups.edit") : t("groups.create")}
        fields={fields} editing={!!form?.item}
        initial={form?.item ? {
          code: form.item.code, course: String(form.item.course), curriculum_id: form.item.curriculum_id, language: form.item.language,
          subgroup_count: String(form.item.subgroup_count), student_count: String(form.item.student_count),
          budget_count: form.item.budget_count == null ? "" : String(form.item.budget_count),
          contract_count: form.item.contract_count == null ? "" : String(form.item.contract_count),
        } : { language: "uz", course: "1", subgroup_count: "1", student_count: "0" }}
        onSubmit={(v) => {
          const body = toBody(v, ["course", "subgroup_count", "student_count", "budget_count", "contract_count"]) as Schemas["GroupIn"]
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/years/{year_id}/groups/{group_id}", { params: { path: { year_id: yearId, group_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/years/{year_id}/groups", { params: { path: { year_id: yearId } }, body })))
        }} />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.code }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/years/{year_id}/groups/{group_id}", { params: { path: { year_id: yearId, group_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}

function StreamsTab({ yearId, locked }: { yearId: string; locked: boolean }) {
  const t = useT()
  const { can } = useAuth()
  const manage = can("groups.manage") && !locked
  const key = ["streams", yearId]
  const query = useQuery({ queryKey: key, queryFn: () => unwrap(api.GET("/api/v1/years/{year_id}/streams", { params: { path: { year_id: yearId } } })) })
  const groups = useQuery({ queryKey: ["groups", yearId], queryFn: () => unwrap(api.GET("/api/v1/years/{year_id}/groups", { params: { path: { year_id: yearId } } })) })
  const yearDetail = useQuery({ queryKey: ["academic-year", yearId], queryFn: () => unwrap(api.GET("/api/v1/academic-years/{year_id}", { params: { path: { year_id: yearId } } })) })
  const subjects = useSubjects()
  const lessonTypes = useLessonTypes()
  const subjectName = useNameMap(subjects.data, useCallback((s: Schemas["SubjectOut"]) => `${s.code} ${s.name_uz}`, []))
  const typeName = useNameMap(lessonTypes.data, useCallback((l: Schemas["LessonTypeOut"]) => l.name, []))
  const groupCode = useNameMap(groups.data, useCallback((g: Group) => g.code, []))
  const semesterName = useNameMap(yearDetail.data?.semesters, useCallback((s: Schemas["SemesterOut"]) => s.name, []))
  const run = useRun(key)
  const [creating, setCreating] = useState(false)
  const [removing, setRemoving] = useState<Stream | null>(null)

  const columns: ColumnDef<Stream, unknown>[] = [
    { accessorKey: "name", header: t("groups.streamName"), cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
    { accessorKey: "subject_id", header: t("curricula.subject"), cell: ({ row }) => subjectName.get(row.original.subject_id) ?? "—" },
    { accessorKey: "lesson_type_id", header: t("groups.lessonType"), cell: ({ row }) => typeName.get(row.original.lesson_type_id) ?? "—" },
    { accessorKey: "semester_id", header: t("groups.semester"), cell: ({ row }) => semesterName.get(row.original.semester_id) ?? "—" },
    { id: "groups", header: t("groups.streamGroups"), enableSorting: false,
      cell: ({ row }) => <span className="text-sm">{row.original.group_ids.map((g) => groupCode.get(g)).join(", ")}</span> },
    { accessorKey: "student_count", header: t("groups.students"), cell: ({ row }) => <span className="tabular-nums">{row.original.student_count}</span> },
    { id: "actions", header: "", enableSorting: false, cell: ({ row }) => manage && <RowActions onDelete={() => setRemoving(row.original)} /> },
  ]

  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  return (
    <>
      <DataTable columns={columns} data={query.data ?? []} toolbar={manage && <Button onClick={() => setCreating(true)}><Plus /> {t("groups.streamCreate")}</Button>} />
      {creating && (
        <StreamDialog yearId={yearId} groups={groups.data ?? []} semesters={yearDetail.data?.semesters ?? []}
          subjects={subjects.data ?? []} lessonTypes={lessonTypes.data ?? []} onClose={() => setCreating(false)}
          onCreated={() => run(async () => undefined, t("ref.created"))} />
      )}
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/years/{year_id}/streams/{stream_id}", { params: { path: { year_id: yearId, stream_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}

function StreamDialog({ yearId, groups, semesters, subjects, lessonTypes, onClose, onCreated }: {
  yearId: string
  groups: Group[]
  semesters: Schemas["SemesterOut"][]
  subjects: Schemas["SubjectOut"][]
  lessonTypes: Schemas["LessonTypeOut"][]
  onClose: () => void
  onCreated: () => Promise<unknown>
}) {
  const t = useT()
  const [name, setName] = useState("")
  const [semesterId, setSemesterId] = useState(semesters[0]?.id ?? "")
  const [subjectId, setSubjectId] = useState("")
  const [lessonTypeId, setLessonTypeId] = useState(lessonTypes.find((l) => l.code === "lecture")?.id ?? "")
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function save() {
    setBusy(true)
    setError(null)
    try {
      await unwrap(api.POST("/api/v1/years/{year_id}/streams", {
        params: { path: { year_id: yearId } },
        body: { name, semester_id: semesterId, subject_id: subjectId, lesson_type_id: lessonTypeId, group_ids: [...selected] },
      }))
      await onCreated()
      onClose()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("groups.streamCreate")}</DialogTitle>
          <DialogDescription>{t("groups.streamHint")}</DialogDescription>
        </DialogHeader>
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("groups.streamName")} htmlFor="s-name" className="sm:col-span-2"><Input id="s-name" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label={t("curricula.subject")} htmlFor="s-subj" className="sm:col-span-2">
            <NativeSelect id="s-subj" value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
              <option value="">—</option>
              {subjects.filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name_uz}</option>)}
            </NativeSelect>
          </Field>
          <Field label={t("groups.semester")} htmlFor="s-sem">
            <NativeSelect id="s-sem" value={semesterId} onChange={(e) => setSemesterId(e.target.value)}>
              {semesters.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </NativeSelect>
          </Field>
          <Field label={t("groups.lessonType")} htmlFor="s-lt">
            <NativeSelect id="s-lt" value={lessonTypeId} onChange={(e) => setLessonTypeId(e.target.value)}>
              {lessonTypes.filter((l) => l.is_auditorium).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </NativeSelect>
          </Field>
        </div>
        <p className="pt-1 text-sm font-medium">{t("groups.streamGroups")}</p>
        <div className="grid max-h-56 grid-cols-2 gap-1.5 overflow-y-auto rounded-lg border p-2 sm:grid-cols-3">
          {groups.map((g) => (
            <label key={g.id} className="flex items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-muted">
              <Checkbox checked={selected.has(g.id)} onCheckedChange={(v) => setSelected((s) => {
                const next = new Set(s)
                if (v === true) next.add(g.id)
                else next.delete(g.id)
                return next
              })} />
              {g.code} <span className="text-xs text-muted-foreground">({g.course})</span>
            </label>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>{t("common.cancel")}</Button>
          <Button onClick={save} disabled={busy || !name || !subjectId || !selected.size}>{t("common.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
