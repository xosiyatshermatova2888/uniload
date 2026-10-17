import type { ReactNode } from "react"

import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

/** Forma maydoni: yorliq, izoh va xato xabari bilan. */
export function Field({
  label, htmlFor, error, hint, children, className,
}: { label: string; htmlFor?: string; error?: string; hint?: string; children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : (
        hint && <p className="text-xs text-muted-foreground">{hint}</p>
      )}
    </div>
  )
}

/** Base UI Select o‘rniga oddiy, ishonchli native select (forma ichida). */
export function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50 dark:bg-input/30",
        className,
      )}
      {...props}
    />
  )
}
