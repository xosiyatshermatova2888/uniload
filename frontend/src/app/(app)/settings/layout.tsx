"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"

import { PageHeader } from "@/components/common/page-header"
import { settingsTabs } from "@/components/layout/nav"
import { useT } from "@/i18n"
import { useAuth } from "@/lib/auth"
import { cn } from "@/lib/utils"

export default function SettingsLayout({ children }: { children: ReactNode }) {
  const t = useT()
  const pathname = usePathname()
  const { can } = useAuth()
  return (
    <>
      <PageHeader title={t("nav.settings")} />
      <nav className="mb-6 flex gap-1 overflow-x-auto border-b">
        {settingsTabs.filter((tab) => can(tab.permission)).map((tab) => (
          <Link key={tab.href} href={tab.href}
            className={cn("-mb-px border-b-2 px-3 py-2 text-sm whitespace-nowrap transition-colors",
              pathname.startsWith(tab.href) ? "border-primary font-medium text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}>
            {t(tab.key)}
          </Link>
        ))}
      </nav>
      {children}
    </>
  )
}
