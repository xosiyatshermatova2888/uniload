"use client"

import { useQueryClient } from "@tanstack/react-query"
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react"

import { api, setAccessToken, setRefreshHandler, toApiError, unwrap, type Schemas } from "@/lib/api/client"

export type Me = Schemas["MeOut"]
type TokenOut = Schemas["TokenOut"]
type Status = "loading" | "authenticated" | "anonymous"

interface AuthState {
  status: Status
  me: Me | null
  login: (email: string, password: string) => Promise<Me>
  logout: () => Promise<void>
  reloadMe: () => Promise<void>
  can: (permission: string) => boolean
}

const AuthContext = createContext<AuthState | null>(null)

// Bir vaqtda bir nechta refresh (masalan, React StrictMode yoki parallel 401) refresh tokenni
// ikki marta ishlatib, butun sessiya zanjirini bekor qilmasligi uchun — yagona “in-flight” so‘rov.
let inflight: Promise<TokenOut | null> | null = null

function requestRefresh(): Promise<TokenOut | null> {
  inflight ??= fetch("/api/v1/auth/refresh", { method: "POST", credentials: "same-origin" })
    .then(async (r) => (r.ok ? ((await r.json()) as TokenOut) : null))
    .catch(() => null)
    .finally(() => setTimeout(() => (inflight = null), 0))
  return inflight
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<Status>("loading")
  const [me, setMe] = useState<Me | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clear = useCallback(() => {
    if (timer.current) clearTimeout(timer.current)
    setAccessToken(null)
    setMe(null)
    setStatus("anonymous")
  }, [])

  // refresh ↔ apply bir-biriga murojaat qiladi; aylanma bog‘liqlikni ref orqali uzamiz.
  const applyRef = useRef<(token: TokenOut) => void>(() => undefined)

  const refresh = useCallback(async (): Promise<boolean> => {
    const token = await requestRefresh()
    if (!token) {
      clear()
      return false
    }
    applyRef.current(token)
    return true
  }, [clear])

  const apply = useCallback(
    (token: TokenOut) => {
      setAccessToken(token.access_token)
      setMe(token.user)
      setStatus("authenticated")
      if (timer.current) clearTimeout(timer.current)
      // Access token tugashidan bir daqiqa oldin jimgina yangilanadi.
      timer.current = setTimeout(() => void refresh(), Math.max(token.expires_in - 60, 30) * 1000)
    },
    [refresh],
  )

  useEffect(() => {
    applyRef.current = apply
  }, [apply])

  useEffect(() => {
    setRefreshHandler(refresh)
    void refresh()
    return () => setRefreshHandler(null)
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
      if (!response.ok) throw await toApiError(response)
      const token = (await response.json()) as TokenOut
      queryClient.clear()
      apply(token)
      return token.user
    },
    [apply, queryClient],
  )

  const logout = useCallback(async () => {
    await fetch("/api/v1/auth/logout", { method: "POST", credentials: "same-origin" }).catch(() => undefined)
    queryClient.clear()
    clear()
  }, [clear, queryClient])

  const reloadMe = useCallback(async () => {
    setMe(await unwrap(api.GET("/api/v1/auth/me")))
  }, [])

  const can = useCallback((permission: string) => !!me?.permissions.includes(permission), [me])

  const value = useMemo(() => ({ status, me, login, logout, reloadMe, can }), [status, me, login, logout, reloadMe, can])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth AuthProvider ichida ishlatilishi kerak")
  return ctx
}
