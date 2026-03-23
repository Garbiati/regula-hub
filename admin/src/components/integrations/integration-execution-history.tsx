"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { History, ChevronLeft, ChevronRight, Clock } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useIntegrationHistory } from "@/hooks/use-integration-history";
import type { IntegrationExecution, IntegrationExecutionStatus } from "@/types/integration";

function StatusBadge({ status }: { status: IntegrationExecutionStatus }) {
  const t = useTranslations();
  const config: Record<IntegrationExecutionStatus, { bg: string; label: string }> = {
    pending: { bg: "bg-gray-500/10 text-gray-400 border-gray-500/20", label: t("integrations.status_pending") },
    running: { bg: "bg-blue-500/10 text-blue-400 border-blue-500/20", label: t("integrations.status_running") },
    completed: { bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", label: t("integrations.status_completed") },
    failed: { bg: "bg-red-500/10 text-red-400 border-red-500/20", label: t("integrations.status_failed") },
    cancelled: { bg: "bg-amber-500/10 text-amber-400 border-amber-500/20", label: t("integrations.status_cancelled") },
  };
  const c = config[status] ?? config.pending;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${c.bg}`}>
      {c.label}
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
    <Card className="glass-specular">
      <CardHeader>
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[var(--accent-indigo)]" />
          <CardTitle>{t("integrations.history_title")}</CardTitle>
          {total > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-[var(--accent-indigo-bg)] text-[var(--accent-indigo)] text-[10px] font-bold">
              {total}
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="py-8 text-center text-[var(--text-tertiary)] text-sm">{t("integrations.loading")}</div>
        ) : items.length === 0 ? (
          <div className="py-10 text-center">
            <Clock className="w-10 h-10 mx-auto mb-3 text-[var(--text-tertiary)] opacity-40" />
            <p className="text-sm text-[var(--text-secondary)]">{t("integrations.no_history")}</p>
            <p className="text-xs text-[var(--text-tertiary)] mt-1">{t("integrations.no_history_hint")}</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-wider text-[var(--text-tertiary)] border-b border-[var(--glass-border)]">
                    <th className="pb-2.5 pr-4 font-medium">{t("integrations.col_date_range")}</th>
                    <th className="pb-2.5 pr-4 font-medium">{t("integrations.col_status")}</th>
                    <th className="pb-2.5 pr-4 font-medium text-right">{t("integrations.col_fetched")}</th>
                    <th className="pb-2.5 pr-4 font-medium text-right">{t("integrations.col_enriched")}</th>
                    <th className="pb-2.5 pr-4 font-medium text-right">{t("integrations.col_pushed")}</th>
                    <th className="pb-2.5 pr-4 font-medium text-right">{t("integrations.col_failed")}</th>
                    <th className="pb-2.5 pr-4 font-medium">{t("integrations.col_started")}</th>
                    <th className="pb-2.5 font-medium text-right">{t("integrations.col_duration")}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((ex: IntegrationExecution) => (
                    <tr
                      key={ex.id}
                      className="border-b border-[var(--glass-border-subtle)] last:border-0 hover:bg-[var(--bg-secondary)]/40 transition-colors"
                    >
                      <td className="py-3 pr-4 font-mono text-xs text-[var(--text-primary)]">
                        {formatDateRange(ex.dateFrom, ex.dateTo)}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={ex.status} />
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-[var(--text-secondary)]">{ex.totalFetched ?? "-"}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-[var(--text-secondary)]">{ex.totalEnriched ?? "-"}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-emerald-400 font-medium">{ex.totalPushed ?? "-"}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-red-400">{ex.totalFailed || "-"}</td>
                      <td className="py-3 pr-4 text-[var(--text-tertiary)] text-xs">{formatTimestamp(ex.startedAt)}</td>
                      <td className="py-3 text-right text-[var(--text-tertiary)] text-xs font-mono">{formatDuration(ex.startedAt, ex.completedAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-3 border-t border-[var(--glass-border-subtle)]">
                <span className="text-xs text-[var(--text-tertiary)]">
                  {t("integrations.page_info", { current: page + 1, total: totalPages })}
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="p-1.5 rounded-lg hover:bg-[var(--bg-secondary)] disabled:opacity-30 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="p-1.5 rounded-lg hover:bg-[var(--bg-secondary)] disabled:opacity-30 transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
