"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { ColumnDef } from "@tanstack/react-table"
import { Ban, CheckCircle2, MoreHorizontal, Plus, ShieldCheck } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { DataTable } from "@/components/common/data-table"
import { Field } from "@/components/common/field"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { ActiveBadge } from "@/components/common/status-badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { RoleAssignmentsEditor, type Assignment } from "@/features/users/role-assignments-editor"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"
import { formatDateTime } from "@/lib/format"

type User = Schemas["UserOut"]
const PAGE_SIZE = 20

function useDebounced<T>(value: T, ms = 300) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return v
}

export default function UsersPage() {
  const t = useT()
  const { me } = useAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState("")
  const q = useDebounced(search)
  const [createOpen, setCreateOpen] = useState(false)
  const [rolesFor, setRolesFor] = useState<User | null>(null)
  const [blockTarget, setBlockTarget] = useState<User | null>(null)

  useEffect(() => setPage(1), [q])

  const query = useQuery({
    queryKey: ["users", page, q],
    queryFn: () => unwrap(api.GET("/api/v1/users", { params: { query: { page, size: PAGE_SIZE, q: q || undefined } } })),
    placeholderData: keepPreviousData,
  })
  const roles = useQuery({ queryKey: ["roles"], queryFn: () => unwrap(api.GET("/api/v1/roles")) })

  const toggleActive = useMutation({
    mutationFn: (u: User) => unwrap(api.PATCH("/api/v1/users/{user_id}", {
      params: { path: { user_id: u.id } }, body: { row_version: u.row_version, is_active: !u.is_active },
    })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (e) => toast.error(e instanceof ApiError ? e.message : String(e)),
  })

  const columns: ColumnDef<User, unknown>[] = [
    {
      accessorKey: "full_name", header: t("users.fullName"),
      cell: ({ row }) => (
        <div>
          <div className="font-medium">{row.original.full_name}</div>
          <div className="text-xs text-muted-foreground">
            <span className="font-mono">{row.original.username}</span>{row.original.email && ` · ${row.original.email}`}
          </div>
        </div>
      ),
    },
    { accessorKey: "phone", header: t("users.phone"), enableSorting: false, cell: ({ row }) => row.original.phone ?? "—" },
    { accessorKey: "is_active", header: t("common.status"), cell: ({ row }) => <ActiveBadge active={row.original.is_active} /> },
    {
      accessorKey: "last_login_at", header: t("users.lastLogin"),
      cell: ({ row }) => <span className="text-muted-foreground tabular-nums">
        {row.original.last_login_at ? formatDateTime(row.original.last_login_at) : t("users.never")}
      </span>,
    },
    {
      id: "actions", header: "", enableSorting: false,
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label={t("common.actions")} />}>
            <MoreHorizontal />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuItem onClick={() => setRolesFor(row.original)}><ShieldCheck /> {t("users.editRoles")}</DropdownMenuItem>
            {row.original.id !== me?.id && (
              <DropdownMenuItem variant={row.original.is_active ? "destructive" : "default"} onClick={() => setBlockTarget(row.original)}>
                {row.original.is_active ? <><Ban /> {t("users.block")}</> : <><CheckCircle2 /> {t("users.unblock")}</>}
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  const total = query.data?.total ?? 0
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <>
      {query.isLoading ? <TableSkeleton /> : query.error ? <ErrorState error={query.error} onRetry={() => query.refetch()} /> : (
        <DataTable
          columns={columns}
          data={query.data?.items ?? []}
          search={search}
          onSearchChange={setSearch}
          toolbar={<Button onClick={() => setCreateOpen(true)}><Plus /> {t("users.create")}</Button>}
          footer={
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{t("common.total", { n: total })}</span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>{t("common.prev")}</Button>
                <span className="tabular-nums">{t("common.page", { page, pages })}</span>
                <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>{t("common.next")}</Button>
              </div>
            </div>
          }
        />
      )}

      {createOpen && <CreateUserDialog roles={roles.data ?? []} onClose={() => setCreateOpen(false)} />}
      {rolesFor && <EditRolesDialog user={rolesFor} roles={roles.data ?? []} onClose={() => setRolesFor(null)} />}
      <ConfirmDialog
        open={!!blockTarget}
        onOpenChange={(o) => !o && setBlockTarget(null)}
        title={blockTarget?.is_active ? t("users.block") : t("users.unblock")}
        description={blockTarget?.is_active ? t("users.blockConfirm", { name: blockTarget.full_name }) : blockTarget?.full_name}
        destructive={blockTarget?.is_active}
        onConfirm={() => blockTarget && toggleActive.mutateAsync(blockTarget)}
      />
    </>
  )
}

const USERNAME = /^[a-z0-9][a-z0-9._-]{2,63}$/

const createSchema = z.object({
  username: z.string().trim().toLowerCase().regex(USERNAME),
  email: z.union([z.literal(""), z.string().email()]).optional(),
  full_name: z.string().min(2),
  phone: z.string().max(32).optional(),
  initial_password: z.string().min(8).regex(/[A-Za-z]/).regex(/\d/),
})

function CreateUserDialog({ roles, onClose }: { roles: Schemas["RoleOut"][]; onClose: () => void }) {
  const t = useT()
  const queryClient = useQueryClient()
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const form = useForm<z.infer<typeof createSchema>>({ resolver: zodResolver(createSchema) })
  const { errors, isSubmitting } = form.formState

  async function submit(values: z.infer<typeof createSchema>) {
    try {
      await unwrap(api.POST("/api/v1/users", {
        body: { ...values, email: values.email || null, phone: values.phone || null, roles: assignments },
      }))
      toast.success(t("users.created"))
      await queryClient.invalidateQueries({ queryKey: ["users"] })
      onClose()
    } catch (e) {
      form.setError("root", { message: e instanceof ApiError ? e.message : String(e) })
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>{t("users.create")}</DialogTitle></DialogHeader>
        <form id="create-user" onSubmit={form.handleSubmit(submit)} className="grid gap-4">
          {errors.root && <Alert variant="destructive"><AlertDescription>{errors.root.message}</AlertDescription></Alert>}
          <Field label={t("users.fullName")} htmlFor="u-name" error={errors.full_name && " "}>
            <Input id="u-name" {...form.register("full_name")} />
          </Field>
          <Field label={`${t("users.username")} *`} htmlFor="u-username" hint={t("users.usernameHint")}
            error={errors.username && t("users.usernameInvalid")}>
            <Input id="u-username" autoCapitalize="none" spellCheck={false} className="font-mono" {...form.register("username")} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("users.email")} htmlFor="u-email" hint={t("users.emailHint")} error={errors.email && " "}>
              <Input id="u-email" type="email" {...form.register("email")} />
            </Field>
            <Field label={t("users.phone")} htmlFor="u-phone">
              <Input id="u-phone" {...form.register("phone")} />
            </Field>
          </div>
          <Field label={t("users.initialPassword")} htmlFor="u-pass" hint={t("users.initialPasswordHint")}
            error={errors.initial_password && t("auth.passwordRule")}>
            <Input id="u-pass" type="password" autoComplete="new-password" {...form.register("initial_password")} />
          </Field>
          <Field label={t("users.roles")}>
            <RoleAssignmentsEditor roles={roles} value={assignments} onChange={setAssignments} />
          </Field>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button type="submit" form="create-user" disabled={isSubmitting}>{t("common.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function EditRolesDialog({ user, roles, onClose }: { user: User; roles: Schemas["RoleOut"][]; onClose: () => void }) {
  const t = useT()
  const queryClient = useQueryClient()
  const detail = useQuery({
    queryKey: ["user", user.id],
    queryFn: () => unwrap(api.GET("/api/v1/users/{user_id}", { params: { path: { user_id: user.id } } })),
  })
  const [assignments, setAssignments] = useState<Assignment[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const value = assignments ?? detail.data?.roles.map((r) => ({
    role_id: r.role_id, scope_type: r.scope_type as Assignment["scope_type"], scope_id: r.scope_id,
  })) ?? []

  const save = useMutation({
    mutationFn: () => unwrap(api.PUT("/api/v1/users/{user_id}/roles", { params: { path: { user_id: user.id } }, body: { roles: value } })),
    onSuccess: async () => {
      toast.success(t("common.saved"))
      await queryClient.invalidateQueries({ queryKey: ["user", user.id] })
      onClose()
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  })

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("users.editRoles")}</DialogTitle>
          <DialogDescription>{user.full_name} · {user.username}</DialogDescription>
        </DialogHeader>
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        {detail.isLoading ? <TableSkeleton rows={2} /> : <RoleAssignmentsEditor roles={roles} value={value} onChange={setAssignments} />}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={() => save.mutate()} disabled={save.isPending || detail.isLoading}>{t("common.save")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
