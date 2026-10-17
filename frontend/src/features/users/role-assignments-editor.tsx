"use client"

import { Plus, X } from "lucide-react"

import { NativeSelect } from "@/components/common/field"
import { Button } from "@/components/ui/button"
import { useT } from "@/i18n"
import type { Schemas } from "@/lib/api/client"

export type Assignment = Schemas["RoleAssignmentIn"]
type Role = Schemas["RoleOut"]

// Fakultet/kafedra ko‘lami tanlovi 2-bosqichda (kafedralar ro‘yxati paydo bo‘lgach) qo‘shiladi.
const SCOPES = ["university", "self"] as const

export function RoleAssignmentsEditor({ roles, value, onChange }: {
  roles: Role[]
  value: Assignment[]
  onChange: (value: Assignment[]) => void
}) {
  const t = useT()
  const update = (i: number, patch: Partial<Assignment>) => onChange(value.map((a, j) => (j === i ? { ...a, ...patch } : a)))

  return (
    <div className="grid gap-2">
      {value.map((a, i) => (
        <div key={i} className="flex items-center gap-2">
          <NativeSelect value={a.role_id} onChange={(e) => {
            const role = roles.find((r) => r.id === e.target.value)
            const scope = role && (SCOPES as readonly string[]).includes(role.default_scope) ? role.default_scope : "self"
            update(i, { role_id: e.target.value, scope_type: scope as Assignment["scope_type"] })
          }}>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </NativeSelect>
          <NativeSelect value={a.scope_type} className="max-w-44"
            onChange={(e) => update(i, { scope_type: e.target.value as Assignment["scope_type"] })}>
            {SCOPES.map((s) => <option key={s} value={s}>{t(`users.scopes.${s}`)}</option>)}
          </NativeSelect>
          <Button variant="ghost" size="icon" onClick={() => onChange(value.filter((_, j) => j !== i))} aria-label={t("common.delete")}>
            <X />
          </Button>
        </div>
      ))}
      <div className="flex items-center justify-between gap-2">
        <Button variant="outline" size="sm" disabled={!roles.length}
          onClick={() => onChange([...value, { role_id: roles[0].id, scope_type: "university", scope_id: null }])}>
          <Plus /> {t("users.roles")}
        </Button>
        <span className="text-xs text-muted-foreground">{t("users.scopeDeptLater")}</span>
      </div>
    </div>
  )
}
