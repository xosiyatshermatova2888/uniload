"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { GraduationCap, Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { Field } from "@/components/common/field"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useT } from "@/i18n"
import { ApiError } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"

const schema = z.object({ email: z.string().email(), password: z.string().min(1) })

export default function LoginPage() {
  const t = useT()
  const router = useRouter()
  const { status, login } = useAuth()
  const form = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } })

  useEffect(() => {
    if (status === "authenticated") router.replace("/")
  }, [status, router])

  async function submit(values: z.infer<typeof schema>) {
    try {
      await login(values.email, values.password)
      router.replace("/")
    } catch (e) {
      form.setError("root", { message: e instanceof ApiError ? e.message : String(e) })
    }
  }

  const { errors, isSubmitting } = form.formState
  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/40 px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2.5">
          <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <GraduationCap className="size-5" />
          </span>
          <div>
            <div className="text-lg leading-tight font-semibold">{t("app.name")}</div>
            <div className="text-xs text-muted-foreground">{t("app.tagline")}</div>
          </div>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">{t("auth.title")}</CardTitle>
            <CardDescription>{t("auth.subtitle")}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={form.handleSubmit(submit)} className="grid gap-4" noValidate>
              {errors.root && (
                <Alert variant="destructive"><AlertDescription>{errors.root.message}</AlertDescription></Alert>
              )}
              <Field label={t("auth.email")} htmlFor="email" error={errors.email && " "}>
                <Input id="email" type="email" autoComplete="username" autoFocus {...form.register("email")} />
              </Field>
              <Field label={t("auth.password")} htmlFor="password" error={errors.password && " "}>
                <Input id="password" type="password" autoComplete="current-password" {...form.register("password")} />
              </Field>
              <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
                {isSubmitting && <Loader2 className="animate-spin" />}
                {t("auth.submit")}
              </Button>
            </form>
          </CardContent>
        </Card>
        <p className="mt-4 text-center text-xs text-muted-foreground">{t("auth.demoHint")}</p>
      </div>
    </div>
  )
}
