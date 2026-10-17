"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { Plus } from "lucide-react"
import { useCallback, useState } from "react"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { EntityFormDialog, toBody, type FieldDef } from "@/components/common/entity-form-dialog"
import { PageHeader } from "@/components/common/page-header"
import { RowActions } from "@/components/common/row-actions"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { ActiveBadge } from "@/components/common/status-badge"
import { Button } from "@/components/ui/button"
import { useT } from "@/i18n"
import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useDepartments, useNameMap, usePrograms } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

type Program = Schemas["ProgramOut"]
type ProgramBody = Schemas["ProgramIn"]

export default function ProgramsPage() {
  const t = useT()
  const { can } = useAuth()
  const manage = can("programs.manage")
  const query = usePrograms()
  const departments = useDepartments()
  const depName = useNameMap(departments.data, useCallback((d: Schemas["DepartmentOut"]) => d.name, []))
  const run = useRun(refKeys.programs)
  const [form, setForm] = useState<{ item?: Program } | null>(null)
  const [removing, setRemoving] = useState<Program | null>(null)

  const fields: FieldDef[] = [
    { name: "code", label: t("programs.code"), required: true, placeholder: "60610600" },
    { name: "degree", label: t("programs.degree"), type: "select", required: true,
      options: [{ value: "bachelor", label: t("programs.degrees.bachelor") }, { value: "master", label: t("programs.degrees.master") }] },
    { name: "name", label: t("form.name"), required: true, wide: true },
    { name: "department_id", label: t("programs.department"), type: "select", required: true, wide: true,
      options: (departments.data ?? []).filter((d) => d.is_active).map((d) => ({ value: d.id, label: d.name })) },
    { name: "duration_years", label: t("programs.duration"), type: "number", required: true, min: 1, max: 6 },
    { name: "is_active", label: t("form.active"), type: "checkbox" },
  ]

  const columns: ColumnDef<Program, unknown>[] = [
    { accessorKey: "code", header: t("programs.code"), cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span> },
    { accessorKey: "name", header: t("form.name"), cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
    { accessorKey: "degree", header: t("programs.degree"), cell: ({ row }) => t(`programs.degrees.${row.original.degree}`) },
    { accessorKey: "duration_years", header: t("programs.duration"), cell: ({ row }) => <span className="tabular-nums">{row.original.duration_years}</span> },
    { accessorKey: "department_id", header: t("programs.department"), cell: ({ row }) => depName.get(row.original.department_id) ?? "—" },
    { accessorKey: "is_active", header: t("common.status"), cell: ({ row }) => <ActiveBadge active={row.original.is_active} /> },
    {
      id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} onDelete={() => setRemoving(row.original)} />,
    },
  ]

  return (
    <>
      <PageHeader title={t("programs.title")} description={t("programs.subtitle")}
        actions={manage && <Button onClick={() => setForm({})}><Plus /> {t("programs.create")}</Button>} />
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable columns={columns} data={query.data ?? []} />
      )}
      <EntityFormDialog
        open={!!form} onOpenChange={(o) => !o && setForm(null)}
        title={form?.item ? t("programs.edit") : t("programs.create")}
        fields={fields} editing={!!form?.item}
        initial={form?.item ? {
          code: form.item.code, name: form.item.name, degree: form.item.degree, department_id: form.item.department_id,
          duration_years: String(form.item.duration_years), is_active: form.item.is_active,
        } : { degree: "bachelor", duration_years: "4", is_active: true }}
        onSubmit={(v) => {
          const body = toBody(v, ["duration_years"]) as ProgramBody
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/programs/{program_id}", { params: { path: { program_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/programs", { body })))
        }}
      />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/programs/{program_id}", { params: { path: { program_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}
