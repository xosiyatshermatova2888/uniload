"use client"

import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Info } from "lucide-react"
import { useEffect, useState } from "react"

import { EmptyState, ErrorState, TableSkeleton } from "@/components/common/states"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useT } from "@/i18n"
import { api, unwrap } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { useRun } from "@/lib/use-crud"
import { useYear } from "@/lib/year"

type Row = { position_code: string; position_name: string; per_rate: string; overload: string; source: string; review: boolean }

export default function NormsPage() {
  const t = useT()
  const { can } = useAuth()
  const { year } = useYear()
  const key = ["norms", year?.id]
  const query = useQuery({
    queryKey: key,
    queryFn: () => unwrap(api.GET("/api/v1/years/{year_id}/position-norms", { params: { path: { year_id: year!.id } } })),
    enabled: !!year,
  })
  const run = useRun(key, ["employment", year?.id])
  const [rows, setRows] = useState<Row[]>([])
  const editable = can("teachers.manage") && !!year && !year.is_locked

  useEffect(() => {
    setRows((query.data ?? []).map((n) => ({
      position_code: n.position_code, position_name: n.position_name,
      per_rate: n.norm_hours_per_rate == null ? "" : String(Number(n.norm_hours_per_rate)),
      overload: n.max_overload_pct == null ? "" : String(Number(n.max_overload_pct)),
      source: n.source_document ?? "", review: n.needs_review,
    })))
  }, [query.data])

  if (!year) return <EmptyState title={t("year.none")} />
  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const update = (i: number, patch: Partial<Row>) => setRows((r) => r.map((x, j) => (j === i ? { ...x, ...patch } : x)))

  return (
    <Card className="max-w-5xl">
      <CardContent className="space-y-4">
        <Alert><Info /><AlertDescription>{t("norms.subtitle")} ({year.label})</AlertDescription></Alert>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("norms.position")}</TableHead>
                <TableHead>{t("norms.perRate")}</TableHead>
                <TableHead>{t("norms.overload")}</TableHead>
                <TableHead>{t("norms.source")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r, i) => (
                <TableRow key={r.position_code}>
                  <TableCell className="font-medium whitespace-nowrap">
                    {r.position_name}
                    {r.review && <AlertTriangle className="ml-1.5 inline size-3.5 text-warning" aria-label={t("norms.review")} />}
                  </TableCell>
                  <TableCell><Input type="number" min={1} className="w-28 tabular-nums" value={r.per_rate} disabled={!editable} onChange={(e) => update(i, { per_rate: e.target.value })} /></TableCell>
                  <TableCell><Input type="number" min={0} max={100} className="w-24 tabular-nums" value={r.overload} disabled={!editable} onChange={(e) => update(i, { overload: e.target.value })} /></TableCell>
                  <TableCell><Input value={r.source} disabled={!editable} onChange={(e) => update(i, { source: e.target.value })} /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
      {editable && (
        <CardFooter className="justify-end">
          <Button onClick={() => run(() => unwrap(api.PUT("/api/v1/years/{year_id}/position-norms", {
            params: { path: { year_id: year.id } },
            body: { norms: rows.map((r) => ({
              position_code: r.position_code as "assistant",
              norm_hours_per_rate: r.per_rate === "" ? null : r.per_rate,
              max_overload_pct: r.overload === "" ? null : r.overload,
              source_document: r.source || null,
            })) },
          })))}>{t("common.save")}</Button>
        </CardFooter>
      )}
    </Card>
  )
}
