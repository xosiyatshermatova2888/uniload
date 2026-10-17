"use client"

import { Check, ChevronDown, KeyRound, LogOut, Monitor, Moon, Sun } from "lucide-react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import { useState } from "react"

import { YearStatusBadge } from "@/components/common/status-badge"
import { ChangePasswordDialog } from "@/components/layout/change-password-dialog"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { useT } from "@/i18n"
import { useAuth } from "@/lib/auth"
import { useYear } from "@/lib/year"

function YearSwitcher() {
  const t = useT()
  const { years, year, select } = useYear()
  if (!year) return <span className="text-sm text-muted-foreground">{t("year.none")}</span>
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" className="gap-2" />}>
        <span className="hidden text-muted-foreground sm:inline">{t("year.selector")}:</span>
        <span className="font-semibold tabular-nums">{year.label}</span>
        <YearStatusBadge status={year.status} className="hidden md:inline-flex" />
        <ChevronDown className="size-4 opacity-60" />
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel>{t("year.selector")}</DropdownMenuLabel>
          {years.map((y) => (
            <DropdownMenuItem key={y.id} onClick={() => select(y.id)} className="justify-between">
              <span className="flex items-center gap-2">
                <Check className={y.id === year.id ? "size-4" : "size-4 opacity-0"} />
                <span className="tabular-nums">{y.label}</span>
                {y.is_current && <span className="text-xs text-muted-foreground">({t("year.current")})</span>}
              </span>
              <YearStatusBadge status={y.status} />
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function ThemeToggle() {
  const t = useT()
  const { setTheme } = useTheme()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="ghost" size="icon" aria-label={t("theme.dark")} />}>
        <Sun className="size-4 dark:hidden" />
        <Moon className="hidden size-4 dark:block" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-36">
        <DropdownMenuItem onClick={() => setTheme("light")}><Sun /> {t("theme.light")}</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("dark")}><Moon /> {t("theme.dark")}</DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}><Monitor /> {t("theme.system")}</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function UserMenu() {
  const t = useT()
  const router = useRouter()
  const { me, logout } = useAuth()
  const [passwordOpen, setPasswordOpen] = useState(false)
  const initials = (me?.full_name ?? "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="ghost" className="h-9 gap-2 px-1.5" />}>
          <Avatar className="size-7">
            <AvatarFallback className="bg-primary/10 text-xs text-primary">{initials}</AvatarFallback>
          </Avatar>
          <span className="hidden max-w-40 truncate text-sm lg:inline">{me?.full_name}</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-60">
          <DropdownMenuGroup>
            <DropdownMenuLabel className="font-normal">
              <div className="truncate text-sm font-medium text-foreground">{me?.full_name}</div>
              <div className="truncate font-mono text-xs text-muted-foreground">{me?.username}</div>
            </DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setPasswordOpen(true)}>
            <KeyRound /> {t("auth.changePassword")}
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onClick={async () => {
              await logout()
              router.replace("/login")
            }}
          >
            <LogOut /> {t("auth.logout")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ChangePasswordDialog open={passwordOpen} onOpenChange={setPasswordOpen} />
    </>
  )
}

export function Topbar() {
  const { me } = useAuth()
  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b bg-background/85 px-4 backdrop-blur">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mx-1 h-5" />
      {me?.university && <YearSwitcher />}
      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  )
}
