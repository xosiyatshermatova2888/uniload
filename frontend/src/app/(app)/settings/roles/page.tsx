"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Copy, Lock, Plus, Trash2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { ConfirmDialog } from "@/components/common/confirm-dialog"
import { Field } from "@/components/common/field"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { cn } from "@/lib/utils"

type Permission = Schemas["PermissionOut"]

function PermissionMatrix({ permissions, selected, onToggle, readOnly }: {
  permissions: Permission[]
  selected: Set<string>
  onToggle?: (code: string) => void
  readOnly?: boolean
}) {
  const groups = useMemo(() => {
    const map = new Map<string, Permission[]>()
    for (const p of permissions) {
      if (p.module === "platform" && p.code !== "platform.subscriptions.view") continue
      map.set(p.module, [...(map.get(p.module) ?? []), p])
    }
    return [...map.entries()]
  }, [permissions])

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {groups.map(([module, items]) => (
        <div key={module} className="rounded-lg border p-3">
          <p className="mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">{module}</p>
          <div className="grid gap-1.5">
            {items.map((p) => (
              <label key={p.code} className={cn("flex items-start gap-2 text-sm", readOnly && "cursor-default")}>
                <Checkbox checked={selected.has(p.code)} disabled={readOnly} onCheckedChange={() => onToggle?.(p.code)} className="mt-0.5" />
                <span>
                  {p.description}
                  <span className="block font-mono text-[11px] text-muted-foreground">{p.code}</span>
                </span>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export default function RolesPage() {
  const t = useT()
  const queryClient = useQueryClient()
  const roles = useQuery({ queryKey: ["roles"], queryFn: () => unwrap(api.GET("/api/v1/roles")) })
  const permissions = useQuery({ queryKey: ["permissions"], queryFn: () => unwrap(api.GET("/api/v1/permissions")) })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [creating, setCreating] = useState<{ copyFrom?: string } | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!selectedId && roles.data?.length) setSelectedId(roles.data[0].id)
  }, [roles.data, selectedId])

  const detail = useQuery({
    queryKey: ["role", selectedId],
    queryFn: () => unwrap(api.GET("/api/v1/roles/{role_id}", { params: { path: { role_id: selectedId! } } })),
    enabled: !!selectedId,
  })
  const [draft, setDraft] = useState<Set<string> | null>(null)
  useEffect(() => setDraft(null), [selectedId])
  const selected = draft ?? new Set(detail.data?.permissions ?? [])

  const save = useMutation({
    mutationFn: () => unwrap(api.PATCH("/api/v1/roles/{role_id}", {
      params: { path: { role_id: selectedId! } },
      body: { row_version: detail.data!.row_version, permissions: [...selected] },
    })),
    onSuccess: async () => {
      toast.success(t("common.saved"))
      setDraft(null)
      await queryClient.invalidateQueries({ queryKey: ["role", selectedId] })
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : String(e)),
  })

  const remove = useMutation({
    mutationFn: () => unwrap(api.DELETE("/api/v1/roles/{role_id}", { params: { path: { role_id: selectedId! } } })),
    onSuccess: async () => {
      toast.success(t("roles.deleted"))
      setSelectedId(null)
      await queryClient.invalidateQueries({ queryKey: ["roles"] })
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : String(e)),
  })

  if (roles.isLoading || permissions.isLoading) return <TableSkeleton />
  if (roles.error) return <ErrorState error={roles.error} onRetry={() => roles.refetch()} />
  const role = detail.data

  return (
    <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
      <Card className="h-fit">
        <CardHeader>
          <CardTitle className="text-base">{t("roles.title")}</CardTitle>
          <CardDescription>{t("roles.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-1">
          {roles.data!.map((r) => (
            <button key={r.id} type="button" onClick={() => setSelectedId(r.id)}
              className={cn("flex items-center justify-between rounded-md px-2.5 py-2 text-left text-sm",
                r.id === selectedId ? "bg-primary/10 font-medium text-primary" : "hover:bg-muted")}>
              <span className="truncate">{r.name}</span>
              {r.is_system && <Lock className="size-3.5 shrink-0 opacity-60" />}
            </button>
          ))}
          <Button variant="outline" className="mt-2" onClick={() => setCreating({})}><Plus /> {t("roles.create")}</Button>
        </CardContent>
      </Card>

      <Card>
        {!role ? <CardContent><TableSkeleton rows={4} /></CardContent> : (
          <>
            <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-base">{role.name}</CardTitle>
                <CardDescription>
                  {role.is_system ? t("roles.system") : t("roles.custom")} · <span className="font-mono">{role.code}</span> ·{" "}
                  {t("roles.users")}: {role.users_count}
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setCreating({ copyFrom: role.id })}><Copy /> {t("roles.copy")}</Button>
                {!role.is_system && (
                  <Button variant="destructive" size="sm" onClick={() => setDeleting(true)}><Trash2 /> {t("common.delete")}</Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <PermissionMatrix permissions={permissions.data ?? []} selected={selected} readOnly={role.is_system}
                onToggle={(code) => {
                  const next = new Set(selected)
                  if (next.has(code)) next.delete(code)
                  else next.add(code)
                  setDraft(next)
                }} />
              {!role.is_system && draft && (
                <div className="mt-4 flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setDraft(null)}>{t("common.cancel")}</Button>
                  <Button onClick={() => save.mutate()} disabled={save.isPending}>{t("common.save")}</Button>
                </div>
              )}
            </CardContent>
          </>
        )}
      </Card>

      {creating && (
        <CreateRoleDialog
          permissions={permissions.data ?? []}
          initial={creating.copyFrom && role ? new Set(role.permissions) : new Set()}
          onClose={() => setCreating(null)}
          onCreated={async (id) => {
            await queryClient.invalidateQueries({ queryKey: ["roles"] })
            setSelectedId(id)
          }}
        />
      )}
      <ConfirmDialog open={deleting} onOpenChange={setDeleting} destructive title={t("common.delete")}
        description={role ? t("roles.deleteConfirm", { name: role.name }) : undefined}
        onConfirm={() => remove.mutateAsync()} />
    </div>
  )
}

function CreateRoleDialog({ permissions, initial, onClose, onCreated }: {
  permissions: Permission[]
  initial: Set<string>
  onClose: () => void
  onCreated: (id: string) => Promise<void>
}) {
  const t = useT()
  const [code, setCode] = useState("")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [selected, setSelected] = useState(initial)
  const [error, setError] = useState<string | null>(null)
  const create = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/roles", {
      body: { code, name, description: description || null, default_scope: "university", permissions: [...selected] },
    })),
    onSuccess: async (role) => {
      toast.success(t("roles.created"))
      await onCreated(role.id)
      onClose()
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  })
  const validCode = /^[a-z0-9_]{2,64}$/.test(code)

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader><DialogTitle>{t("roles.create")}</DialogTitle></DialogHeader>
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label={t("roles.name")} htmlFor="r-name"><Input id="r-name" value={name} onChange={(e) => setName(e.target.value)} /></Field>
          <Field label={t("roles.code")} htmlFor="r-code" hint="a-z, 0-9, _" error={code && !validCode ? "a-z, 0-9, _" : undefined}>
            <Input id="r-code" value={code} onChange={(e) => setCode(e.target.value.toLowerCase())} className="font-mono" />
          </Field>
          <Field label={t("roles.description")} htmlFor="r-desc" className="sm:col-span-2">
            <Input id="r-desc" value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
        </div>
        <PermissionMatrix permissions={permissions} selected={selected} onToggle={(c) => {
          const next = new Set(selected)
          if (next.has(c)) next.delete(c)
          else next.add(c)
          setSelected(next)
        }} />
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={() => create.mutate()} disabled={!validCode || name.length < 2 || create.isPending}>{t("common.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
