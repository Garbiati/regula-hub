"use client";

import { useTranslations } from "next-intl";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

export interface OperatorStatus {
  username: string;
  status: "pending" | "loading" | "success" | "error";
  rowCount?: number;
  error?: string;
}

export interface ExportPipelineStatusProps {
  operators: OperatorStatus[];
  totalRows: number;
  isComplete: boolean;
}

export function ExportPipelineStatus({ operators, totalRows, isComplete }: ExportPipelineStatusProps) {
  const t = useTranslations();

  if (operators.length === 0) return null;

  return (
    <div className="glass-card p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[var(--text-primary)]">
          {t("agendamentos.pipeline_title")}
        </span>
        {isComplete && (
          <span className="text-xs text-[var(--text-secondary)]">
            {totalRows} {t("agendamentos.total_records")}
          </span>
        )}
      </div>
      <div className="space-y-1">
        {operators.map((op) => (
          <div key={op.username} className="flex items-center gap-2 text-xs">
            {op.status === "loading" && <Loader2 className="h-3 w-3 animate-spin text-blue-500" />}
            {op.status === "success" && <CheckCircle2 className="h-3 w-3 text-green-500" />}
            {op.status === "error" && <XCircle className="h-3 w-3 text-red-500" />}
            {op.status === "pending" && <div className="h-3 w-3 rounded-full bg-gray-300" />}
            <span className="font-mono text-[var(--text-secondary)]">{op.username}</span>
            {op.status === "success" && op.rowCount !== undefined && (
              <span className="text-[var(--text-tertiary)]">({op.rowCount} rows)</span>
            )}
            {op.status === "error" && op.error && (
              <span className="text-red-500">{op.error}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
