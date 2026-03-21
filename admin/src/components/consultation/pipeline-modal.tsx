"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { ArrowRight, CheckCircle2, AlertTriangle, Zap, X } from "lucide-react";

import { cn } from "@/lib/utils";
import type { PipelineState } from "@/types/pipeline";
import { PipelineDag } from "./pipeline-dag";

interface PipelineModalProps {
  open: boolean;
  state: PipelineState;
  onRetryOperator: (username: string) => void;
  onRetryEnrichment?: () => void;
  onConfirm: () => void;
  onCancel: () => void;
  enrichEnabled?: boolean;
  cacheEnabled?: boolean;
}

export function PipelineModal({ open, state, onRetryOperator, onRetryEnrichment, onConfirm, onCancel, enrichEnabled, cacheEnabled }: PipelineModalProps) {
  const t = useTranslations();

  // Escape key handler
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  const successOps = state.operators.filter((op) => op.status === "success");
  const errorOps = state.operators.filter((op) => op.status === "error");
  const totalItems = successOps.reduce((sum, op) => sum + op.itemCount, 0);
  const hasErrors = errorOps.length > 0;
  const hasRetrying = state.operators.some((op) => op.status === "connecting" || op.status === "searching")
    || state.enrichStatus === "active";
  const doneCount = state.operators.filter((op) => op.status === "success" || op.status === "error").length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center animate-backdrop-in"
      data-testid="pipeline-modal"
      role="dialog"
      aria-modal="true"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/25 [backdrop-filter:blur(12px)] [-webkit-backdrop-filter:blur(12px)]"
        onClick={onCancel}
      />

      {/* Modal — wider for DAG canvas */}
      <div
        className={cn(
          "relative z-10 w-full sm:max-w-3xl md:max-w-4xl lg:max-w-5xl xl:max-w-6xl mx-2 sm:mx-4 rounded-2xl sm:rounded-[var(--radius-modal)] overflow-hidden flex flex-col",
          "bg-[var(--glass-surface-strong)] [backdrop-filter:var(--glass-blur-strong)] [-webkit-backdrop-filter:var(--glass-blur-strong)]",
          "border border-[var(--glass-border)] shadow-[var(--glass-shadow-floating)]",
          "animate-slide-in-scale",
          // Height: fullscreen on mobile, responsive breakpoints on desktop
          "h-[calc(100vh-16px)] sm:h-[480px] md:h-[520px] lg:h-[560px] xl:h-[600px] max-h-[90vh]",
        )}
      >
        {/* ── Header (compact) ── */}
        <div className="flex items-center gap-3 px-6 pt-3 pb-2 shrink-0">
          <div className="flex items-center justify-center w-8 h-8 rounded-2xl bg-[var(--accent-indigo-bg)]">
            <Zap className="h-4 w-4 text-[var(--accent-indigo)]" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[var(--text-primary)]">{t("pipeline.modal_title")}</h2>
            <p className="text-xs text-[var(--text-tertiary)]">
              {t("pipeline.modal_subtitle", { count: state.operators.length })}
            </p>
          </div>

          <div className="ml-auto flex items-center gap-3">
            {/* Progress counter */}
            {!state.isComplete && (
              <div className="flex items-center gap-2" data-testid="pipeline-progress">
                <div className="w-2 h-2 rounded-full bg-[var(--accent-indigo)] animate-pulse" />
                <span className="text-xs font-medium text-[var(--accent-indigo)]">
                  {t("pipeline.progress", { done: doneCount, total: state.operators.length })}
                </span>
              </div>
            )}
            {/* Cancel/Close button (X) */}
            <button
              type="button"
              onClick={onCancel}
              className="p-1.5 rounded-lg hover:bg-[var(--glass-surface-hover)] transition-colors"
              aria-label={state.isComplete ? t("common.close") : t("pipeline.cancel_search")}
              data-testid="pipeline-cancel-btn"
            >
              <X className="h-4 w-4 text-[var(--text-tertiary)]" />
            </button>
          </div>
        </div>

        {/* ── DAG canvas (flex-1 fills remaining space) ── */}
        <div className="flex flex-col flex-1 min-h-0 px-4 sm:px-6 pb-2" data-testid="pipeline-visualization">
          <PipelineDag state={state} onRetryOperator={onRetryOperator} enrichEnabled={enrichEnabled} cacheEnabled={cacheEnabled} />
        </div>

        {/* ── Completion footer (overlay — does not push canvas) ── */}
        {state.isComplete && !state.isCancelled && (
          <div className="absolute bottom-0 left-0 right-0 px-6 pb-5 pt-2 z-20">
            <div
              className={cn(
                "rounded-2xl border p-4 animate-slide-in-scale",
                "bg-[var(--glass-surface-strong)] [backdrop-filter:var(--glass-blur-strong)] [-webkit-backdrop-filter:var(--glass-blur-strong)]",
                hasErrors
                  ? "border-[var(--status-warning)]/30"
                  : "border-[var(--status-success)]/30",
              )}
              style={{ animationDelay: "200ms" }}
            >
              {/* Summary row */}
              <div className="flex items-center gap-3 mb-3">
                {hasErrors ? (
                  <AlertTriangle className="h-5 w-5 text-[var(--status-warning)] shrink-0" />
                ) : (
                  <CheckCircle2 className="h-5 w-5 text-[var(--status-success)] shrink-0" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {hasErrors
                      ? t("pipeline.summary_partial", { success: successOps.length, total: state.operators.length })
                      : t("pipeline.summary_success")}
                  </p>
                  <p className="text-xs text-[var(--text-tertiary)]">
                    {t("pipeline.summary_detail", { total: totalItems, unique: state.uniqueCount })}
                    {state.droppedCount > 0 && (
                      <span className="ml-1">
                        ({t("pipeline.dropped_rows", { count: state.droppedCount })})
                      </span>
                    )}
                    {state.cachedCount > 0 && (
                      <span className="ml-1">
                        ({t("pipeline.cache_loaded", { count: state.cachedCount })})
                      </span>
                    )}
                    {enrichEnabled && state.enrichProgress.total > 0 && state.enrichProgress.total < state.uniqueCount && (
                      <span className="ml-1">
                        ({t("pipeline.enrich_unique_cns", { count: state.enrichProgress.total })})
                      </span>
                    )}
                  </p>
                </div>
              </div>

              {/* Failed operators detail */}
              {hasErrors && (
                <div className="space-y-2 mb-3">
                  <p className="text-xs font-semibold text-[var(--status-danger)] uppercase tracking-wider">
                    {t("pipeline.failed_operators")}
                  </p>
                  {errorOps.map((op) => (
                    <div
                      key={op.username}
                      className="flex items-center justify-between py-2 px-3 rounded-xl bg-[var(--status-danger)]/5 border border-[var(--status-danger)]/15"
                    >
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-[var(--text-primary)]">{op.username}</span>
                        <span className="text-[11px] text-[var(--status-danger)]">{op.error ?? t("pipeline.operator_error")}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => onRetryOperator(op.username)}
                        disabled={hasRetrying}
                        className={cn(
                          "px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-200",
                          "bg-[var(--accent-indigo)] text-white",
                          "hover:bg-[var(--accent-indigo-light)] hover:scale-105 active:scale-95",
                          "hover:shadow-[0_4px_16px_rgba(88,86,214,0.3)]",
                          "disabled:opacity-50 disabled:cursor-not-allowed",
                        )}
                        data-testid={`pipeline-footer-retry-${op.username}`}
                      >
                        {t("pipeline.operator_retry")}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Enrichment partial warning */}
              {state.enrichStatus === "partial" && state.enrichFailedCount > 0 && (
                <div className="flex items-center justify-between py-2 px-3 rounded-xl bg-[var(--status-warning)]/5 border border-[var(--status-warning)]/15 mb-3">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-[var(--text-primary)]">
                      {t("pipeline.enrich_partial", { found: state.enrichedCount, failed: state.enrichFailedCount })}
                    </span>
                    <span className="text-[11px] text-[var(--status-warning)]">
                      {t("pipeline.enrich_partial_detail")}
                    </span>
                  </div>
                  {onRetryEnrichment && (
                    <button
                      type="button"
                      onClick={onRetryEnrichment}
                      disabled={hasRetrying}
                      className={cn(
                        "px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-200",
                        "bg-[var(--accent-indigo)] text-white",
                        "hover:bg-[var(--accent-indigo-light)] hover:scale-105 active:scale-95",
                        "hover:shadow-[0_4px_16px_rgba(88,86,214,0.3)]",
                        "disabled:opacity-50 disabled:cursor-not-allowed",
                      )}
                      data-testid="pipeline-retry-enrich-btn"
                    >
                      {t("pipeline.operator_retry")}
                    </button>
                  )}
                </div>
              )}

              {/* Confirm button */}
              <button
                type="button"
                onClick={onConfirm}
                disabled={hasRetrying}
                className={cn(
                  "w-full flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-semibold transition-all duration-200",
                  "bg-[var(--accent-indigo)] text-white",
                  "hover:bg-[var(--accent-indigo-light)] hover:scale-[1.02] active:scale-[0.98]",
                  "hover:shadow-[0_8px_24px_rgba(88,86,214,0.3)]",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                )}
                data-testid="pipeline-confirm-btn"
              >
                <ArrowRight className="h-4 w-4" />
                {t("pipeline.view_results", { count: state.filteredCount || state.uniqueCount })}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
