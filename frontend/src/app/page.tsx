"use client"

import { Loader2 } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

import { useAuth } from "@/lib/auth"

export default function Home() {
  const router = useRouter()
  const { status, me } = useAuth()

  useEffect(() => {
    if (status === "anonymous") router.replace("/login")
    if (status === "authenticated") router.replace(me?.is_platform_admin ? "/platform/universities" : "/dashboard")
  }, [status, me, router])

  return (
    <div className="flex min-h-svh items-center justify-center">
      <Loader2 className="size-5 animate-spin text-muted-foreground" />
    </div>
  )
}
