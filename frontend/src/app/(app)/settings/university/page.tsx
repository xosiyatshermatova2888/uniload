"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { toast } from "sonner"

import { Field, NativeSelect } from "@/components/common/field"
import { ErrorState, TableSkeleton } from "@/components/common/states"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { api, ApiError, unwrap } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"

export default function UniversitySettingsPage() {
  const t = useT()
  const { can, reloadMe } = useAuth()
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ["university"], queryFn: () => unwrap(api.GET("/api/v1/university")) })
  const [form, setForm] = useState({ name: "", short_name: "", stir: "", default_locale: "uz", overload: "" })
  const editable = can("settings.manage")

  useEffect(() => {
    const u = query.data
    if (!u) return
    setForm({
      name: u.name, short_name: u.short_name ?? "", stir: u.stir ?? "", default_locale: u.default_locale,
      overload: u.settings?.overload_tolerance_pct != null ? String(u.settings.overload_tolerance_pct) : "",
    })
  }, [query.data])

  const save = useMutation({
    mutationFn: () => unwrap(api.PATCH("/api/v1/university", {
      body: {
        row_version: query.data!.row_version,
        name: form.name,
        short_name: form.short_name || null,
        stir: form.stir || null,
        default_locale: form.default_locale as "uz" | "ru" | "en",
        settings: { overload_tolerance_pct: form.overload === "" ? null : Number(form.overload) },
      },
    })),
    onSuccess: async () => {
      toast.success(t("common.saved"))
      await queryClient.invalidateQueries({ queryKey: ["university"] })
      await reloadMe()
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : String(e)),
  })

  if (query.isLoading) return <TableSkeleton />
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  return (
    <Card className="max-w-3xl">
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <Field label={t("university.code")}><Input value={query.data!.code} disabled /></Field>
        <Field label={t("university.stir")} htmlFor="stir">
          <Input id="stir" value={form.stir} onChange={set("stir")} disabled={!editable} inputMode="numeric" maxLength={9} />
        </Field>
        <Field label={t("university.name")} htmlFor="name" className="sm:col-span-2">
          <Input id="name" value={form.name} onChange={set("name")} disabled={!editable} />
        </Field>
        <Field label={t("university.shortName")} htmlFor="short">
          <Input id="short" value={form.short_name} onChange={set("short_name")} disabled={!editable} />
        </Field>
        <Field label={t("university.locale")} htmlFor="locale" hint="Rus va ingliz tillari keyingi bosqichda">
          <NativeSelect id="locale" value={form.default_locale} onChange={set("default_locale")} disabled={!editable}>
            <option value="uz">O‘zbekcha</option>
            <option value="ru">Русский</option>
            <option value="en">English</option>
          </NativeSelect>
        </Field>
        <Field label={t("university.overloadTolerance")} htmlFor="overload" hint={t("university.overloadHint")} className="sm:col-span-2">
          <Input id="overload" type="number" min={0} max={100} value={form.overload} onChange={set("overload")}
            disabled={!editable} className="max-w-32" />
        </Field>
      </CardContent>
      {editable && (
        <CardFooter className="justify-end">
          <Button onClick={() => save.mutate()} disabled={save.isPending}>{t("common.save")}</Button>
        </CardFooter>
      )}
    </Card>
  )
}
