"use client"

import { useState, type ReactNode } from "react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useT } from "@/i18n"

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: ReactNode
  confirmLabel?: string
  destructive?: boolean
  children?: ReactNode
  /** Xato bo‘lsa oyna ochiq qoladi; xato xabari chaqiruvchida ko‘rsatiladi. */
  onConfirm: () => Promise<unknown> | unknown
  confirmDisabled?: boolean
}

/** Barcha muhim amallar uchun yagona tasdiqlash oynasi. */
export function ConfirmDialog({
  open, onOpenChange, title, description, confirmLabel, destructive, children, onConfirm, confirmDisabled,
}: ConfirmDialogProps) {
  const t = useT()
  const [busy, setBusy] = useState(false)

  async function handleConfirm() {
    setBusy(true)
    try {
      await onConfirm()
      onOpenChange(false)
    } catch {
      /* chaqiruvchi xabarni ko‘rsatadi */
    } finally {
      setBusy(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => !busy && onOpenChange(next)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description && <AlertDialogDescription>{description}</AlertDialogDescription>}
        </AlertDialogHeader>
        {children}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={busy}>{t("common.cancel")}</AlertDialogCancel>
          <AlertDialogAction
            variant={destructive ? "destructive" : "default"}
            disabled={busy || confirmDisabled}
            onClick={handleConfirm}
          >
            {busy ? t("common.loading") : (confirmLabel ?? t("common.confirm"))}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
