"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { Check, Lock, Plus } from "lucide-react"
import { useState } from "react"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { EntityFormDialog, toBody, type FieldDef } from "@/components/common/entity-form-dialog"
import { RowActions } from "@/components/common/row-actions"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { Button } from "@/components/ui/button"
import { useT } from "@/i18n"
import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useLessonTypes } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

type LessonType = Schemas["LessonTypeOut"]

export default function LessonTypesPage() {
  const t = useT()
  const { can } = useAuth()
  const manage = can("curriculum.manage")
  const query = useLessonTypes()
  const run = useRun(refKeys.lessonTypes)
  const [form, setForm] = useState<{ item?: LessonType } | null>(null)
  const [removing, setRemoving] = useState<LessonType | null>(null)

  const fields: FieldDef[] = [
    { name: "code", label: t("form.code"), required: true, createOnly: true, hint: "a-z, 0-9, _" },
    { name: "sort_order", label: t("lessonTypes.order"), type: "number", min: 0, max: 1000 },
    { name: "name", label: t("form.name"), required: true, wide: true },
    { name: "is_auditorium", label: t("lessonTypes.auditorium"), type: "checkbox" },
    { name: "counts_in_workload", label: t("lessonTypes.counts"), type: "checkbox" },
  ]
  const yes = (v: boolean) => (v ? <Check className="size-4 text-success" /> : <span className="text-muted-foreground">—</span>)

  const columns: ColumnDef<LessonType, unknown>[] = [
    { accessorKey: "code", header: t("form.code"), cell: ({ row }) => <span className="font-mono text-xs">{row.original.code}</span> },
    { accessorKey: "name", header: t("form.name"), cell: ({ row }) => (
      <span className="flex items-center gap-1.5 font-medium">{row.original.name}{row.original.is_system && <Lock className="size-3 opacity-50" aria-label={t("lessonTypes.system")} />}</span>
    ) },
    { accessorKey: "is_auditorium", header: t("lessonTypes.auditorium"), cell: ({ row }) => yes(row.original.is_auditorium) },
    { accessorKey: "counts_in_workload", header: t("lessonTypes.counts"), cell: ({ row }) => yes(row.original.counts_in_workload) },
    { accessorKey: "sort_order", header: t("lessonTypes.order"), cell: ({ row }) => <span className="tabular-nums">{row.original.sort_order}</span> },
    { id: "actions", header: "", enableSorting: false, cell: ({ row }) => manage && (
      <RowActions onEdit={() => setForm({ item: row.original })} onDelete={row.original.is_system ? undefined : () => setRemoving(row.original)} />
    ) },
  ]

  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  return (
    <>
      <p className="mb-4 text-sm text-muted-foreground">{t("lessonTypes.subtitle")}</p>
      <DataTable columns={columns} data={query.data ?? []} searchable={false}
        toolbar={manage && <Button onClick={() => setForm({})}><Plus /> {t("lessonTypes.create")}</Button>} />
      <EntityFormDialog open={!!form} onOpenChange={(o) => !o && setForm(null)} title={form?.item ? form.item.name : t("lessonTypes.create")}
        fields={fields} editing={!!form?.item}
        initial={form?.item ? {
          name: form.item.name, sort_order: String(form.item.sort_order), is_auditorium: form.item.is_auditorium,
          counts_in_workload: form.item.counts_in_workload,
        } : { sort_order: "200", counts_in_workload: true }}
        onSubmit={(v) => {
          const body = toBody(v, ["sort_order"]) as Schemas["LessonTypeIn"]
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/lesson-types/{lesson_type_id}", { params: { path: { lesson_type_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/lesson-types", { body })))
        }} />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/lesson-types/{lesson_type_id}", { params: { path: { lesson_type_id: removing.id } } })), t("ref.deleted"))} />
    </>
  )
}
