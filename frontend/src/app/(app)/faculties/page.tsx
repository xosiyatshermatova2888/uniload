"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { Plus } from "lucide-react"
import { useState } from "react"

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
import { refKeys, useFaculties } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

type Faculty = Schemas["FacultyOut"]

export default function FacultiesPage() {
  const t = useT()
  const { can } = useAuth()
  const manage = can("org.manage")
  const query = useFaculties()
  const run = useRun(refKeys.faculties)
  const [form, setForm] = useState<{ item?: Faculty } | null>(null)
  const [removing, setRemoving] = useState<Faculty | null>(null)

  const fields: FieldDef[] = [
    { name: "code", label: t("form.code"), required: true },
    { name: "name", label: t("form.name"), required: true, wide: true },
    { name: "is_active", label: t("form.active"), type: "checkbox" },
  ]

  const columns: ColumnDef<Faculty, unknown>[] = [
    { accessorKey: "code", header: t("form.code"), cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span> },
    { accessorKey: "name", header: t("form.name"), cell: ({ row }) => <span className="font-medium">{row.original.name}</span> },
    { accessorKey: "departments_count", header: t("faculties.departments"), cell: ({ row }) => <span className="tabular-nums">{row.original.departments_count}</span> },
    { accessorKey: "is_active", header: t("common.status"), cell: ({ row }) => <ActiveBadge active={row.original.is_active} /> },
    {
      id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} onDelete={() => setRemoving(row.original)} />,
    },
  ]

  return (
    <>
      <PageHeader title={t("faculties.title")} description={t("faculties.subtitle")}
        actions={manage && <Button onClick={() => setForm({})}><Plus /> {t("faculties.create")}</Button>} />
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable columns={columns} data={query.data ?? []} />
      )}
      <EntityFormDialog
        open={!!form} onOpenChange={(o) => !o && setForm(null)}
        title={form?.item ? t("faculties.edit") : t("faculties.create")}
        fields={fields} editing={!!form?.item}
        initial={form?.item ? { code: form.item.code, name: form.item.name, is_active: form.item.is_active } : { is_active: true }}
        onSubmit={(v) => {
          const body = toBody(v) as { code: string; name: string; is_active: boolean }
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/faculties/{faculty_id}", { params: { path: { faculty_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/faculties", { body })))
        }}
      />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/faculties/{faculty_id}", { params: { path: { faculty_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}
