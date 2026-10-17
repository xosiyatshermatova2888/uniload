"use client"

import { Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, type ReactNode } from "react"

import { AppSidebar } from "@/components/layout/app-sidebar"
import { ChangePasswordDialog } from "@/components/layout/change-password-dialog"
import { Topbar } from "@/components/layout/topbar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { useT } from "@/i18n"
import { useAuth } from "@/lib/auth"
import { YearProvider } from "@/lib/year"

export default function AppLayout({ children }: { children: ReactNode }) {
  const t = useT()
  const router = useRouter()
  const { status, me } = useAuth()

  useEffect(() => {
    if (status === "anonymous") router.replace("/login")
  }, [status, router])

  if (status !== "authenticated" || !me) {
    return (
      <div className="flex min-h-svh items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> {t("common.loading")}
      </div>
    )
  }

  return (
    <YearProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="bg-background">
          <Topbar />
          <div className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </SidebarInset>
      </SidebarProvider>
      <ChangePasswordDialog open={me.must_change_password} onOpenChange={() => undefined} forced />
    </YearProvider>
  )
}
