"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { toast } from "sonner"
import { z } from "zod"

import { Field } from "@/components/common/field"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { api, ApiError, unwrap } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"

const passwordRule = z.string().min(8).regex(/[A-Za-z]/).regex(/\d/)

export function ChangePasswordDialog({
  open, onOpenChange, forced = false,
}: { open: boolean; onOpenChange: (open: boolean) => void; forced?: boolean }) {
  const t = useT()
  const { reloadMe } = useAuth()
  const schema = z
    .object({ current: z.string().min(1), next: passwordRule, repeat: z.string() })
    .refine((v) => v.next === v.repeat, { path: ["repeat"], message: t("auth.passwordsDiffer") })
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { current: "", next: "", repeat: "" } })

  async function submit(values: z.infer<typeof schema>) {
    try {
      await unwrap(api.POST("/api/v1/auth/password/change", {
        body: { current_password: values.current, new_password: values.next },
      }))
      toast.success(t("auth.passwordChanged"))
      form.reset()
      await reloadMe()
      onOpenChange(false)
    } catch (e) {
      form.setError("root", { message: e instanceof ApiError ? e.message : String(e) })
    }
  }

  const errors = form.formState.errors
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (forced && !next) return // majburiy almashtirishni yopib bo‘lmaydi
        onOpenChange(next)
      }}
    >
      <DialogContent showCloseButton={!forced}>
        <DialogHeader>
          <DialogTitle>{t("auth.changePassword")}</DialogTitle>
          {forced && <DialogDescription>{t("auth.mustChange")}</DialogDescription>}
        </DialogHeader>
        <form id="change-password" onSubmit={form.handleSubmit(submit)} className="grid gap-4">
          {errors.root && (
            <Alert variant="destructive"><AlertDescription>{errors.root.message}</AlertDescription></Alert>
          )}
          <Field label={t("auth.currentPassword")} htmlFor="cp-current" error={errors.current && " "}>
            <Input id="cp-current" type="password" autoComplete="current-password" {...form.register("current")} />
          </Field>
          <Field label={t("auth.newPassword")} htmlFor="cp-next" hint={t("auth.passwordRule")}
            error={errors.next && t("auth.passwordRule")}>
            <Input id="cp-next" type="password" autoComplete="new-password" {...form.register("next")} />
          </Field>
          <Field label={t("auth.repeatPassword")} htmlFor="cp-repeat" error={errors.repeat?.message}>
            <Input id="cp-repeat" type="password" autoComplete="new-password" {...form.register("repeat")} />
          </Field>
        </form>
        <DialogFooter>
          {!forced && <Button variant="outline" onClick={() => onOpenChange(false)}>{t("common.cancel")}</Button>}
          <Button type="submit" form="change-password" disabled={form.formState.isSubmitting}>
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
