"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { Plus, Star } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState } from "react"

import { DataTable } from "@/components/common/data-table"
import { PageHeader } from "@/components/common/page-header"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { YearStatusBadge } from "@/components/common/status-badge"
import { Button } from "@/components/ui/button"
import { CreateYearWizard } from "@/features/academic-years/create-year-wizard"
import { useT } from "@/i18n"
import { useAuth } from "@/lib/auth"
import { formatDate, formatDateTime } from "@/lib/format"
import { useYearsQuery, type AcademicYear } from "@/lib/year"

export default function AcademicYearsPage() {
  const t = useT()
  const router = useRouter()
  const { can } = useAuth()
  const [wizardOpen, setWizardOpen] = useState(false)
  const query = useYearsQuery()
  const years = query.data ?? []
  const labels = new Map(years.map((y) => [y.id, y.label]))

  const columns: ColumnDef<AcademicYear, unknown>[] = [
    {
      accessorKey: "label",
      header: t("years.label"),
      cell: ({ row }) => (
        <span className="flex items-center gap-2 font-medium tabular-nums">
          {row.original.label}
          {row.original.is_current && (
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
              <Star className="size-3" /> {t("year.current")}
            </span>
          )}
        </span>
      ),
    },
    { accessorKey: "status", header: t("common.status"), cell: ({ row }) => <YearStatusBadge status={row.original.status} /> },
    {
      id: "period",
      header: t("years.period"),
      enableSorting: false,
      cell: ({ row }) => <span className="tabular-nums text-muted-foreground">{formatDate(row.original.starts_on)} — {formatDate(row.original.ends_on)}</span>,
    },
    {
      accessorKey: "source_year_id",
      header: t("years.source"),
      enableSorting: false,
      cell: ({ row }) => <span className="text-muted-foreground">{row.original.source_year_id ? labels.get(row.original.source_year_id) ?? "—" : "—"}</span>,
    },
    {
      accessorKey: "created_at",
      header: t("years.createdAt"),
      cell: ({ row }) => <span className="text-muted-foreground tabular-nums">{formatDateTime(row.original.created_at)}</span>,
    },
  ]

  return (
    <>
      <PageHeader
        title={t("years.title")}
        description={t("years.subtitle")}
        actions={can("academic_year.create") && (
          <Button onClick={() => setWizardOpen(true)}><Plus /> {t("years.create")}</Button>
        )}
      />
      {query.isLoading ? <TableSkeleton /> : query.error ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : (
        <DataTable columns={columns} data={years} onRowClick={(y) => router.push(`/academic-years/${y.id}`)} />
      )}
      {wizardOpen && <CreateYearWizard open={wizardOpen} onOpenChange={setWizardOpen} years={years} />}
    </>
  )
}
