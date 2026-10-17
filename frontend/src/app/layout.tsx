import type { Metadata } from "next"
import { Inter } from "next/font/google"

import { Providers } from "@/components/providers"

import "./globals.css"

const inter = Inter({ subsets: ["latin", "latin-ext", "cyrillic"], variable: "--font-sans" })

export const metadata: Metadata = {
  title: { default: "UniLoad", template: "%s · UniLoad" },
  description: "Universitet o‘quv yuklamalarini avtomatlashtirish platformasi",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz" suppressHydrationWarning>
      <body className={`${inter.variable} antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
