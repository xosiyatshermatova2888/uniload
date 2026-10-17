"use client"

import { useQuery } from "@tanstack/react-query"
import { Archive, ArrowLeft, CheckCircle2, Copy, Lock, Pencil, Plus, Trash2 } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { use, useCallback, useMemo, useState } from "react"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { CurriculumStatusBadge } from "@/components/common/curriculum-status"
import { Field, NativeSelect } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableFooter, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useDepartments, useLessonTypes, useNameMap, usePrograms, useSubjects } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

type Entry = Schemas["CurriculumSubjectOut"]

const n = (v: string | number | null | undefined) => (v == null ? 0 : Number(v))
const fmt = (v: number) => (v ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : "")

export default function CurriculumDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const t = useT()
  const router = useRouter()
  const { can } = useAuth()
  const key = ["curriculum", id]
  const query = useQuery({
    queryKey: key,
    queryFn: () => unwrap(api.GET("/api/v1/curricula/{curriculum_id}", { params: { path: { curriculum_id: id } } })),
  })
  const programs = usePrograms()
  const lessonTypes = useLessonTypes()
  const departments = useDepartments()
  const depName = useNameMap(departments.data, useCallback((d: Schemas["DepartmentOut"]) => d.code, []))
  const run = useRun(key, refKeys.curricula)
  const [entryForm, setEntryForm] = useState<{ entry?: Entry } | null>(null)
  const [removing, setRemoving] = useState<Entry | null>(null)
  const [action, setAction] = useState<"approve" | "version" | "archive" | null>(null)
  const [approvalDoc, setApprovalDoc] = useState("")

  const c = query.data
  const usedTypes = useMemo(() => {
    const codes = new Set((c?.subjects ?? []).flatMap((s) => Object.keys(s.hours)))
    return (lessonTypes.data ?? []).filter((lt) => codes.has(lt.code))
  }, [c, lessonTypes.data])
  const bySemester = useMemo(() => {
    const map = new Map<number, Entry[]>()
    for (const s of c?.subjects ?? []) map.set(s.semester_no, [...(map.get(s.semester_no) ?? []), s])
    return [...map.entries()].sort(([a], [b]) => a - b)
  }, [c])

  if (query.isLoading) return <TableSkeleton rows={8} />
  if (query.error || !c) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const program = programs.data?.find((p) => p.id === c.education_program_id)
  const editable = c.status === "draft" && can("curriculum.manage")

  return (
    <>
      <Link href="/curricula" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {t("curricula.title")}
      </Link>
      <PageHeader
        title={program ? `${program.code} ${program.name}` : t("curricula.title")}
        description={`${t("curricula.admissionYear")}: ${c.admission_year} · ${t(`curricula.forms.${c.education_form}`)} · v${c.version}${c.title ? ` · ${c.title}` : ""}`}
        actions={<>
          <CurriculumStatusBadge status={c.status} />
          {editable && <Button variant="outline" onClick={() => setEntryForm({})}><Plus /> {t("curricula.addSubject")}</Button>}
          {c.status === "draft" && can("curriculum.approve") && (
            <Button onClick={() => { setApprovalDoc(c.approval_doc ?? ""); setAction("approve") }}><CheckCircle2 /> {t("curricula.approve")}</Button>
          )}
          {c.status !== "draft" && can("curriculum.manage") && <Button variant="outline" onClick={() => setAction("version")}><Copy /> {t("curricula.newVersion")}</Button>}
          {c.status === "approved" && can("curriculum.approve") && <Button variant="outline" onClick={() => setAction("archive")}><Archive /> {t("curricula.archive")}</Button>}
        </>}
      />

      {c.status !== "draft" && (
        <Alert className="mb-4"><Lock /><AlertDescription>
          {t("curricula.lockedHint")}{c.approval_doc ? ` ${t("curricula.approvalDoc")}: ${c.approval_doc}` : ""}
        </AlertDescription></Alert>
      )}

      {!c.subjects.length ? <EmptyState title={t("curricula.empty")} /> : (
        <div className="grid gap-4">
          {bySemester.map(([semester, entries]) => {
            const totals = c.totals_by_semester[String(semester)] ?? {}
            return (
              <Card key={semester} className="gap-0 py-0">
                <CardHeader className="border-b py-3"><CardTitle className="text-sm">{t("curricula.semester", { n: semester })}</CardTitle></CardHeader>
                <CardContent className="overflow-x-auto p-0">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-24">{t("form.code")}</TableHead>
                        <TableHead>{t("curricula.subject")}</TableHead>
                        <TableHead>{t("curricula.department")}</TableHead>
                        <TableHead className="text-right">{t("curricula.credits")}</TableHead>
                        {usedTypes.map((lt) => <TableHead key={lt.code} className="text-right">{lt.name}</TableHead>)}
                        <TableHead className="text-right">{t("curricula.total")}</TableHead>
                        <TableHead>{t("curricula.control")}</TableHead>
                        {editable && <TableHead />}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {entries.map((e) => {
                        const sum = Object.values(e.hours).reduce((a, h) => a + n(h), 0)
                        return (
                          <TableRow key={e.id}>
                            <TableCell className="font-mono text-xs">{e.subject_code}</TableCell>
                            <TableCell className="font-medium">{e.subject_name}{e.is_elective && <span className="ml-1 text-xs text-muted-foreground">({t("curricula.elective")})</span>}</TableCell>
                            <TableCell className="text-muted-foreground">{depName.get(e.department_id)}</TableCell>
                            <TableCell className="text-right tabular-nums">{e.credits ?? "—"}</TableCell>
                            {usedTypes.map((lt) => <TableCell key={lt.code} className="text-right tabular-nums">{fmt(n(e.hours[lt.code]))}</TableCell>)}
                            <TableCell className="text-right font-medium tabular-nums">{fmt(sum)}</TableCell>
                            <TableCell>{t(`curricula.controls.${e.control_type}`)}</TableCell>
                            {editable && (
                              <TableCell className="text-right whitespace-nowrap">
                                <Button variant="ghost" size="icon-sm" onClick={() => setEntryForm({ entry: e })} aria-label={t("common.edit")}><Pencil /></Button>
                                <Button variant="ghost" size="icon-sm" onClick={() => setRemoving(e)} aria-label={t("common.delete")}><Trash2 /></Button>
                              </TableCell>
                            )}
                          </TableRow>
                        )
                      })}
                    </TableBody>
                    <TableFooter>
                      <TableRow>
                        <TableCell colSpan={3}>{t("curricula.total")}</TableCell>
                        <TableCell className="text-right tabular-nums">{fmt(entries.reduce((a, e) => a + n(e.credits), 0))}</TableCell>
                        {usedTypes.map((lt) => <TableCell key={lt.code} className="text-right tabular-nums">{fmt(n(totals[lt.code]))}</TableCell>)}
                        <TableCell className="text-right tabular-nums">{fmt(Object.values(totals).reduce((a, h) => a + n(h), 0))}</TableCell>
                        <TableCell colSpan={editable ? 2 : 1} />
                      </TableRow>
                    </TableFooter>
                  </Table>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {entryForm && (
        <EntryDialog curriculum={c} entry={entryForm.entry} lessonTypes={lessonTypes.data ?? []} onClose={() => setEntryForm(null)}
          onSaved={() => run(async () => undefined)} />
      )}
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.subject_name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/curricula/{curriculum_id}/subjects/{entry_id}", {
          params: { path: { curriculum_id: id, entry_id: removing.id } },
        })), t("ref.deleted"))} />
      <ConfirmDialog open={action === "approve"} onOpenChange={(o) => !o && setAction(null)} title={t("curricula.approve")}
        description={t("curricula.approveConfirm")} confirmDisabled={approvalDoc.trim().length < 3}
        onConfirm={() => run(() => unwrap(api.POST("/api/v1/curricula/{curriculum_id}/approve", {
          params: { path: { curriculum_id: id } }, body: { row_version: c.row_version, approval_doc: approvalDoc },
        })))}>
        <Field label={t("curricula.approvalDoc")} htmlFor="approval-doc" hint={t("curricula.approvalDocHint")}>
          <Input id="approval-doc" value={approvalDoc} onChange={(e) => setApprovalDoc(e.target.value)} />
        </Field>
      </ConfirmDialog>
      <ConfirmDialog open={action === "version"} onOpenChange={(o) => !o && setAction(null)} title={t("curricula.newVersion")}
        description={t("curricula.newVersionConfirm")}
        onConfirm={async () => {
          const created = await run(() => unwrap(api.POST("/api/v1/curricula/{curriculum_id}/new-version", { params: { path: { curriculum_id: id } } })), t("ref.created"))
          router.push(`/curricula/${created.id}`)
        }} />
      <ConfirmDialog open={action === "archive"} onOpenChange={(o) => !o && setAction(null)} title={t("curricula.archive")} destructive
        onConfirm={() => run(() => unwrap(api.POST("/api/v1/curricula/{curriculum_id}/archive", {
          params: { path: { curriculum_id: id } }, body: { row_version: c.row_version },
        })))} />
    </>
  )
}

function EntryDialog({ curriculum, entry, lessonTypes, onClose, onSaved }: {
  curriculum: Schemas["CurriculumDetailOut"]
  entry?: Entry
  lessonTypes: Schemas["LessonTypeOut"][]
  onClose: () => void
  onSaved: () => Promise<unknown>
}) {
  const t = useT()
  const subjects = useSubjects()
  const departments = useDepartments()
  const [subjectId, setSubjectId] = useState(entry?.subject_id ?? "")
  const [semester, setSemester] = useState(String(entry?.semester_no ?? 1))
  const [credits, setCredits] = useState(entry?.credits ?? "")
  const [departmentId, setDepartmentId] = useState(entry?.department_id ?? "")
  const [control, setControl] = useState<Entry["control_type"]>(entry?.control_type ?? "exam")
  const [elective, setElective] = useState(entry?.is_elective ?? false)
  const [hours, setHours] = useState<Record<string, string>>(
    Object.fromEntries(Object.entries(entry?.hours ?? {}).map(([k, v]) => [k, String(Number(v))])))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const semesters = Array.from({ length: curriculum.duration_years * 2 }, (_, i) => i + 1)

  async function save() {
    setBusy(true)
    setError(null)
    const hoursBody = Object.fromEntries(Object.entries(hours).filter(([, v]) => v !== "" && Number(v) > 0))
    const common = {
      semester_no: Number(semester), credits: credits === "" ? null : String(credits), control_type: control,
      is_elective: elective, hours: hoursBody, department_id: departmentId || null,
    }
    try {
      if (entry) {
        await unwrap(api.PATCH("/api/v1/curricula/{curriculum_id}/subjects/{entry_id}", {
          params: { path: { curriculum_id: curriculum.id, entry_id: entry.id } },
          body: { ...common, row_version: entry.row_version, department_id: departmentId || undefined },
        }))
      } else {
        await unwrap(api.POST("/api/v1/curricula/{curriculum_id}/subjects", {
          params: { path: { curriculum_id: curriculum.id } }, body: { ...common, subject_id: subjectId, elective_group: null },
        }))
      }
      await onSaved()
      onClose()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-xl">
        <DialogHeader><DialogTitle>{entry ? t("curricula.editSubject") : t("curricula.addSubject")}</DialogTitle></DialogHeader>
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("curricula.subject")} htmlFor="e-subject" className="sm:col-span-2">
            <NativeSelect id="e-subject" value={subjectId} disabled={!!entry} onChange={(e) => setSubjectId(e.target.value)}>
              <option value="">—</option>
              {(subjects.data ?? []).filter((s) => s.is_active || s.id === subjectId).map((s) => (
                <option key={s.id} value={s.id}>{s.code} — {s.name_uz}</option>
              ))}
            </NativeSelect>
          </Field>
          <Field label={t("curricula.semesterNo")} htmlFor="e-sem">
            <NativeSelect id="e-sem" value={semester} onChange={(e) => setSemester(e.target.value)}>
              {semesters.map((s) => <option key={s} value={s}>{t("curricula.semester", { n: s })}</option>)}
            </NativeSelect>
          </Field>
          <Field label={t("curricula.credits")} htmlFor="e-credits">
            <Input id="e-credits" type="number" min={0} step="0.5" value={String(credits)} onChange={(e) => setCredits(e.target.value)} />
          </Field>
          <Field label={t("curricula.department")} htmlFor="e-dep" hint={t("curricula.departmentHint")}>
            <NativeSelect id="e-dep" value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
              <option value="">—</option>
              {(departments.data ?? []).filter((d) => d.is_active || d.id === departmentId).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </NativeSelect>
          </Field>
          <Field label={t("curricula.control")} htmlFor="e-control">
            <NativeSelect id="e-control" value={control} onChange={(e) => setControl(e.target.value as Entry["control_type"])}>
              {(["exam", "credit_test", "none"] as const).map((k) => <option key={k} value={k}>{t(`curricula.controls.${k}`)}</option>)}
            </NativeSelect>
          </Field>
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <Checkbox checked={elective} onCheckedChange={(v) => setElective(v === true)} /> {t("curricula.elective")}
          </label>
        </div>
        <p className="pt-2 text-sm font-medium">{t("curricula.hours")}</p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {lessonTypes.map((lt) => (
            <Field key={lt.code} label={lt.name} htmlFor={`h-${lt.code}`}>
              <Input id={`h-${lt.code}`} type="number" min={0} step="0.5" value={hours[lt.code] ?? ""}
                onChange={(e) => setHours((h) => ({ ...h, [lt.code]: e.target.value }))} className="tabular-nums" />
            </Field>
          ))}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={busy}>{t("common.cancel")}</Button>
          <Button onClick={save} disabled={busy || !subjectId}>{t("common.save")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
