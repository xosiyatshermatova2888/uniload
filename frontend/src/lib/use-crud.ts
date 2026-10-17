"use client"

import { useQueryClient, type QueryKey } from "@tanstack/react-query"
import { useCallback } from "react"
import { toast } from "sonner"

import { useT } from "@/i18n"
import { ApiError } from "@/lib/api/client"

/** Amalni bajaradi, kesh kalitlarini yangilaydi va natijani toast bilan ko‘rsatadi.
 *  Xato qayta ko‘tariladi — formalar va tasdiqlash oynalari ochiq qoladi. */
export function useRun(...keys: QueryKey[]) {
  const t = useT()
  const queryClient = useQueryClient()
  return useCallback(
    async <T>(action: () => Promise<T>, success?: string): Promise<T> => {
      try {
        const result = await action()
        await Promise.all(keys.map((queryKey) => queryClient.invalidateQueries({ queryKey })))
        toast.success(success ?? t("ref.saved"))
        return result
      } catch (e) {
        toast.error(e instanceof ApiError ? e.message : String(e))
        throw e
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [queryClient, t, ...keys.map((k) => JSON.stringify(k))],
  )
}
