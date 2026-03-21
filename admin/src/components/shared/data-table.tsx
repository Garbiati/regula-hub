"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface DataTableProps<TData> {
  columns: ColumnDef<TData, unknown>[];
  data: TData[];
  pageSize?: number;
  enableColumnFilters?: boolean;
  enableSorting?: boolean;
  onRowClick?: (row: TData) => void;
}

const PAGE_SIZES = [25, 50, 100];

export function DataTable<TData>({
  columns,
  data,
  pageSize = 50,
  enableColumnFilters = true,
  enableSorting = true,
  onRowClick,
}: DataTableProps<TData>) {
  const t = useTranslations();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [showAll, setShowAll] = useState(false);

  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table API is safe here
  const table = useReactTable({
    data,
    columns,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    ...(enableSorting && { getSortedRowModel: getSortedRowModel() }),
    ...(enableColumnFilters && { getFilteredRowModel: getFilteredRowModel() }),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  // "Show all" sets page size to data length, effectively disabling pagination
  const effectiveShowAll = showAll || table.getState().pagination.pageSize >= data.length;
  const totalFiltered = table.getFilteredRowModel().rows.length;
  const currentPage = table.getState().pagination.pageIndex;
  const currentPageSize = table.getState().pagination.pageSize;
  const from = currentPage * currentPageSize + 1;
  const to = Math.min((currentPage + 1) * currentPageSize, totalFiltered);

  return (
    <div className="space-y-2">
      {/* Pagination controls top */}
      <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
        <span>
          {t("table.showing", { from, to, total: totalFiltered })}
          {totalFiltered !== data.length && (
            <span className="ml-1 text-[var(--text-tertiary)]">
              ({data.length} {t("agendamentos.total_records")})
            </span>
          )}
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[var(--text-tertiary)]">{t("table.page_size")}:</span>
          {PAGE_SIZES.map((size) => (
            <button
              key={size}
              type="button"
              onClick={() => { setShowAll(false); table.setPageSize(size); table.setPageIndex(0); }}
              className={cn(
                "px-2 py-0.5 rounded-md transition-colors",
                !showAll && currentPageSize === size
                  ? "bg-[var(--accent-indigo)] text-white"
                  : "hover:bg-[var(--glass-surface-hover)]",
              )}
            >
              {size}
            </button>
          ))}
          <button
            type="button"
            onClick={() => { setShowAll(true); table.setPageSize(data.length || 1); table.setPageIndex(0); }}
            className={cn(
              "px-2 py-0.5 rounded-md transition-colors",
              effectiveShowAll
                ? "bg-[var(--accent-indigo)] text-white"
                : "hover:bg-[var(--glass-surface-hover)]",
            )}
          >
            {t("table.all_rows")}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="max-h-[600px] overflow-auto glass-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="whitespace-nowrap align-bottom">
                    {header.isPlaceholder ? null : (
                      <div className="space-y-1">
                        {/* Header label + sort button */}
                        <div
                          className={cn(
                            "flex items-center gap-1",
                            enableSorting && header.column.getCanSort() && "cursor-pointer select-none",
                          )}
                          onClick={enableSorting ? header.column.getToggleSortingHandler() : undefined}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {enableSorting && header.column.getCanSort() && (
                            <span className="text-[var(--text-tertiary)]">
                              {header.column.getIsSorted() === "asc" ? (
                                <ArrowUp className="h-3 w-3" />
                              ) : header.column.getIsSorted() === "desc" ? (
                                <ArrowDown className="h-3 w-3" />
                              ) : (
                                <ArrowUpDown className="h-3 w-3" />
                              )}
                            </span>
                          )}
                        </div>
                        {/* Column filter input */}
                        {enableColumnFilters && header.column.getCanFilter() && (
                          <input
                            type="text"
                            value={(header.column.getFilterValue() as string) ?? ""}
                            onChange={(e) => header.column.setFilterValue(e.target.value)}
                            placeholder={t("table.filter_placeholder")}
                            className={cn(
                              "w-full px-1.5 py-0.5 text-[11px] rounded-md",
                              "bg-[var(--glass-surface)] border border-[var(--glass-border-subtle)]",
                              "text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]",
                              "focus:outline-none focus:border-[var(--accent-indigo)]",
                            )}
                          />
                        )}
                      </div>
                    )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className={cn(onRowClick && "cursor-pointer hover:bg-[var(--glass-surface-hover)] transition-colors")}
                  onClick={() => onRowClick?.(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-[var(--text-tertiary)]">
                  {t("table.no_results")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination controls bottom */}
      {!effectiveShowAll && table.getPageCount() > 1 && (
        <div className="flex items-center justify-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            className="px-2 py-1 rounded-md hover:bg-[var(--glass-surface-hover)] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {"<<"}
          </button>
          <button
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-2 py-1 rounded-md hover:bg-[var(--glass-surface-hover)] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {"<"}
          </button>
          <span className="text-[var(--text-secondary)]">
            {currentPage + 1} / {table.getPageCount()}
          </span>
          <button
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-2 py-1 rounded-md hover:bg-[var(--glass-surface-hover)] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {">"}
          </button>
          <button
            type="button"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            className="px-2 py-1 rounded-md hover:bg-[var(--glass-surface-hover)] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {">>"}
          </button>
        </div>
      )}
    </div>
  );
}
