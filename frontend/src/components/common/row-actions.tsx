"use client"

import { MoreHorizontal, Pencil, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { useT } from "@/i18n"

/** Jadval qatori amallari: tahrirlash, o‘chirish va qo‘shimcha bandlar. */
export function RowActions({ onEdit, onDelete, children }: { onEdit?: () => void; onDelete?: () => void; children?: ReactNode }) {
  const t = useT()
  if (!onEdit && !onDelete && !children) return null
  return (
    <div onClick={(e) => e.stopPropagation()} className="flex justify-end">
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label={t("common.actions")} />}>
          <MoreHorizontal />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          {onEdit && <DropdownMenuItem onClick={onEdit}><Pencil /> {t("common.edit")}</DropdownMenuItem>}
          {children}
          {onDelete && <DropdownMenuItem variant="destructive" onClick={onDelete}><Trash2 /> {t("common.delete")}</DropdownMenuItem>}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
