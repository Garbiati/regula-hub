"use client";

import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  RefreshCw,
  User,
  LogIn,
  Search,
  ListChecks,
  GitMerge,
  Hash,
  Database,
  Filter,
  HardDriveDownload,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { PipelineNodeStatus } from "@/types/pipeline";
import type { LayoutNode } from "@/lib/pipeline-layout";

// ── Adaptive sizing helper ──

type NodeSize = "lg" | "md" | "sm";

function nodeSize(h: number): NodeSize {
  if (h >= 50) return "lg";
  if (h >= 44) return "md";
  return "sm";
}

const iconCls: Record<NodeSize, string> = { lg: "h-4 w-4", md: "h-3.5 w-3.5", sm: "h-3 w-3" };
const textCls: Record<NodeSize, string> = { lg: "text-sm", md: "text-xs", sm: "text-[11px]" };
const smallTextCls: Record<NodeSize, string> = { lg: "text-xs", md: "text-[11px]", sm: "text-[10px]" };
const countTextCls: Record<NodeSize, string> = { lg: "text-[11px]", md: "text-[10px]", sm: "text-[9px]" };

// ── Shared base wrapper for all DAG nodes (absolute positioned) ──

interface NodeBaseProps {
  node: LayoutNode;
  className?: string;
  children: React.ReactNode;
  testId: string;
}

function NodeBase({ node, className, children, testId }: NodeBaseProps) {
  return (
    <div
      className={cn(
        "absolute flex items-center gap-2 rounded-xl border transition-all duration-500",
        "bg-[var(--glass-surface)] [backdrop-filter:var(--glass-blur)] [-webkit-backdrop-filter:var(--glass-blur)]",
        "animate-dag-node-enter",
        className,
      )}
      style={{
        left: node.x,
        top: node.y,
        width: node.w,
        height: node.h,
        animationDelay: `${node.col * 100}ms`,
      }}
      data-testid={testId}
    >
      {children}
    </div>
  );
}

// ── OperatorNode (col 0) ──

interface OperatorNodeProps {
  node: LayoutNode;
  username: string;
  status: PipelineNodeStatus;
  error?: string;
  onRetry?: () => void;
}

export function OperatorNode({ node, username, status, error, onRetry }: OperatorNodeProps) {
  const t = useTranslations();
  const isActive = status === "connecting" || status === "searching";
  const size = nodeSize(node.h);

  return (
    <NodeBase
      node={node}
      testId={`pipeline-node-${username}`}
      className={cn(
        "px-3",
        status === "idle" && "border-[var(--glass-border)] opacity-60",
        isActive && "border-[var(--accent-indigo)]/40 animate-pipeline-pulse",
        status === "success" && "border-[var(--status-success)]/40 border-l-[3px] border-l-[var(--status-success)]",
        status === "error" && "border-[var(--status-danger)]/40 border-l-[3px] border-l-[var(--status-danger)]",
        status === "cancelled" && "border-[var(--glass-border)] opacity-40",
      )}
    >
      <User className={cn("shrink-0 text-[var(--text-tertiary)]", iconCls[size])} />
      <span className={cn("font-semibold text-[var(--text-primary)] truncate flex-1", textCls[size])} title={username}>
        {username}
      </span>
      {status === "error" && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 p-1 rounded-md hover:bg-[var(--status-danger)]/10 transition-colors"
          data-testid={`pipeline-retry-${username}`}
          title={error ?? t("pipeline.operator_error")}
        >
          <RefreshCw className={cn("text-[var(--status-danger)]", size === "sm" ? "h-2.5 w-2.5" : "h-3 w-3")} />
        </button>
      )}
    </NodeBase>
  );
}

// ── StepNode (col 1=login, col 2=search, col 3=results) ──

export type StepPhase = "login" | "search" | "results";

interface StepNodeProps {
  node: LayoutNode;
  phase: StepPhase;
  operatorStatus: PipelineNodeStatus;
  itemCount?: number;
}

const stepIcons: Record<StepPhase, React.ElementType> = {
  login: LogIn,
  search: Search,
  results: ListChecks,
};

function resolveStepStatus(phase: StepPhase, operatorStatus: PipelineNodeStatus): "idle" | "active" | "success" | "error" | "cancelled" {
  if (operatorStatus === "cancelled") return "cancelled";
  if (operatorStatus === "idle") return "idle";

  // On error, only the failing phase shows red — prior phases stay green
  if (operatorStatus === "error") {
    if (phase === "login") return "success"; // login must have completed for error to reach search
    if (phase === "search") return "error";
    return "error"; // results
  }

  if (phase === "login") {
    if (operatorStatus === "connecting") return "active";
    return "success"; // searching or success means login done
  }
  if (phase === "search") {
    if (operatorStatus === "connecting") return "idle";
    if (operatorStatus === "searching") return "active";
    return "success";
  }
  // results
  if (operatorStatus === "success") return "success";
  return "idle";
}

export function StepNode({ node, phase, operatorStatus, itemCount }: StepNodeProps) {
  const t = useTranslations();
  const stepStatus = resolveStepStatus(phase, operatorStatus);
  const Icon = stepIcons[phase];
  const size = nodeSize(node.h);

  const labelKey = {
    login: "pipeline.step_login",
    search: "pipeline.step_search",
    results: "pipeline.step_results",
  }[phase] as "pipeline.step_login" | "pipeline.step_search" | "pipeline.step_results";

  return (
    <NodeBase
      node={node}
      testId={`pipeline-step-${node.operator}-${phase}`}
      className={cn(
        "px-3 justify-center",
        stepStatus === "idle" && "border-[var(--glass-border)] opacity-50",
        stepStatus === "active" && "border-[var(--accent-indigo)]/40 animate-pipeline-pulse",
        stepStatus === "success" && "border-[var(--status-success)]/30",
        stepStatus === "error" && "border-[var(--status-danger)]/30 opacity-60",
        stepStatus === "cancelled" && "border-[var(--glass-border)] opacity-30",
      )}
    >
      {stepStatus === "cancelled" ? (
        <Ban className={cn("shrink-0 text-[var(--text-tertiary)]", iconCls[size])} />
      ) : stepStatus === "active" ? (
        <Loader2 className={cn("shrink-0 text-[var(--accent-indigo)] animate-spin", iconCls[size])} />
      ) : stepStatus === "success" ? (
        <CheckCircle2 className={cn("shrink-0 text-[var(--status-success)]", iconCls[size])} />
      ) : stepStatus === "error" ? (
        <XCircle className={cn("shrink-0 text-[var(--status-danger)]", iconCls[size])} />
      ) : (
        <Icon className={cn("shrink-0 text-[var(--text-tertiary)]", iconCls[size])} />
      )}
      <span
        className={cn(
          "font-medium truncate",
          smallTextCls[size],
          stepStatus === "idle" && "text-[var(--text-tertiary)]",
          stepStatus === "active" && "text-[var(--accent-indigo)]",
          stepStatus === "success" && "text-[var(--status-success)]",
          stepStatus === "error" && "text-[var(--status-danger)]",
          stepStatus === "cancelled" && "text-[var(--text-tertiary)]",
        )}
      >
        {t(labelKey)}
      </span>
      {phase === "results" && stepStatus === "success" && itemCount !== undefined && (
        <span className={cn("ml-auto font-bold text-[var(--status-success)] animate-count-up", countTextCls[size])}>
          {itemCount}
        </span>
      )}
    </NodeBase>
  );
}

// ── MergeNode (col 4) ──

interface DagMergeNodeProps {
  node: LayoutNode;
  status: "idle" | "active" | "success";
  uniqueCount: number;
}

export function DagMergeNode({ node, status, uniqueCount }: DagMergeNodeProps) {
  const size = nodeSize(node.h);
  const mergeIconCls = size === "lg" ? "h-5 w-5" : size === "md" ? "h-4 w-4" : "h-3.5 w-3.5";

  return (
    <NodeBase
      node={node}
      testId="pipeline-merge-node"
      className={cn(
        "flex-col justify-center items-center gap-1 px-3",
        status === "idle" && "border-[var(--glass-border)] opacity-50",
        status === "active" && "border-[var(--accent-indigo)]/30 animate-merge-glow",
        status === "success" && "border-[var(--status-success)]/40 animate-node-success",
      )}
    >
      {status === "active" ? (
        <Loader2 className={cn("text-[var(--accent-indigo)] animate-spin", mergeIconCls)} />
      ) : status === "success" ? (
        <GitMerge className={cn("text-[var(--status-success)]", mergeIconCls)} />
      ) : (
        <GitMerge className={cn("text-[var(--text-tertiary)]", mergeIconCls)} />
      )}
      <span className={cn("font-semibold text-[var(--text-secondary)]", countTextCls[size])}>Merge + Dedup</span>
      {status === "success" && (
        <span className={cn("font-bold text-[var(--status-success)] animate-count-up", smallTextCls[size])}>{uniqueCount}</span>
      )}
    </NodeBase>
  );
}

// ── EnrichNode (col 5 when enrichment enabled) ──

interface DagEnrichNodeProps {
  node: LayoutNode;
  status: "idle" | "active" | "success" | "partial" | "skipped";
  enrichedCount: number;
  enrichFailedCount: number;
  progress: { done: number; total: number };
}

export function DagEnrichNode({ node, status, enrichedCount, enrichFailedCount, progress }: DagEnrichNodeProps) {
  const t = useTranslations();
  const size = nodeSize(node.h);
  const enrichIconCls = size === "lg" ? "h-5 w-5" : size === "md" ? "h-4 w-4" : "h-3.5 w-3.5";
  const pct = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;
  const remaining = Math.max(0, progress.total - progress.done);

  return (
    <NodeBase
      node={node}
      testId="pipeline-enrich-node"
      className={cn(
        "flex-col justify-center items-center gap-1 px-3 overflow-hidden",
        status === "idle" && "border-[var(--glass-border)] opacity-50",
        status === "active" && "border-[var(--accent-indigo)]/30",
        status === "success" && "border-[var(--status-success)]/40 animate-node-success",
        status === "partial" && "border-[var(--status-warning)]/40",
        status === "skipped" && "border-[var(--glass-border)] opacity-30",
      )}
    >
      {/* Progress bar background — only during active */}
      {status === "active" && (
        <div
          className="absolute bottom-0 left-0 h-[3px] bg-[var(--accent-indigo)] transition-all duration-500 ease-out rounded-b-xl"
          style={{ width: `${pct}%` }}
        />
      )}

      {status === "active" ? (
        <Loader2 className={cn("text-[var(--accent-indigo)] animate-spin", enrichIconCls)} />
      ) : status === "success" ? (
        <CheckCircle2 className={cn("text-[var(--status-success)]", enrichIconCls)} />
      ) : status === "partial" ? (
        <AlertTriangle className={cn("text-[var(--status-warning)]", enrichIconCls)} />
      ) : (
        <Search className={cn("text-[var(--text-tertiary)]", enrichIconCls)} />
      )}

      <span className={cn("font-semibold text-[var(--text-secondary)]", countTextCls[size])}>
        {t("pipeline.step_enrich")}
      </span>
      {status === "active" ? (
        <div className="flex flex-col items-center gap-0.5">
          <span className={cn("font-bold text-[var(--accent-indigo)] tabular-nums", countTextCls[size])}>
            {progress.done}/{progress.total}
          </span>
          <div className={cn("flex items-center gap-1.5 tabular-nums", smallTextCls[size])}>
            {enrichedCount > 0 && (
              <span className="text-[var(--status-success)]">{enrichedCount} ok</span>
            )}
            {enrichFailedCount > 0 && (
              <span className="text-[var(--status-danger)]">{enrichFailedCount} err</span>
            )}
            {remaining > 0 && (
              <span className="text-[var(--text-tertiary)]">{remaining} left</span>
            )}
          </div>
        </div>
      ) : (status === "success" || status === "partial") ? (
        <span className={cn(
          "font-bold animate-count-up",
          status === "success" ? "text-[var(--status-success)]" : "text-[var(--status-warning)]",
          smallTextCls[size],
        )}>
          {enrichedCount}/{progress.total}
        </span>
      ) : null}
    </NodeBase>
  );
}

// ── CacheNode ──

interface DagCacheNodeProps {
  node: LayoutNode;
  status: "idle" | "loading" | "done" | "skipped";
  cachedCount: number;
}

export function DagCacheNode({ node, status, cachedCount }: DagCacheNodeProps) {
  const t = useTranslations();
  const size = nodeSize(node.h);
  const iconCl = size === "lg" ? "h-5 w-5" : size === "md" ? "h-4 w-4" : "h-3.5 w-3.5";

  return (
    <NodeBase
      node={node}
      testId="pipeline-cache-node"
      className={cn(
        "flex-col justify-center items-center gap-1 px-3",
        status === "idle" && "border-[var(--glass-border)] opacity-50",
        status === "loading" && "border-[var(--accent-indigo)]/30 animate-pipeline-pulse",
        status === "done" && "border-[var(--status-success)]/40 animate-node-success",
        status === "skipped" && "border-[var(--glass-border)] opacity-30",
      )}
    >
      {status === "loading" ? (
        <Loader2 className={cn("text-[var(--accent-indigo)] animate-spin", iconCl)} />
      ) : status === "done" ? (
        <Database className={cn("text-[var(--status-success)]", iconCl)} />
      ) : (
        <Database className={cn("text-[var(--text-tertiary)]", iconCl)} />
      )}
      <span className={cn("font-semibold text-[var(--text-secondary)]", countTextCls[size])}>
        {t("pipeline.step_cache")}
      </span>
      {status === "done" && (
        <span className={cn("font-bold text-[var(--status-success)] animate-count-up", smallTextCls[size])}>{cachedCount}</span>
      )}
    </NodeBase>
  );
}

// ── FilterNode ──

interface DagFilterNodeProps {
  node: LayoutNode;
  status: "idle" | "active" | "success";
  filteredCount: number;
}

export function DagFilterNode({ node, status, filteredCount }: DagFilterNodeProps) {
  const t = useTranslations();
  const size = nodeSize(node.h);
  const iconCl = size === "lg" ? "h-5 w-5" : size === "md" ? "h-4 w-4" : "h-3.5 w-3.5";

  return (
    <NodeBase
      node={node}
      testId="pipeline-filter-node"
      className={cn(
        "flex-col justify-center items-center gap-1 px-3",
        status === "idle" && "border-[var(--glass-border)] opacity-50",
        status === "active" && "border-[var(--accent-indigo)]/30 animate-merge-glow",
        status === "success" && "border-[var(--status-success)]/40 animate-node-success",
      )}
    >
      {status === "active" ? (
        <Loader2 className={cn("text-[var(--accent-indigo)] animate-spin", iconCl)} />
      ) : status === "success" ? (
        <Filter className={cn("text-[var(--status-success)]", iconCl)} />
      ) : (
        <Filter className={cn("text-[var(--text-tertiary)]", iconCl)} />
      )}
      <span className={cn("font-semibold text-[var(--text-secondary)]", countTextCls[size])}>
        {t("pipeline.step_filter")}
      </span>
      {status === "success" && (
        <span className={cn("font-bold text-[var(--status-success)] animate-count-up", smallTextCls[size])}>{filteredCount}</span>
      )}
    </NodeBase>
  );
}

// ── PersistNode ──

interface DagPersistNodeProps {
  node: LayoutNode;
  status: "idle" | "saving" | "done" | "error" | "skipped";
}

export function DagPersistNode({ node, status }: DagPersistNodeProps) {
  const t = useTranslations();
  const size = nodeSize(node.h);
  const iconCl = size === "lg" ? "h-5 w-5" : size === "md" ? "h-4 w-4" : "h-3.5 w-3.5";

  return (
    <NodeBase
      node={node}
      testId="pipeline-persist-node"
      className={cn(
        "flex-col justify-center items-center gap-1 px-3",
        status === "idle" && "border-[var(--glass-border)] opacity-50",
        status === "saving" && "border-[var(--accent-indigo)]/30 animate-pipeline-pulse",
        status === "done" && "border-[var(--status-success)]/40 animate-node-success",
        status === "error" && "border-[var(--status-warning)]/40",
        status === "skipped" && "border-[var(--glass-border)] opacity-30",
      )}
    >
      {status === "saving" ? (
        <Loader2 className={cn("text-[var(--accent-indigo)] animate-spin", iconCl)} />
      ) : status === "done" ? (
        <HardDriveDownload className={cn("text-[var(--status-success)]", iconCl)} />
      ) : status === "error" ? (
        <AlertTriangle className={cn("text-[var(--status-warning)]", iconCl)} />
      ) : (
        <HardDriveDownload className={cn("text-[var(--text-tertiary)]", iconCl)} />
      )}
      <span className={cn("font-semibold text-[var(--text-secondary)]", countTextCls[size])}>
        {t("pipeline.step_persist")}
      </span>
    </NodeBase>
  );
}

// ── FinalNode (col 5) ──

interface FinalNodeProps {
  node: LayoutNode;
  visible: boolean;
  count: number;
}

export function FinalNode({ node, visible, count }: FinalNodeProps) {
  const t = useTranslations();
  const size = nodeSize(node.h);
  const finalIconCls = size === "lg" ? "h-5 w-5" : size === "md" ? "h-4 w-4" : "h-3.5 w-3.5";
  const finalCountCls = size === "lg" ? "text-lg" : size === "md" ? "text-base" : "text-sm";

  if (!visible) {
    return (
      <NodeBase
        node={node}
        testId="pipeline-final-node"
        className="flex-col justify-center items-center border-[var(--glass-border)] opacity-30 px-3"
      >
        <Hash className={cn("text-[var(--text-tertiary)]", finalIconCls)} />
      </NodeBase>
    );
  }

  return (
    <NodeBase
      node={node}
      testId="pipeline-final-node"
      className="flex-col justify-center items-center border-[var(--status-success)]/40 bg-[var(--status-success)]/5 px-3 animate-node-success"
    >
      <span className={cn("font-bold text-[var(--status-success)] animate-count-up", finalCountCls)}>{count}</span>
      <span className={cn("font-medium text-[var(--text-tertiary)]", countTextCls[size])}>
        {t("pipeline.final_count", { count })}
      </span>
    </NodeBase>
  );
}
