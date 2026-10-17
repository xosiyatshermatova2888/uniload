"use client"

import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table"
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react"
import { useState, type ReactNode } from "react"

import { EmptyState } from "@/components/common/states"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useT } from "@/i18n"
import { cn } from "@/lib/utils"

interface DataTableProps<T> {
  columns: ColumnDef<T, unknown>[]
  data: T[]
  searchable?: boolean
  /** Server tomonidan qidiruv bo‘lsa — tashqaridan boshqariladi. */
  search?: string
  onSearchChange?: (value: string) => void
  toolbar?: ReactNode
  footer?: ReactNode
  onRowClick?: (row: T) => void
  empty?: ReactNode
}

/** TanStack Table asosidagi umumiy jadval: saralash, qidiruv, bo‘sh holat. */
export function DataTable<T>({
  columns, data, searchable = true, search, onSearchChange, toolbar, footer, onRowClick, empty,
}: DataTableProps<T>) {
  const t = useT()
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState("")
  const serverSearch = onSearchChange !== undefined

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter: serverSearch ? "" : globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  return (
    <div className="space-y-3">
      {(searchable || toolbar) && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          {searchable ? (
            <div className="relative w-full sm:max-w-xs">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={serverSearch ? (search ?? "") : globalFilter}
                onChange={(e) => (serverSearch ? onSearchChange?.(e.target.value) : setGlobalFilter(e.target.value))}
                placeholder={t("common.search")}
                className="pl-8"
              />
            </div>
          ) : (
            <span />
          )}
          {toolbar && <div className="flex flex-wrap gap-2">{toolbar}</div>}
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border bg-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((group) => (
              <TableRow key={group.id} className="hover:bg-transparent">
                {group.headers.map((header) => {
                  const sortable = header.column.getCanSort()
                  const dir = header.column.getIsSorted()
                  return (
                    <TableHead key={header.id} className="h-10 text-xs font-medium text-muted-foreground">
                      {header.isPlaceholder ? null : sortable ? (
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 hover:text-foreground"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {dir === "asc" ? <ArrowUp className="size-3" /> : dir === "desc" ? <ArrowDown className="size-3" /> : <ArrowUpDown className="size-3 opacity-40" />}
                        </button>
                      ) : (
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={cn(onRowClick && "cursor-pointer")}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className="py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={columns.length} className="p-4">
                  {empty ?? <EmptyState />}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {footer}
    </div>
  )
}
