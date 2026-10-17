"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { Plus } from "lucide-react"
import { useRouter } from "next/navigation"
import { useCallback, useMemo, useState } from "react"

import { CurriculumStatusBadge } from "@/components/common/curriculum-status"
import { DataTable } from "@/components/common/data-table"
import { EntityFormDialog, toBody, type FieldDef } from "@/components/common/entity-form-dialog"
import { NativeSelect } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { Button } from "@/components/ui/button"
import { useT } from "@/i18n"
import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useCurricula, useNameMap, usePrograms, type Curriculum } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

const FORMS = ["full_time", "part_time", "evening", "distance"] as const

export default function CurriculaPage() {
  const t = useT()
  const router = useRouter()
  const { can } = useAuth()
  const query = useCurricula()
  const programs = usePrograms()
  const programName = useNameMap(programs.data, useCallback((p: Schemas["ProgramOut"]) => `${p.code} ${p.name}`, []))
  const run = useRun(refKeys.curricula)
  const [status, setStatus] = useState("")
  const [creating, setCreating] = useState(false)
  const data = useMemo(() => (query.data ?? []).filter((c) => !status || c.status === status), [query.data, status])

  const fields: FieldDef[] = [
    { name: "education_program_id", label: t("curricula.program"), type: "select", required: true, wide: true,
      options: (programs.data ?? []).filter((p) => p.is_active).map((p) => ({ value: p.id, label: `${p.code} — ${p.name}` })) },
    { name: "education_form", label: t("curricula.form"), type: "select", required: true,
      options: FORMS.map((f) => ({ value: f, label: t(`curricula.forms.${f}`) })) },
    { name: "admission_year", label: t("curricula.admissionYear"), type: "number", required: true, min: 2000, max: 2100 },
    { name: "title", label: t("curricula.titleField"), wide: true },
  ]

  const columns: ColumnDef<Curriculum, unknown>[] = [
    { accessorKey: "education_program_id", header: t("curricula.program"),
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{programName.get(row.original.education_program_id) ?? "—"}</div>
          {row.original.title && <div className="text-xs text-muted-foreground">{row.original.title}</div>}
        </div>
      ) },
    { accessorKey: "admission_year", header: t("curricula.admissionYear"), cell: ({ row }) => <span className="tabular-nums">{row.original.admission_year}</span> },
    { accessorKey: "education_form", header: t("curricula.form"), cell: ({ row }) => t(`curricula.forms.${row.original.education_form}`) },
    { accessorKey: "version", header: t("curricula.version"), cell: ({ row }) => <span className="tabular-nums">v{row.original.version}</span> },
    { accessorKey: "subjects_count", header: t("curricula.subjects"), cell: ({ row }) => <span className="tabular-nums">{row.original.subjects_count}</span> },
    { accessorKey: "total_credits", header: t("curricula.credits"), cell: ({ row }) => <span className="tabular-nums">{row.original.total_credits ?? "—"}</span> },
    { accessorKey: "status", header: t("common.status"), cell: ({ row }) => <CurriculumStatusBadge status={row.original.status} /> },
  ]

  return (
    <>
      <PageHeader title={t("curricula.title")} description={t("curricula.subtitle")}
        actions={can("curriculum.manage") && <Button onClick={() => setCreating(true)}><Plus /> {t("curricula.create")}</Button>} />
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable columns={columns} data={data} onRowClick={(c) => router.push(`/curricula/${c.id}`)} toolbar={
          <NativeSelect value={status} onChange={(e) => setStatus(e.target.value)} className="w-44">
            <option value="">{t("form.all")}</option>
            {(["draft", "approved", "archived"] as const).map((s) => <option key={s} value={s}>{t(`curricula.statuses.${s}`)}</option>)}
          </NativeSelect>
        } />
      )}
      <EntityFormDialog open={creating} onOpenChange={setCreating} title={t("curricula.create")} fields={fields}
        initial={{ education_form: "full_time", admission_year: String(new Date().getFullYear()) }}
        onSubmit={async (v) => {
          const created = await run(() => unwrap(api.POST("/api/v1/curricula", {
            body: toBody(v, ["admission_year"]) as Schemas["CurriculumIn"],
          })), t("ref.created"))
          router.push(`/curricula/${created.id}`)
        }} />
    </>
  )
}
