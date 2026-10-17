"use client"

import { useQuery } from "@tanstack/react-query"
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react"

import { api, unwrap, type Schemas } from "@/lib/api/client"
import { useAuth } from "@/lib/auth"

export type AcademicYear = Schemas["AcademicYearOut"]

interface YearState {
  years: AcademicYear[]
  year: AcademicYear | null
  isLoading: boolean
  select: (id: string) => void
}

const YearContext = createContext<YearState | null>(null)
const STORAGE_KEY = "uniload.selectedYear"

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function writeStored(id: string) {
  try {
    window.localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* brauzer xotirasi mavjud bo‘lmasa — tanlov faqat shu sessiyada saqlanadi */
  }
}

export const yearsQueryKey = ["academic-years"] as const

export function useYearsQuery(enabled = true) {
  return useQuery({
    queryKey: yearsQueryKey,
    queryFn: () => unwrap(api.GET("/api/v1/academic-years")),
    enabled,
  })
}

/** Global tanlangan o‘quv yili (YearSwitcher). Yilga bog‘liq sahifalar shu yil bilan ishlaydi. */
export function YearProvider({ children }: { children: ReactNode }) {
  const { me, can } = useAuth()
  const enabled = !!me?.university && can("academic_year.view")
  const { data = [], isLoading } = useYearsQuery(enabled)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    setSelectedId(readStored())
  }, [])

  const year = useMemo(() => {
    if (!data.length) return null
    return data.find((y) => y.id === selectedId) ?? data.find((y) => y.is_current) ?? data[0]
  }, [data, selectedId])

  const select = useCallback((id: string) => {
    setSelectedId(id)
    writeStored(id)
  }, [])

  const value = useMemo(() => ({ years: data, year, isLoading: enabled && isLoading, select }), [data, year, enabled, isLoading, select])
  return <YearContext.Provider value={value}>{children}</YearContext.Provider>
}

export function useYear(): YearState {
  const ctx = useContext(YearContext)
  if (!ctx) throw new Error("useYear YearProvider ichida ishlatilishi kerak")
  return ctx
}
