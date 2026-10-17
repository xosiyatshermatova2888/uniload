"use client"

import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Pencil } from "lucide-react"
import Link from "next/link"
import { use, useCallback, useState } from "react"

import { EntityFormDialog, toBody } from "@/components/common/entity-form-dialog"
import { teacherFields, teacherInitial } from "@/features/teachers/form"
import { PageHeader } from "@/components/common/page-header"
import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states"
import { ActiveBadge, YearStatusBadge } from "@/components/common/status-badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useT } from "@/i18n"
import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { refKeys, useDepartments, useNameMap, useTeacherCatalog } from "@/lib/refs"
import { useRun } from "@/lib/use-crud"

export default function TeacherDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const t = useT()
  const { can } = useAuth()
  const key = ["teacher", id]
  const teacher = useQuery({ queryKey: key, queryFn: () => unwrap(api.GET("/api/v1/teachers/{teacher_id}", { params: { path: { teacher_id: id } } })) })
  const history = useQuery({ queryKey: [...key, "history"], queryFn: () => unwrap(api.GET("/api/v1/teachers/{teacher_id}/history", { params: { path: { teacher_id: id } } })) })
  const departments = useDepartments()
  const catalog = useTeacherCatalog()
  const depName = useNameMap(departments.data, useCallback((d: Schemas["DepartmentOut"]) => d.name, []))
  const run = useRun(key, refKeys.teachers)
  const [editing, setEditing] = useState(false)

  if (teacher.isLoading) return <TableSkeleton rows={6} />
  if (teacher.error || !teacher.data) return <ErrorState error={teacher.error} onRetry={() => teacher.refetch()} />
  const x = teacher.data

  return (
    <>
      <Link href="/teachers" className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> {t("teachers.title")}
      </Link>
      <PageHeader title={x.full_name} description={`${t("teachers.employeeNo")}: ${x.employee_no}`}
        actions={can("teachers.manage") && <Button variant="outline" onClick={() => setEditing(true)}><Pencil /> {t("common.edit")}</Button>} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle className="text-base">{t("teachers.profile")}</CardTitle></CardHeader>
          <CardContent>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-muted-foreground">{t("teachers.degree")}</dt><dd>{t(`teachers.degrees.${x.academic_degree}`)}</dd>
              <dt className="text-muted-foreground">{t("teachers.titleField")}</dt><dd>{t(`teachers.titles.${x.academic_title}`)}</dd>
              <dt className="text-muted-foreground">{t("users.email")}</dt><dd>{x.email ?? "—"}</dd>
              <dt className="text-muted-foreground">{t("users.phone")}</dt><dd>{x.phone ?? "—"}</dd>
              <dt className="text-muted-foreground">{t("common.status")}</dt><dd><ActiveBadge active={x.is_active} /></dd>
            </dl>
          </CardContent>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">{t("teachers.history")}</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            {!history.data?.length ? <EmptyState title={t("teachers.noEmployment")} /> : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("years.label")}</TableHead>
                    <TableHead>{t("teachers.department")}</TableHead>
                    <TableHead>{t("teachers.position")}</TableHead>
                    <TableHead className="text-right">{t("teachers.rate")}</TableHead>
                    <TableHead className="text-right">{t("teachers.normHours")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.data.map((h) => (
                    <TableRow key={`${h.academic_year_id}-${h.department_id}-${h.employment_type}`}>
                      <TableCell className="whitespace-nowrap"><span className="mr-2 tabular-nums">{h.year_label}</span><YearStatusBadge status={h.year_status} /></TableCell>
                      <TableCell>{depName.get(h.department_id) ?? "—"}</TableCell>
                      <TableCell>{catalog.data?.positions[h.position_code] ?? h.position_code}</TableCell>
                      <TableCell className="text-right tabular-nums">{Number(h.rate).toFixed(2)}</TableCell>
                      <TableCell className="text-right tabular-nums">{h.norm_hours ? Number(h.norm_hours) : "—"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
      <EntityFormDialog open={editing} onOpenChange={setEditing} title={t("teachers.edit")} fields={teacherFields(t)} editing initial={teacherInitial(x)}
        onSubmit={(v) => run(() => unwrap(api.PATCH("/api/v1/teachers/{teacher_id}", {
          params: { path: { teacher_id: id } }, body: { ...(toBody(v) as Schemas["TeacherIn"]), row_version: x.row_version },
        })))} />
    </>
  )
}
