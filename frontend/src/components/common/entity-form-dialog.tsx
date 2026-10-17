"use client"

import { useEffect, useState } from "react"

import { Field, NativeSelect } from "@/components/common/field"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { ApiError } from "@/lib/api/client"
import { cn } from "@/lib/utils"

export type FieldDef = {
  name: string
  label: string
  type?: "text" | "number" | "select" | "checkbox" | "date"
  options?: { value: string; label: string }[]
  required?: boolean
  hint?: string
  placeholder?: string
  min?: number
  max?: number
  step?: string
  /** Faqat yaratishda ko‘rsatiladi (masalan, o‘zgarmaydigan kod). */
  createOnly?: boolean
  wide?: boolean
}

export type FormValues = Record<string, string | boolean>

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  fields: FieldDef[]
  initial?: FormValues
  editing?: boolean
  /** Qiymatlar matn ko‘rinishida; bo‘sh matn — null. Xato bo‘lsa ApiError ko‘taring — oynada ko‘rsatiladi. */
  onSubmit: (values: FormValues) => Promise<unknown>
}

/** Konfiguratsiya asosidagi yaratish/tahrirlash oynasi — ma’lumotnoma sahifalari uchun. */
export function EntityFormDialog({ open, onOpenChange, title, description, fields, initial, editing, onSubmit }: Props) {
  const t = useT()
  const [values, setValues] = useState<FormValues>({})
  const [error, setError] = useState<string | null>(null)
  const [missing, setMissing] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    const start: FormValues = {}
    for (const f of fields) start[f.name] = initial?.[f.name] ?? (f.type === "checkbox" ? false : "")
    setValues(start)
    setError(null)
    setMissing(new Set())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const empty = new Set(fields.filter((f) => f.required && !(editing && f.createOnly) && values[f.name] === "").map((f) => f.name))
    setMissing(empty)
    if (empty.size) return
    setBusy(true)
    try {
      await onSubmit(values)
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const set = (name: string, value: string | boolean) => setValues((v) => ({ ...v, [name]: value }))

  return (
    <Dialog open={open} onOpenChange={(o) => !busy && onOpenChange(o)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <form id="entity-form" onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          {error && <Alert variant="destructive" className="sm:col-span-2"><AlertDescription>{error}</AlertDescription></Alert>}
          {fields.filter((f) => !(editing && f.createOnly)).map((f) => {
            const id = `ef-${f.name}`
            const err = missing.has(f.name) ? t("form.required") : undefined
            if (f.type === "checkbox") {
              return (
                <label key={f.name} className="flex items-center gap-2 text-sm sm:col-span-2">
                  <Checkbox checked={values[f.name] === true} onCheckedChange={(v) => set(f.name, v === true)} />
                  {f.label}
                </label>
              )
            }
            return (
              <Field key={f.name} label={f.label + (f.required ? " *" : "")} htmlFor={id} hint={f.hint} error={err}
                className={cn(f.wide && "sm:col-span-2")}>
                {f.type === "select" ? (
                  <NativeSelect id={id} value={String(values[f.name] ?? "")} onChange={(e) => set(f.name, e.target.value)}>
                    <option value="">—</option>
                    {f.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </NativeSelect>
                ) : (
                  <Input id={id} type={f.type ?? "text"} value={String(values[f.name] ?? "")} placeholder={f.placeholder}
                    min={f.min} max={f.max} step={f.step} onChange={(e) => set(f.name, e.target.value)} />
                )}
              </Field>
            )
          })}
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>{t("common.cancel")}</Button>
          <Button type="submit" form="entity-form" disabled={busy}>{editing ? t("common.save") : t("common.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/** Forma qiymatlarini API tanasiga: bo‘sh matn → null, raqamli maydonlar → son. */
export function toBody(values: FormValues, numeric: string[] = []): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(values)) {
    if (typeof v === "boolean") out[k] = v
    else if (v === "") out[k] = null
    else out[k] = numeric.includes(k) ? Number(v) : v
  }
  return out
}
