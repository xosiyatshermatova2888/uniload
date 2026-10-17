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
import { refKeys, useDepartments, useNameMap, useSubjects } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

type Subject = Schemas["SubjectOut"]
type SubjectBody = Schemas["SubjectIn"]

export default function SubjectsPage() {
  const t = useT()
  const { can } = useAuth()
  const manage = can("subjects.manage")
  const query = useSubjects()
  const departments = useDepartments()
  const depName = useNameMap(departments.data, useCallback((d: Schemas["DepartmentOut"]) => d.name, []))
  const run = useRun(refKeys.subjects)
  const [depFilter, setDepFilter] = useState("")
  const [form, setForm] = useState<{ item?: Subject } | null>(null)
  const [removing, setRemoving] = useState<Subject | null>(null)
  const data = useMemo(() => (query.data ?? []).filter((s) => !depFilter || s.default_department_id === depFilter), [query.data, depFilter])

  const fields: FieldDef[] = [
    { name: "code", label: t("form.code"), required: true },
    { name: "default_department_id", label: t("subjects.department"), type: "select",
      options: (departments.data ?? []).filter((d) => d.is_active).map((d) => ({ value: d.id, label: d.name })) },
    { name: "name_uz", label: t("subjects.nameUz"), required: true, wide: true },
    { name: "name_ru", label: t("subjects.nameRu"), wide: true },
    { name: "name_en", label: t("subjects.nameEn"), wide: true },
    { name: "is_active", label: t("form.active"), type: "checkbox" },
  ]

  const columns: ColumnDef<Subject, unknown>[] = [
    { accessorKey: "code", header: t("form.code"), cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span> },
    { accessorKey: "name_uz", header: t("form.name"), cell: ({ row }) => <span className="font-medium">{row.original.name_uz}</span> },
    { accessorKey: "default_department_id", header: t("subjects.department"),
      cell: ({ row }) => (row.original.default_department_id ? depName.get(row.original.default_department_id) : "—") },
    { accessorKey: "is_active", header: t("common.status"), cell: ({ row }) => <ActiveBadge active={row.original.is_active} /> },
    {
      id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} onDelete={() => setRemoving(row.original)} />,
    },
  ]

  return (
    <>
      <PageHeader title={t("subjects.title")} description={t("subjects.subtitle")}
        actions={manage && <Button onClick={() => setForm({})}><Plus /> {t("subjects.create")}</Button>} />
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable columns={columns} data={data} toolbar={
          <NativeSelect value={depFilter} onChange={(e) => setDepFilter(e.target.value)} className="w-64">
            <option value="">{t("form.all")}</option>
            {(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </NativeSelect>
        } />
      )}
      <EntityFormDialog
        open={!!form} onOpenChange={(o) => !o && setForm(null)}
        title={form?.item ? t("subjects.edit") : t("subjects.create")}
        fields={fields} editing={!!form?.item}
        initial={form?.item ? {
          code: form.item.code, name_uz: form.item.name_uz, name_ru: form.item.name_ru ?? "", name_en: form.item.name_en ?? "",
          default_department_id: form.item.default_department_id ?? "", is_active: form.item.is_active,
        } : { is_active: true, default_department_id: depFilter }}
        onSubmit={(v) => {
          const body = toBody(v) as SubjectBody
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/subjects/{subject_id}", { params: { path: { subject_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/subjects", { body })))
        }}
      />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.name_uz }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/subjects/{subject_id}", { params: { path: { subject_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}
