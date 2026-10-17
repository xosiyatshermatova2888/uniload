"use client"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "next-themes"
import { useState, type ReactNode } from "react"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { I18nProvider } from "@/i18n"
import { ApiError } from "@/lib/api/client"
import { AuthProvider } from "@/lib/auth"

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            // 4xx xatolarda qayta urinish ma’nosiz (ruxsat yo‘q, topilmadi va h.k.).
            retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
          },
        },
      }),
  )
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <I18nProvider locale="uz">
          <AuthProvider>
            <TooltipProvider>
              {children}
              <Toaster richColors position="top-right" />
            </TooltipProvider>
          </AuthProvider>
        </I18nProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
