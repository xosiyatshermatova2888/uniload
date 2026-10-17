"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { Plus } from "lucide-react"
import { useCallback, useMemo, useState } from "react"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { EntityFormDialog, toBody, type FieldDef } from "@/components/common/entity-form-dialog"
import { NativeSelect } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { RowActions } from "@/components/common/row-actions"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { ActiveBadge } from "@/components/common/status-badge"
import { Button } from "@/components/ui/button"
import { useT } from "@/i18n"
import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useDepartments, useFaculties, useNameMap } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

type Department = Schemas["DepartmentOut"]

export default function DepartmentsPage() {
  const t = useT()
  const { can } = useAuth()
  const manage = can("org.manage")
  const query = useDepartments()
  const faculties = useFaculties()
  const facultyName = useNameMap(faculties.data, useCallback((f: Schemas["FacultyOut"]) => f.name, []))
  const depName = useNameMap(query.data, useCallback((d: Department) => d.name, []))
  const run = useRun(refKeys.departments, refKeys.faculties)
  const [facultyFilter, setFacultyFilter] = useState("")
  const [form, setForm] = useState<{ item?: Department } | null>(null)
  const [removing, setRemoving] = useState<Department | null>(null)

  const data = useMemo(() => (query.data ?? []).filter((d) => !facultyFilter || d.faculty_id === facultyFilter), [query.data, facultyFilter])
  const fields: FieldDef[] = [
    { name: "faculty_id", label: t("departments.faculty"), type: "select", required: true, wide: true,
      options: (faculties.data ?? []).map((f) => ({ value: f.id, label: f.name })) },
    { name: "code", label: t("form.code"), required: true },
    { name: "name", label: t("form.name"), required: true, wide: true },
    { name: "is_active", label: t("form.active"), type: "checkbox" },
  ]

  const columns: ColumnDef<Department, unknown>[] = [
    { accessorKey: "code", header: t("form.code"), cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span> },
    {
      accessorKey: "name", header: t("form.name"),
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.name}</div>
          {row.original.merged_into_id && (
            <div className="text-xs text-muted-foreground">{t("departments.mergedInto")}: {depName.get(row.original.merged_into_id)}</div>
          )}
        </div>
      ),
    },
    { accessorKey: "faculty_id", header: t("departments.faculty"), cell: ({ row }) => facultyName.get(row.original.faculty_id) ?? "—" },
    { accessorKey: "is_active", header: t("common.status"), cell: ({ row }) => <ActiveBadge active={row.original.is_active} /> },
    {
      id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} onDelete={() => setRemoving(row.original)} />,
    },
  ]

  return (
    <>
      <PageHeader title={t("departments.title")} description={t("departments.subtitle")}
        actions={manage && <Button onClick={() => setForm({})}><Plus /> {t("departments.create")}</Button>} />
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable columns={columns} data={data} toolbar={
          <NativeSelect value={facultyFilter} onChange={(e) => setFacultyFilter(e.target.value)} className="w-64">
            <option value="">{t("departments.allFaculties")}</option>
            {(faculties.data ?? []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
          </NativeSelect>
        } />
      )}
      <EntityFormDialog
        open={!!form} onOpenChange={(o) => !o && setForm(null)}
        title={form?.item ? t("departments.edit") : t("departments.create")}
        fields={fields} editing={!!form?.item}
        initial={form?.item
          ? { faculty_id: form.item.faculty_id, code: form.item.code, name: form.item.name, is_active: form.item.is_active }
          : { is_active: true, faculty_id: facultyFilter }}
        onSubmit={(v) => {
          const body = toBody(v) as { faculty_id: string; code: string; name: string; is_active: boolean }
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/departments/{department_id}", { params: { path: { department_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/departments", { body })))
        }}
      />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/departments/{department_id}", { params: { path: { department_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}
