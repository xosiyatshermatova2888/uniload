import createClient from "openapi-fetch"

import type { components, paths } from "./schema"

export type Schemas = components["schemas"]

/** Backend RFC 7807 xatosi. `code` frontend’da tarjima va mantiq uchun ishlatiladi. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public errors: Array<Record<string, unknown>> = [],
    public requestId?: string,
  ) {
    super(message)
  }
}

// Access token faqat xotirada saqlanadi (localStorage’da emas) — XSS’dan himoya.
let accessToken: string | null = null
let refreshHandler: (() => Promise<boolean>) | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setRefreshHandler(handler: (() => Promise<boolean>) | null) {
  refreshHandler = handler
}

async function authFetch(input: Request): Promise<Response> {
  const send = () => {
    const req = input.clone()
    if (accessToken) req.headers.set("Authorization", `Bearer ${accessToken}`)
    return fetch(req)
  }
  let response = await send()
  if (response.status === 401 && refreshHandler) {
    const body = await response.clone().json().catch(() => null)
    if (body?.code === "TOKEN_EXPIRED" && (await refreshHandler())) {
      response = await send()
    }
  }
  return response
}

export const api = createClient<paths>({ baseUrl: "", fetch: authFetch })

export async function toApiError(response: Response, error?: unknown): Promise<ApiError> {
  const body = (error ?? (await response.clone().json().catch(() => null))) as
    | { code?: string; detail?: string | null; title?: string; errors?: Array<Record<string, unknown>>; request_id?: string }
    | null
  const message = body?.detail || body?.title || `So‘rov bajarilmadi (${response.status})`
  return new ApiError(response.status, body?.code ?? "HTTP_ERROR", message, body?.errors ?? [], body?.request_id)
}

/** openapi-fetch natijasini “data yoki ApiError” ko‘rinishiga keltiradi. */
export async function unwrap<T>(promise: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await promise
  if (!response.ok) throw await toApiError(response, error)
  return data as T
}
