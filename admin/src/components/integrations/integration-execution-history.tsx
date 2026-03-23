"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { History, ChevronLeft, ChevronRight } from "lucide-react";

import { useIntegrationHistory } from "@/hooks/use-integration-history";
import type { IntegrationExecution } from "@/types/integration";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-gray-500/10 text-gray-400",
    running: "bg-blue-500/10 text-blue-400",
    completed: "bg-emerald-500/10 text-emerald-400",
    failed: "bg-red-500/10 text-red-400",
    cancelled: "bg-amber-500/10 text-amber-400",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] ?? colors.pending}`}>
      {status}
    </span>
  );
}

function formatDuration(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt) return "-";
  const start = new Date(startedAt);
  const end = completedAt ? new Date(completedAt) : new Date();
  const diffMs = end.getTime() - start.getTime();
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

function formatDateRange(from: string, to: string): string {
  return `${from} → ${to}`;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "-";
  return new Date(ts).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const PAGE_SIZE = 10;

export function IntegrationExecutionHistory() {
  const t = useTranslations();
  const [page, setPage] = useState(0);
  const skip = page * PAGE_SIZE;
  const { data, isLoading } = useIntegrationHistory(skip, PAGE_SIZE);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="glass-card rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <History className="w-4 h-4 text-[var(--text-tertiary)]" />
        <h3 className="font-semibold text-[var(--text-primary)]">{t("integrations.history_title")}</h3>
        {total > 0 && <span className="text-xs text-[var(--text-tertiary)]">({total})</span>}
      </div>

      {isLoading ? (
        <div className="py-4 text-center text-[var(--text-tertiary)] text-sm">{t("integrations.loading")}</div>
      ) : items.length === 0 ? (
        <div className="py-4 text-center text-[var(--text-tertiary)] text-sm">
          {t("integrations.no_history")}
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[var(--text-tertiary)] border-b border-[var(--border-primary)]">
                  <th className="pb-2 pr-4">{t("integrations.col_date_range")}</th>
                  <th className="pb-2 pr-4">{t("integrations.col_status")}</th>
                  <th className="pb-2 pr-4">{t("integrations.col_fetched")}</th>
                  <th className="pb-2 pr-4">{t("integrations.col_enriched")}</th>
                  <th className="pb-2 pr-4">{t("integrations.col_pushed")}</th>
                  <th className="pb-2 pr-4">{t("integrations.col_failed")}</th>
                  <th className="pb-2 pr-4">{t("integrations.col_started")}</th>
                  <th className="pb-2">{t("integrations.col_duration")}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((ex: IntegrationExecution) => (
                  <tr key={ex.id} className="border-b border-[var(--border-primary)] last:border-0">
                    <td className="py-2.5 pr-4 font-mono text-xs">{formatDateRange(ex.dateFrom, ex.dateTo)}</td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={ex.status} />
                    </td>
                    <td className="py-2.5 pr-4 text-[var(--text-secondary)]">{ex.totalFetched ?? "-"}</td>
                    <td className="py-2.5 pr-4 text-[var(--text-secondary)]">{ex.totalEnriched ?? "-"}</td>
                    <td className="py-2.5 pr-4 text-emerald-400">{ex.totalPushed ?? "-"}</td>
                    <td className="py-2.5 pr-4 text-red-400">{ex.totalFailed ?? "-"}</td>
                    <td className="py-2.5 pr-4 text-[var(--text-tertiary)] text-xs">
                      {formatTimestamp(ex.startedAt)}
                    </td>
                    <td className="py-2.5 text-[var(--text-tertiary)] text-xs">
                      {formatDuration(ex.startedAt, ex.completedAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-[var(--text-tertiary)]">
                {t("integrations.page_info", { current: page + 1, total: totalPages })}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-1 rounded hover:bg-[var(--bg-secondary)] disabled:opacity-30 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                  className="p-1 rounded hover:bg-[var(--bg-secondary)] disabled:opacity-30 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
