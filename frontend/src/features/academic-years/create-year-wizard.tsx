"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { AlertTriangle, CalendarPlus, Check, Copy, FilePlus2, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useMemo, useState } from "react"
import { toast } from "sonner"

import { Field, NativeSelect } from "@/components/common/field"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { api, ApiError, unwrap, type Schemas } from "@/lib/api/client"
import { formatDate } from "@/lib/format"
import { cn } from "@/lib/utils"
import { yearsQueryKey, type AcademicYear } from "@/lib/year"

type Mode = "empty" | "copy"
type Preview = Schemas["CopyPreviewOut"]

const STEPS = ["years.wizard.step1", "years.wizard.step2", "years.wizard.step3", "years.wizard.step4"] as const

export function CreateYearWizard({ open, onOpenChange, years }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  years: AcademicYear[]
}) {
  const t = useT()
  const router = useRouter()
  const queryClient = useQueryClient()
  const suggested = useMemo(
    () => (years.length ? Math.max(...years.map((y) => y.start_year)) + 1 : new Date().getFullYear()),
    [years],
  )
  const [step, setStep] = useState(0)
  const [startYear, setStartYear] = useState<number>(suggested)
  const [mode, setMode] = useState<Mode>(years.length ? "copy" : "empty")
  const [sourceId, setSourceId] = useState<string>(years.find((y) => y.is_current)?.id ?? years[0]?.id ?? "")
  const [options, setOptions] = useState({ semesters: true, norms: true, employment: true, groups: true })
  const [preview, setPreview] = useState<Preview | null>(null)
  const [error, setError] = useState<string | null>(null)

  const body = {
    start_year: startYear,
    mode,
    source_year_id: mode === "copy" ? sourceId || null : null,
    options,
  }

  function reset() {
    setStep(0)
    setStartYear(suggested)
    setMode(years.length ? "copy" : "empty")
    setPreview(null)
    setError(null)
  }

  const previewMutation = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/academic-years/preview", { body })),
    onSuccess: (data) => {
      setPreview(data)
      setError(null)
      setStep(3)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  })

  const createMutation = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/academic-years", { body })),
    onSuccess: async (year) => {
      await queryClient.invalidateQueries({ queryKey: yearsQueryKey })
      toast.success(t("years.wizard.created", { label: year.label }))
      onOpenChange(false)
      reset()
      router.push(`/academic-years/${year.id}`)
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  })

  const validYear = Number.isInteger(startYear) && startYear >= 2000 && startYear <= 2100
  const canNext = step === 0 ? validYear : step === 1 ? mode === "empty" || !!sourceId : true

  function next() {
    setError(null)
    if (step === 1 && mode === "empty") return previewMutation.mutate()
    if (step === 2) return previewMutation.mutate()
    setStep((s) => s + 1)
  }

  function back() {
    setError(null)
    setStep((s) => (s === 3 && mode === "empty" ? 1 : s - 1))
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) reset() }}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><CalendarPlus className="size-5 text-primary" /> {t("years.create")}</DialogTitle>
          <DialogDescription>{t("years.subtitle")}</DialogDescription>
        </DialogHeader>

        <ol className="grid grid-cols-4 gap-2">
          {STEPS.map((key, i) => (
            <li key={key} className="flex flex-col gap-1.5">
              <div className={cn("h-1 rounded-full", i <= step ? "bg-primary" : "bg-muted")} />
              <span className={cn("text-xs", i === step ? "font-medium" : "text-muted-foreground")}>{i + 1}. {t(key)}</span>
            </li>
          ))}
        </ol>

        <div className="min-h-52 py-2">
          {step === 0 && (
            <Field label={t("years.wizard.startYear")} htmlFor="start-year"
              hint={validYear ? `${startYear}–${startYear + 1}` : undefined}>
              <Input id="start-year" type="number" min={2000} max={2100} value={startYear}
                onChange={(e) => setStartYear(Number(e.target.value))} className="max-w-40 tabular-nums" />
            </Field>
          )}

          {step === 1 && (
            <div className="grid gap-3">
              {([
                ["empty", FilePlus2, "years.wizard.modeEmpty", "years.wizard.modeEmptyHint"],
                ["copy", Copy, "years.wizard.modeCopy", "years.wizard.modeCopyHint"],
              ] as const).map(([value, Icon, title, hint]) => (
                <button key={value} type="button" disabled={value === "copy" && !years.length}
                  onClick={() => setMode(value)}
                  className={cn("flex items-start gap-3 rounded-xl border p-4 text-left transition-colors disabled:opacity-50",
                    mode === value ? "border-primary bg-primary/5 ring-1 ring-primary" : "hover:bg-muted/50")}>
                  <Icon className="mt-0.5 size-5 text-primary" />
                  <span>
                    <span className="block text-sm font-medium">{t(title)}</span>
                    <span className="block text-xs text-muted-foreground">{t(hint)}</span>
                  </span>
                </button>
              ))}
              {mode === "copy" && (
                <Field label={t("years.wizard.sourceYear")} htmlFor="source-year">
                  <NativeSelect id="source-year" value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
                    {years.map((y) => (
                      <option key={y.id} value={y.id}>{y.label} — {t(`year.statuses.${y.status}`)}</option>
                    ))}
                  </NativeSelect>
                </Field>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="grid gap-2">
              {(["semesters", "norms", "employment", "groups"] as const).map((key) => (
                <label key={key} className="flex items-start gap-3 rounded-lg border p-3 text-sm">
                  <Checkbox checked={options[key]} className="mt-0.5"
                    onCheckedChange={(v) => setOptions((o) => ({ ...o, [key]: v === true }))} />
                  <span>
                    <span className="block font-medium">{t(`years.wizard.copy.${key}`)}</span>
                    <span className="block text-xs text-muted-foreground">{t(`years.wizard.copyHint.${key}`)}</span>
                  </span>
                </label>
              ))}
            </div>
          )}

          {step === 3 && preview && (
            <div className="grid gap-3 text-sm">
              {preview.already_exists && (
                <Alert variant="destructive"><AlertDescription>{t("years.wizard.exists")}</AlertDescription></Alert>
              )}
              <div className="rounded-xl border bg-muted/30 p-4">
                <p className="font-medium">{t("years.wizard.willCreate", { label: preview.label })}</p>
                <p className="mt-1 text-muted-foreground">
                  {formatDate(preview.starts_on)} — {formatDate(preview.ends_on)}
                  {preview.source_label && ` · ${t("years.source")}: ${preview.source_label}`}
                </p>
                <ul className="mt-3 space-y-1">
                  {preview.semesters.map((s) => (
                    <li key={s.term} className="flex justify-between gap-2">
                      <span>{s.name}</span>
                      <span className="tabular-nums text-muted-foreground">{formatDate(s.starts_on)} — {formatDate(s.ends_on)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              {preview.mode === "copy" && (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {(["semesters", "norms", "employment", "groups"] as const).map((key) => (
                    <div key={key} className="rounded-lg border p-2.5 text-center">
                      <div className="text-lg font-semibold tabular-nums">{preview.will_copy[key] ?? 0}</div>
                      <div className="text-[11px] text-muted-foreground">{t(`years.wizard.copy.${key}`)}</div>
                    </div>
                  ))}
                </div>
              )}
              {preview.graduates_skipped.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {t("years.wizard.graduates")}: {preview.graduates_skipped.join(", ")}
                </p>
              )}
              {preview.not_copied.length > 0 && (
                <details className="rounded-lg border p-3 text-xs text-muted-foreground">
                  <summary className="cursor-pointer font-medium text-foreground">{t("years.wizard.notCopied")}</summary>
                  <ul className="mt-2 list-disc space-y-1 pl-4">{preview.not_copied.map((n) => <li key={n}>{n}</li>)}</ul>
                </details>
              )}
              {preview.warnings.map((w) => (
                <div key={w} className="flex gap-2 rounded-lg bg-warning/10 p-3">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warning" /> {w}
                </div>
              ))}
            </div>
          )}

          {error && <Alert variant="destructive" className="mt-3"><AlertDescription>{error}</AlertDescription></Alert>}
        </div>

        <DialogFooter>
          {step > 0 && <Button variant="outline" onClick={back}>{t("common.back")}</Button>}
          {step < 3 ? (
            <Button onClick={next} disabled={!canNext || previewMutation.isPending}>
              {previewMutation.isPending && <Loader2 className="animate-spin" />} {t("common.next")}
            </Button>
          ) : (
            <Button onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !preview || preview.already_exists}>
              {createMutation.isPending ? <Loader2 className="animate-spin" /> : <Check />} {t("common.create")}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
