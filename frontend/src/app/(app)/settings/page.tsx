"use client"

import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { settingsTabs } from "@/components/layout/nav"
import { useAuth } from "@/lib/auth"

export default function SettingsIndex() {
  const router = useRouter()
  const { can } = useAuth()
  useEffect(() => {
    const first = settingsTabs.find((tab) => can(tab.permission))
    if (first) router.replace(first.href)
  }, [can, router])
  return null
}
