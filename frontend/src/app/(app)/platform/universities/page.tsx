"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { Pause, Play, Plus } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { Field, NativeSelect } from "@/components/common/field"
import { PageHeader } from "@/components/common/page-header"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { cn } from "@/lib/utils"

type University = Schemas["PlatformUniversityOut"]

export default function PlatformUniversitiesPage() {
  const t = useT()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ["platform", "universities"], queryFn: () => unwrap(api.GET("/api/v1/platform/universities")) })
  const [createOpen, setCreateOpen] = useState(false)
  const [target, setTarget] = useState<University | null>(null)

  const toggle = useMutation({
    mutationFn: (u: University) => unwrap(api.PATCH("/api/v1/platform/universities/{university_id}", {
      params: { path: { university_id: u.id } },
      body: { row_version: u.row_version, status: u.status === "active" ? "suspended" : "active" },
    })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["platform", "universities"] }),
    onError: (e) => toast.error(e instanceof ApiError ? e.message : String(e)),
  })

  const columns: ColumnDef<University, unknown>[] = [
    {
      accessorKey: "name", header: t("platform.name"),
      cell: ({ row }) => <div><div className="font-medium">{row.original.name}</div>
        <div className="font-mono text-xs text-muted-foreground">{row.original.code}</div></div>,
    },
    {
      accessorKey: "status", header: t("common.status"),
      cell: ({ row }) => <span className={cn("text-xs font-medium", row.original.status === "active" ? "text-emerald-700 dark:text-emerald-300" : "text-destructive")}>
        {t(`platform.statuses.${row.original.status}`)}
      </span>,
    },
    { accessorKey: "plan_code", header: t("platform.plan"), cell: ({ row }) => row.original.plan_code ?? "—" },
    { accessorKey: "subscription_status", header: t("platform.subscription"), cell: ({ row }) => row.original.subscription_status ?? "—" },
    { accessorKey: "users_count", header: t("platform.users"), cell: ({ row }) => <span className="tabular-nums">{row.original.users_count}</span> },
    {
      id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => row.original.status !== "closed" && (
        <Button variant="ghost" size="sm" onClick={() => setTarget(row.original)}>
          {row.original.status === "active" ? <><Pause /> {t("platform.suspend")}</> : <><Play /> {t("platform.activate")}</>}
        </Button>
      ),
    },
  ]

  return (
    <>
      <PageHeader title={t("platform.title")} description={t("platform.subtitle")}
        actions={<Button onClick={() => setCreateOpen(true)}><Plus /> {t("platform.create")}</Button>} />
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable columns={columns} data={query.data ?? []} />
      )}
      {createOpen && <CreateUniversityDialog onClose={() => setCreateOpen(false)} />}
      <ConfirmDialog
        open={!!target}
        onOpenChange={(o) => !o && setTarget(null)}
        title={target?.status === "active" ? t("platform.suspend") : t("platform.activate")}
        description={target?.status === "active" ? t("platform.suspendConfirm", { name: target.name }) : target?.name}
        destructive={target?.status === "active"}
        onConfirm={() => target && toggle.mutateAsync(target)}
      />
    </>
  )
}

const schema = z.object({
  code: z.string().regex(/^[a-z0-9-]{2,64}$/),
  name: z.string().min(3),
  short_name: z.string().max(64).optional(),
  plan_code: z.string(),
  admin_email: z.string().email(),
  admin_name: z.string().min(2),
  admin_password: z.string().min(8).regex(/[A-Za-z]/).regex(/\d/),
})

function CreateUniversityDialog({ onClose }: { onClose: () => void }) {
  const t = useT()
  const queryClient = useQueryClient()
  const plans = useQuery({ queryKey: ["platform", "plans"], queryFn: () => unwrap(api.GET("/api/v1/platform/plans")) })
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { plan_code: "trial" } })
  const { errors, isSubmitting } = form.formState

  async function submit(v: z.infer<typeof schema>) {
    try {
      await unwrap(api.POST("/api/v1/platform/universities", {
        body: {
          code: v.code, name: v.name, short_name: v.short_name || null, plan_code: v.plan_code,
          first_admin: { email: v.admin_email, full_name: v.admin_name, initial_password: v.admin_password },
        },
      }))
      toast.success(t("platform.created"))
      await queryClient.invalidateQueries({ queryKey: ["platform", "universities"] })
      onClose()
    } catch (e) {
      form.setError("root", { message: e instanceof ApiError ? e.message : String(e) })
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>{t("platform.create")}</DialogTitle></DialogHeader>
        <form id="create-uni" onSubmit={form.handleSubmit(submit)} className="grid gap-4">
          {errors.root && <Alert variant="destructive"><AlertDescription>{errors.root.message}</AlertDescription></Alert>}
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("platform.code")} htmlFor="uc" hint="a-z, 0-9, -" error={errors.code && "a-z, 0-9, -"}>
              <Input id="uc" className="font-mono" {...form.register("code")} />
            </Field>
            <Field label={t("platform.plan")} htmlFor="up">
              <NativeSelect id="up" {...form.register("plan_code")}>
                {(plans.data ?? []).map((p) => <option key={p.id} value={p.code}>{p.name}</option>)}
              </NativeSelect>
            </Field>
          </div>
          <Field label={t("platform.name")} htmlFor="un" error={errors.name && " "}><Input id="un" {...form.register("name")} /></Field>
          <p className="pt-1 text-sm font-medium">{t("platform.firstAdmin")}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("users.fullName")} htmlFor="an" error={errors.admin_name && " "}><Input id="an" {...form.register("admin_name")} /></Field>
            <Field label={t("users.email")} htmlFor="ae" error={errors.admin_email && " "}><Input id="ae" type="email" {...form.register("admin_email")} /></Field>
          </div>
          <Field label={t("users.initialPassword")} htmlFor="ap" hint={t("users.initialPasswordHint")}
            error={errors.admin_password && t("auth.passwordRule")}>
            <Input id="ap" type="password" autoComplete="new-password" {...form.register("admin_password")} />
          </Field>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button type="submit" form="create-uni" disabled={isSubmitting}>{t("common.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
