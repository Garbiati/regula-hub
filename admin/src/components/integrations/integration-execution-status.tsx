"use client";

import { useTranslations } from "next-intl";
import { CheckCircle2, XCircle, Loader2, Ban, Search, Sparkles, Send, ArrowRight } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { useIntegrationStatus } from "@/hooks/use-integration-status";
import type { IntegrationExecutionStatus as TExecutionStatus } from "@/types/integration";

type Stage = "fetching" | "enriching" | "pushing" | "complete";

const STAGES: Stage[] = ["fetching", "enriching", "pushing", "complete"];

const STAGE_META: Record<Stage, { icon: React.ReactNode; activeIcon: React.ReactNode }> = {
  fetching: {
    icon: <Search className="w-4 h-4" />,
    activeIcon: <Search className="w-4 h-4 animate-pulse" />,
  },
  enriching: {
    icon: <Sparkles className="w-4 h-4" />,
    activeIcon: <Sparkles className="w-4 h-4 animate-pulse" />,
  },
  pushing: {
    icon: <Send className="w-4 h-4" />,
    activeIcon: <Send className="w-4 h-4 animate-pulse" />,
  },
  complete: {
    icon: <CheckCircle2 className="w-4 h-4" />,
    activeIcon: <CheckCircle2 className="w-4 h-4" />,
  },
};

const STATUS_CONFIG: Record<TExecutionStatus, { icon: React.ReactNode; color: string; bg: string }> = {
  pending: {
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    color: "text-[var(--text-tertiary)]",
    bg: "bg-gray-500/10",
  },
  running: {
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    color: "text-[var(--accent-indigo)]",
    bg: "bg-[var(--accent-indigo-bg)]",
  },
  completed: {
    icon: <CheckCircle2 className="w-5 h-5" />,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  failed: {
    icon: <XCircle className="w-5 h-5" />,
    color: "text-red-400",
    bg: "bg-red-500/10",
  },
  cancelled: {
    icon: <Ban className="w-5 h-5" />,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
};

function StepIndicator({ stage, currentStage, status }: { stage: Stage; currentStage: string; status: TExecutionStatus }) {
  const t = useTranslations();
  const stageIdx = STAGES.indexOf(stage);
  const currentIdx = STAGES.indexOf(currentStage as Stage);
  const meta = STAGE_META[stage];

  const isCompleted = status === "completed" || stageIdx < currentIdx;
  const isActive = stage === currentStage && status === "running";
  const isFailed = status === "failed" && stage === currentStage;

  let stepColor = "text-[var(--text-tertiary)] opacity-40";
  let ringColor = "ring-[var(--glass-border)]";
  let bgColor = "";
  if (isCompleted) {
    stepColor = "text-emerald-400";
    ringColor = "ring-emerald-500/30";
    bgColor = "bg-emerald-500/10";
  } else if (isActive) {
    stepColor = "text-[var(--accent-indigo)]";
    ringColor = "ring-[var(--accent-indigo)]/40";
    bgColor = "bg-[var(--accent-indigo-bg)]";
  } else if (isFailed) {
    stepColor = "text-red-400";
    ringColor = "ring-red-500/30";
    bgColor = "bg-red-500/10";
  }

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className={`p-2.5 rounded-xl ring-1 ${ringColor} ${bgColor} ${stepColor} transition-all duration-300`}>
        {isActive ? meta.activeIcon : meta.icon}
      </div>
      <span className={`text-[11px] font-medium ${isCompleted || isActive ? "text-[var(--text-secondary)]" : "text-[var(--text-tertiary)] opacity-60"}`}>
        {t(`integrations.stage_${stage}`)}
      </span>
    </div>
  );
}

function StepConnector({ completed }: { completed: boolean }) {
  return (
    <div className="flex-1 flex items-center px-1 -mt-5">
      <div className={`h-[2px] w-full rounded-full transition-colors duration-500 ${completed ? "bg-emerald-400/50" : "bg-[var(--glass-border)]"}`} />
      <ArrowRight className={`w-3 h-3 shrink-0 -ml-1 transition-colors duration-500 ${completed ? "text-emerald-400/60" : "text-[var(--glass-border)]"}`} />
    </div>
  );
}

function StatCounter({ label, value, color }: { label: string; value: number | null; color?: string }) {
  return (
    <div className="text-center px-3 py-2">
      <p className={`text-xl font-bold tabular-nums ${color ?? "text-[var(--text-primary)]"}`}>{value ?? 0}</p>
      <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">{label}</p>
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
      <Card className="glass-specular">
        <CardContent className="flex items-center justify-center py-10">
          <Loader2 className="w-5 h-5 animate-spin text-[var(--text-tertiary)]" />
        </CardContent>
      </Card>
    );
  }

  const statusConfig = STATUS_CONFIG[execution.status];
  const stage = execution.progressData?.stage ?? "initializing";

  return (
    <Card className="glass-specular">
      <CardContent className="space-y-5 py-5">
        {/* Status header */}
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl ${statusConfig.bg}`}>
            <span className={statusConfig.color}>{statusConfig.icon}</span>
          </div>
          <div>
            <h3 className={`font-semibold ${statusConfig.color}`}>{t(`integrations.status_${execution.status}`)}</h3>
            {execution.status === "running" && (
              <p className="text-xs text-[var(--text-tertiary)]">
                {t(`integrations.stage_${stage}`)}
              </p>
            )}
          </div>
        </div>

        {/* Pipeline stepper */}
        {(execution.status === "running" || execution.status === "completed" || execution.status === "failed") && (
          <div className="flex items-start justify-between px-2">
            {STAGES.map((s, i) => (
              <div key={s} className="contents">
                <StepIndicator stage={s} currentStage={stage} status={execution.status} />
                {i < STAGES.length - 1 && (
                  <StepConnector completed={STAGES.indexOf(stage as Stage) > i || execution.status === "completed"} />
                )}
              </div>
            ))}
          </div>
        )}

        {/* Stat counters */}
        <div className="grid grid-cols-4 divide-x divide-[var(--glass-border)] rounded-xl bg-[var(--bg-secondary)]/40">
          <StatCounter label={t("integrations.col_fetched")} value={execution.totalFetched} />
          <StatCounter label={t("integrations.col_enriched")} value={execution.totalEnriched} color="text-[var(--accent-indigo)]" />
          <StatCounter label={t("integrations.col_pushed")} value={execution.totalPushed} color="text-emerald-400" />
          <StatCounter label={t("integrations.col_failed")} value={execution.totalFailed} color={execution.totalFailed ? "text-red-400" : undefined} />
        </div>

        {/* Error message */}
        {execution.errorMessage && (
          <div className="flex items-start gap-2.5 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
            <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-400">{execution.errorMessage}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
