"use client"

import { GraduationCap } from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useT } from "@/i18n"
import { useAuth } from "@/lib/auth"

import { platformNav, settingsTabs, tenantNav, type NavItem } from "./nav"

export function AppSidebar() {
  const t = useT()
  const pathname = usePathname()
  const { me, can } = useAuth()
  const sections = me?.is_platform_admin ? platformNav : tenantNav

  const visible = (item: NavItem) => {
    if (!item.permission) return true
    // Sozlamalar: istalgan sozlama yorlig‘iga ruxsat bo‘lsa ko‘rinadi.
    if (item.href === "/settings") return settingsTabs.some((tab) => can(tab.permission))
    return can(item.permission)
  }

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="h-14 justify-center border-b">
        <Link href="/" className="flex items-center gap-2 px-1.5 group-data-[collapsible=icon]:px-0">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="size-4.5" />
          </span>
          <span className="min-w-0 group-data-[collapsible=icon]:hidden">
            <span className="block text-sm leading-tight font-semibold">{t("app.name")}</span>
            <span className="block truncate text-xs text-muted-foreground">
              {me?.university?.short_name ?? me?.university?.name ?? t("nav.platform")}
            </span>
          </span>
        </Link>
      </SidebarHeader>
      <SidebarContent>
        {sections.map((section) => {
          const items = section.items.filter(visible)
          if (!items.length) return null
          return (
            <SidebarGroup key={section.title}>
              <SidebarGroupLabel>{t(section.title)}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {items.map((item) => {
                    const ready = item.phase <= 1
                    const active = pathname === item.href || pathname.startsWith(`${item.href}/`)
                    const label = t(item.key)
                    return (
                      <SidebarMenuItem key={item.href}>
                        {ready ? (
                          <SidebarMenuButton isActive={active} tooltip={label} render={<Link href={item.href} />}>
                            <item.icon />
                            <span>{label}</span>
                          </SidebarMenuButton>
                        ) : (
                          <>
                            <SidebarMenuButton aria-disabled tooltip={`${label} — ${t("nav.soon", { phase: item.phase })}`}>
                              <item.icon />
                              <span>{label}</span>
                            </SidebarMenuButton>
                            <SidebarMenuBadge className="text-[10px] text-muted-foreground">
                              {t("nav.soon", { phase: item.phase })}
                            </SidebarMenuBadge>
                          </>
                        )}
                      </SidebarMenuItem>
                    )
                  })}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })}
      </SidebarContent>
      <SidebarFooter className="px-3 pb-3 text-[11px] text-muted-foreground group-data-[collapsible=icon]:hidden">
        v0.1 · 1-bosqich
      </SidebarFooter>
    </Sidebar>
  )
}
