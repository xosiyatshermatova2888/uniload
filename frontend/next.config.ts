import type { NextConfig } from "next"

// Brauzer API’ga shu origin orqali murojaat qiladi (/api/v1/...), Next.js uni backendga uzatadi.
// Shu sababli refresh cookie `SameSite=Strict` bilan ishlaydi va CORS kerak bo‘lmaydi.
const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000"

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${apiUrl}/api/v1/:path*` }]
  },
}

export default nextConfig
