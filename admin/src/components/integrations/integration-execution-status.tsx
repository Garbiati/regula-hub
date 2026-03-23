"use client";

import { useTranslations } from "next-intl";
import { CheckCircle2, XCircle, Loader2, Ban, Search, Sparkles, Send } from "lucide-react";

import { useIntegrationStatus } from "@/hooks/use-integration-status";
import type { IntegrationExecutionStatus } from "@/types/integration";

const STAGE_ICONS: Record<string, React.ReactNode> = {
  initializing: <Loader2 className="w-4 h-4 animate-spin" />,
  fetching: <Search className="w-4 h-4" />,
  enriching: <Sparkles className="w-4 h-4" />,
  pushing: <Send className="w-4 h-4" />,
  complete: <CheckCircle2 className="w-4 h-4" />,
};

const STATUS_CONFIG: Record<
  IntegrationExecutionStatus,
  { icon: React.ReactNode; color: string; labelKey: string }
> = {
  pending: {
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    color: "text-[var(--text-tertiary)]",
    labelKey: "integrations.status_pending",
  },
  running: {
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    color: "text-[var(--accent-indigo)]",
    labelKey: "integrations.status_running",
  },
  completed: {
    icon: <CheckCircle2 className="w-5 h-5" />,
    color: "text-emerald-400",
    labelKey: "integrations.status_completed",
  },
  failed: {
    icon: <XCircle className="w-5 h-5" />,
    color: "text-red-400",
    labelKey: "integrations.status_failed",
  },
  cancelled: {
    icon: <Ban className="w-5 h-5" />,
    color: "text-amber-400",
    labelKey: "integrations.status_cancelled",
  },
};

function ProgressCounter({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold text-[var(--text-primary)]">{value ?? 0}</p>
      <p className="text-xs text-[var(--text-tertiary)]">{label}</p>
    </div>
  );
}

export interface IntegrationExecutionStatusProps {
  executionId: string;
}

export function IntegrationExecutionStatus({ executionId }: IntegrationExecutionStatusProps) {
  const { data: execution, isLoading } = useIntegrationStatus(executionId);
  const t = useTranslations();

  if (isLoading || !execution) {
    return (
      <div className="glass-card rounded-xl p-5 flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-[var(--text-tertiary)]" />
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[execution.status];
  const progress = execution.progressData;
  const stage = progress?.stage ?? "initializing";

  return (
    <div className="glass-card rounded-xl p-5 space-y-4">
      {/* Status header */}
      <div className="flex items-center gap-3">
        <span className={statusConfig.color}>{statusConfig.icon}</span>
        <div>
          <h3 className={`font-semibold ${statusConfig.color}`}>{t(statusConfig.labelKey)}</h3>
          {execution.status === "running" && (
            <p className="text-xs text-[var(--text-tertiary)] flex items-center gap-1.5">
              {STAGE_ICONS[stage]}
              {t(`integrations.stage_${stage}`)}
            </p>
          )}
        </div>
      </div>

      {/* Progress counters */}
      <div className="grid grid-cols-4 gap-4">
        <ProgressCounter label={t("integrations.col_fetched")} value={execution.totalFetched} />
        <ProgressCounter label={t("integrations.col_enriched")} value={execution.totalEnriched} />
        <ProgressCounter label={t("integrations.col_pushed")} value={execution.totalPushed} />
        <ProgressCounter label={t("integrations.col_failed")} value={execution.totalFailed} />
      </div>

      {/* Error message */}
      {execution.errorMessage && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          <p className="text-sm text-red-400">{execution.errorMessage}</p>
        </div>
      )}
    </div>
  );
}
