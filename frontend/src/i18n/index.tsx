"use client"

import { createContext, useCallback, useContext, type ReactNode } from "react"

import { uz, type Messages } from "./uz"

export type Locale = "uz" | "ru" | "en"

// ru/en tarjimalari qo‘shilganda shu yerga ulanadi; hozircha barcha tillar o‘zbekchaga tushadi.
const catalogs: Record<Locale, Messages> = { uz, ru: uz, en: uz }

type Leaves<T, P extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${P}${K}` : Leaves<T[K], `${P}${K}.`>
}[keyof T & string]

export type MessageKey = Leaves<Messages>

const I18nContext = createContext<Locale>("uz")

export function I18nProvider({ locale = "uz", children }: { locale?: Locale; children: ReactNode }) {
  return <I18nContext.Provider value={locale}>{children}</I18nContext.Provider>
}

// Kalitlarning o‘zida nuqta bo‘lishi mumkin (masalan, audit.“auth.login”), shuning uchun eng uzun moslik qidiriladi.
function lookup(node: unknown, parts: string[]): unknown {
  if (!parts.length) return node
  if (!node || typeof node !== "object") return undefined
  for (let i = parts.length; i >= 1; i--) {
    const key = parts.slice(0, i).join(".")
    if (key in node) {
      const found = lookup((node as Record<string, unknown>)[key], parts.slice(i))
      if (found !== undefined) return found
    }
  }
  return undefined
}

export function translate(locale: Locale, key: string, vars?: Record<string, string | number>): string {
  const value = lookup(catalogs[locale], key.split("."))
  if (typeof value !== "string") return key
  return vars ? value.replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? `{${name}}`)) : value
}

export function useT() {
  const locale = useContext(I18nContext)
  return useCallback(
    (key: MessageKey | (string & {}), vars?: Record<string, string | number>) => translate(locale, key, vars),
    [locale],
  )
}
