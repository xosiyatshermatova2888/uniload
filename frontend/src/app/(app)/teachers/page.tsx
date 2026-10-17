"use client"

import { useQuery } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { Plus } from "lucide-react"
import { useRouter } from "next/navigation"
import { useCallback, useMemo, useState } from "react"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { EntityFormDialog, toBody, type FieldDef } from "@/components/common/entity-form-dialog"
import { teacherFields, teacherInitial } from "@/features/teachers/form"
import { NativeSelect } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { RowActions } from "@/components/common/row-actions"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states"
import { ActiveBadge } from "@/components/common/status-badge"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useT } from "@/i18n"
import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useDepartments, useNameMap, useTeacherCatalog, useTeachers } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"
import { useYear } from "@/lib/year"

type Teacher = Schemas["TeacherOut"]
type Employment = Schemas["EmploymentOut"]

export default function TeachersPage() {
  const t = useT()
  const { year } = useYear()
  return (
    <>
      <PageHeader title={t("teachers.title")} description={t("teachers.subtitle")} />
      <Tabs defaultValue="employment">
        <TabsList className="mb-4">
          <TabsTrigger value="employment">{t("teachers.employment", { year: year?.label ?? "—" })}</TabsTrigger>
          <TabsTrigger value="list">{t("teachers.list")}</TabsTrigger>
        </TabsList>
        <TabsContent value="employment">{year ? <EmploymentTab year={year} /> : <EmptyState title={t("year.none")} />}</TabsContent>
        <TabsContent value="list"><TeachersTab /></TabsContent>
      </Tabs>
    </>
  )
}

function TeachersTab() {
  const t = useT()
  const router = useRouter()
  const { can } = useAuth()
  const manage = can("teachers.manage")
  const query = useTeachers()
  const run = useRun(refKeys.teachers)
  const [form, setForm] = useState<{ item?: Teacher } | null>(null)
  const degree = (d: string) => t(`teachers.degrees.${d}`)

  const columns: ColumnDef<Teacher, unknown>[] = [
    { accessorKey: "full_name", header: t("teachers.fullName"), cell: ({ row }) => <span className="font-medium">{row.original.full_name}</span> },
    { accessorKey: "employee_no", header: t("teachers.employeeNo"), cell: ({ row }) => <span className="font-mono text-xs">{row.original.employee_no}</span> },
    { accessorKey: "academic_degree", header: t("teachers.degree"), cell: ({ row }) => degree(row.original.academic_degree) },
    { accessorKey: "academic_title", header: t("teachers.titleField"), cell: ({ row }) => t(`teachers.titles.${row.original.academic_title}`) },
    { accessorKey: "is_active", header: t("common.status"), cell: ({ row }) => <ActiveBadge active={row.original.is_active} /> },
    { id: "actions", header: "", enableSorting: false, cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} /> },
  ]

  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  return (
    <>
      <DataTable columns={columns} data={query.data ?? []} onRowClick={(x) => router.push(`/teachers/${x.id}`)}
        toolbar={manage && <Button onClick={() => setForm({})}><Plus /> {t("teachers.create")}</Button>} />
      <EntityFormDialog open={!!form} onOpenChange={(o) => !o && setForm(null)} title={form?.item ? t("teachers.edit") : t("teachers.create")}
        fields={teacherFields(t)} editing={!!form?.item} initial={teacherInitial(form?.item)}
        onSubmit={(v) => {
          const body = toBody(v) as Schemas["TeacherIn"]
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/teachers/{teacher_id}", { params: { path: { teacher_id: form.item.id } }, body: { ...body, row_version: form.item.row_version } }))
            : unwrap(api.POST("/api/v1/teachers", { body })))
        }} />
    </>
  )
}

function EmploymentTab({ year }: { year: Schemas["AcademicYearOut"] }) {
  const t = useT()
  const { can, me } = useAuth()
  const key = ["employment", year.id]
  const query = useQuery({ queryKey: key, queryFn: () => unwrap(api.GET("/api/v1/years/{year_id}/employment", { params: { path: { year_id: year.id } } })) })
  const teachers = useTeachers()
  const departments = useDepartments()
  const catalog = useTeacherCatalog()
  const depName = useNameMap(departments.data, useCallback((d: Schemas["DepartmentOut"]) => d.name, []))
  const run = useRun(key)
  const [depFilter, setDepFilter] = useState("")
  const [form, setForm] = useState<{ item?: Employment } | null>(null)
  const [removing, setRemoving] = useState<Employment | null>(null)
  // Kafedra ko‘lamidagi foydalanuvchi uchun backend o‘zi filtrlaydi; tugma faqat ruxsat bo‘lsa.
  const manage = can("teachers.manage") && !year.is_locked && !!me
  const data = useMemo(() => (query.data ?? []).filter((e) => !depFilter || e.department_id === depFilter), [query.data, depFilter])
  const positions = catalog.data?.positions ?? {}
  const types = catalog.data?.employment_types ?? {}

  const fields: FieldDef[] = [
    { name: "teacher_id", label: t("teachers.teacher"), type: "select", required: true, wide: true, createOnly: true,
      options: (teachers.data ?? []).filter((x) => x.is_active).map((x) => ({ value: x.id, label: `${x.full_name} (${x.employee_no})` })) },
    { name: "department_id", label: t("teachers.department"), type: "select", required: true, wide: true,
      options: (departments.data ?? []).filter((d) => d.is_active).map((d) => ({ value: d.id, label: d.name })) },
    { name: "position_code", label: t("teachers.position"), type: "select", required: true,
      options: Object.entries(positions).map(([value, label]) => ({ value, label })) },
    { name: "employment_type", label: t("teachers.type"), type: "select", required: true,
      options: Object.entries(types).map(([value, label]) => ({ value, label })) },
    { name: "rate", label: t("teachers.rate"), type: "number", required: true, min: 0.05, max: 2, step: "0.05" },
  ]

  const columns: ColumnDef<Employment, unknown>[] = [
    { accessorKey: "teacher_name", header: t("teachers.fullName"), cell: ({ row }) => <span className="font-medium">{row.original.teacher_name}</span> },
    { accessorKey: "department_id", header: t("teachers.department"), cell: ({ row }) => depName.get(row.original.department_id) ?? "—" },
    { accessorKey: "position_code", header: t("teachers.position"), cell: ({ row }) => positions[row.original.position_code] ?? row.original.position_code },
    { accessorKey: "employment_type", header: t("teachers.type"), cell: ({ row }) => types[row.original.employment_type] ?? row.original.employment_type },
    { accessorKey: "rate", header: t("teachers.rate"), cell: ({ row }) => <span className="tabular-nums">{Number(row.original.rate).toFixed(2)}</span> },
    { accessorKey: "norm_hours", header: t("teachers.normHours"), cell: ({ row }) => row.original.norm_hours
      ? <span className="tabular-nums">{Number(row.original.norm_hours)}</span>
      : <span className="text-xs text-muted-foreground">{t("teachers.normMissing")}</span> },
    { id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => manage && <RowActions onEdit={() => setForm({ item: row.original })} onDelete={() => setRemoving(row.original)} /> },
  ]

  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  return (
    <>
      <DataTable columns={columns} data={data} empty={<EmptyState title={t("teachers.noEmployment")} />} toolbar={<>
        <NativeSelect value={depFilter} onChange={(e) => setDepFilter(e.target.value)} className="w-64">
          <option value="">{t("form.all")}</option>
          {(departments.data ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </NativeSelect>
        {manage && <Button onClick={() => setForm({})}><Plus /> {t("teachers.employmentCreate")}</Button>}
      </>} />
      <EntityFormDialog open={!!form} onOpenChange={(o) => !o && setForm(null)}
        title={form?.item ? `${t("teachers.employmentEdit")} — ${form.item.teacher_name}` : t("teachers.employmentCreate")}
        fields={fields} editing={!!form?.item}
        initial={form?.item ? {
          department_id: form.item.department_id, position_code: form.item.position_code,
          employment_type: form.item.employment_type, rate: String(Number(form.item.rate)),
        } : { employment_type: "main", rate: "1", department_id: depFilter }}
        onSubmit={(v) => {
          const body = toBody(v) as Record<string, unknown>
          return run(() => form?.item
            ? unwrap(api.PATCH("/api/v1/years/{year_id}/employment/{employment_id}", {
              params: { path: { year_id: year.id, employment_id: form.item.id } },
              body: { ...(body as Partial<Schemas["EmploymentUpdateIn"]>), row_version: form.item.row_version },
            }))
            : unwrap(api.POST("/api/v1/years/{year_id}/employment", { params: { path: { year_id: year.id } }, body: body as Schemas["EmploymentIn"] })))
        }} />
      <ConfirmDialog open={!!removing} onOpenChange={(o) => !o && setRemoving(null)} destructive title={t("common.delete")}
        description={removing ? t("ref.deleteConfirm", { name: removing.teacher_name }) : undefined}
        onConfirm={() => removing && run(() => unwrap(api.DELETE("/api/v1/years/{year_id}/employment/{employment_id}", {
          params: { path: { year_id: year.id, employment_id: removing.id } },
        })), t("ref.deleted"))} />
    </>
  )
}
