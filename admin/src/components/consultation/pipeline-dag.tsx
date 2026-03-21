"use client";

import { useMemo } from "react";

import { computeDagLayout } from "@/lib/pipeline-layout";
import type { PipelineState, PipelineNodeStatus } from "@/types/pipeline";
import { PipelineCanvas } from "./pipeline-canvas";
import { PipelineEdge, type EdgeStatus } from "./pipeline-edge";
import { OperatorNode, StepNode, DagMergeNode, DagFilterNode, DagCacheNode, DagPersistNode, DagEnrichNode, FinalNode, type StepPhase } from "./pipeline-node";

interface PipelineDagProps {
  state: PipelineState;
  onRetryOperator: (username: string) => void;
  enrichEnabled?: boolean;
  cacheEnabled?: boolean;
}

// ── Edge status resolution ──

function resolveEdgeStatus(
  edgeId: string,
  state: PipelineState,
): EdgeStatus {
  const { operators, mergeStatus, filterStatus, enrichStatus, cacheStatus, persistStatus } = state;

  // cache → merge edge
  if (edgeId === "cache->merge") {
    if (cacheStatus === "done") return "success";
    if (cacheStatus === "loading") return "connecting";
    return "idle";
  }

  // merge → filter edge
  if (edgeId === "merge->filter") {
    if (filterStatus === "success") return "success";
    if (mergeStatus === "success") return "success";
    return "idle";
  }

  // filter → enrich edge
  if (edgeId === "filter->enrich") {
    if (["success", "partial", "active", "skipped"].includes(enrichStatus)) return "success";
    if (filterStatus === "success") return "success";
    return "idle";
  }

  // enrich → persist edge
  if (edgeId === "enrich->persist") {
    if (persistStatus !== "idle") return "success";
    if (enrichStatus === "success" || enrichStatus === "partial" || enrichStatus === "skipped") return "success";
    return "idle";
  }

  // filter → persist edge (when no enrich)
  if (edgeId === "filter->persist") {
    if (persistStatus !== "idle") return "success";
    if (filterStatus === "success") return "success";
    return "idle";
  }

  // *->final edges
  if (edgeId.endsWith("->final")) {
    const from = edgeId.replace("->final", "");
    if (from === "enrich") {
      if (enrichStatus === "success" || enrichStatus === "partial" || enrichStatus === "skipped") return "success";
      if (enrichStatus === "active") return "searching";
      return "idle";
    }
    if (from === "persist") {
      if (persistStatus === "done" || persistStatus === "error") return "success";
      if (persistStatus === "saving") return "searching";
      return "idle";
    }
    if (from === "filter") {
      if (filterStatus === "success") return "success";
      return "idle";
    }
    if (mergeStatus === "success") return "success";
    return "idle";
  }

  // results → merge edges
  if (edgeId.endsWith("->merge") && !edgeId.startsWith("cache")) {
    const username = edgeId.replace("-results->merge", "");
    const op = operators.find((o) => o.username === username);
    if (!op) return "idle";
    if (op.status === "cancelled") return "cancelled";
    if (op.status === "success") return "success";
    if (op.status === "error") return "error";
    if (op.status === "searching") return "searching";
    if (op.status === "connecting") return "connecting";
    return "idle";
  }

  // Intra-row edges: {username}-{fromType}->{username}-{toType}
  const match = edgeId.match(/^(.+)-(operator|login|search)->(.+)-(login|search|results)$/);
  if (!match) return "idle";

  const username = match[1];
  const toType = match[4] as "login" | "search" | "results";
  const op = operators.find((o) => o.username === username);
  if (!op) return "idle";

  const s = op.status;
  if (s === "cancelled") return "cancelled";

  if (toType === "login") {
    if (s === "idle") return "idle";
    if (s === "connecting") return "connecting";
    return "success";
  }
  if (toType === "search") {
    if (s === "idle" || s === "connecting") return "idle";
    if (s === "searching") return "connecting";
    // On error, login→search edge stays success (login succeeded)
    if (s === "error") return "success";
    return "success";
  }
  // toType === "results"
  if (s === "success") return "success";
  if (s === "searching") return "searching";
  if (s === "error") return "error";
  return "idle";
}

export function PipelineDag({ state, onRetryOperator, enrichEnabled = false, cacheEnabled = false }: PipelineDagProps) {
  const usernames = useMemo(() => state.operators.map((op) => op.username), [state.operators]);
  const layout = useMemo(() => computeDagLayout(usernames, enrichEnabled, cacheEnabled), [usernames, enrichEnabled, cacheEnabled]);

  const operators = state.operators;
  const opMap = useMemo(() => {
    const m = new Map<string, (typeof operators)[number]>();
    for (const op of operators) {
      m.set(op.username, op);
    }
    return m;
  }, [operators]);

  const finalCount = state.filteredCount;
  // Last stage before final: persist (if cache) > enrich (if enrich) > filter
  const lastStage = cacheEnabled ? state.persistStatus : enrichEnabled ? state.enrichStatus : state.filterStatus;
  const finalVisible = lastStage === "success" || lastStage === "partial" || lastStage === "skipped" || lastStage === "done" || lastStage === "error";

  return (
    <PipelineCanvas contentWidth={layout.totalWidth} contentHeight={layout.totalHeight}>
      {/* SVG edge layer */}
      <svg
        className="absolute inset-0 pointer-events-none"
        width={layout.totalWidth}
        height={layout.totalHeight}
        style={{ overflow: "visible" }}
      >
        {layout.edges.map((edge) => (
          <PipelineEdge
            key={edge.id}
            edge={edge}
            status={resolveEdgeStatus(edge.id, state)}
            compact={layout.nodeH < 50}
          />
        ))}
      </svg>

      {/* Node layer */}
      {layout.nodes.map((node) => {
        if (node.type === "operator") {
          const op = opMap.get(node.operator);
          const status: PipelineNodeStatus = op?.status ?? "idle";
          return (
            <OperatorNode
              key={node.id}
              node={node}
              username={node.operator}
              status={status}
              error={op?.error}
              onRetry={status === "error" ? () => onRetryOperator(node.operator) : undefined}
            />
          );
        }

        if (node.type === "login" || node.type === "search" || node.type === "results") {
          const op = opMap.get(node.operator);
          const operatorStatus: PipelineNodeStatus = op?.status ?? "idle";
          return (
            <StepNode
              key={node.id}
              node={node}
              phase={node.type as StepPhase}
              operatorStatus={operatorStatus}
              itemCount={op?.itemCount}
            />
          );
        }

        if (node.type === "cache") {
          return (
            <DagCacheNode
              key={node.id}
              node={node}
              status={state.cacheStatus}
              cachedCount={state.cachedCount}
            />
          );
        }

        if (node.type === "merge") {
          return (
            <DagMergeNode
              key={node.id}
              node={node}
              status={state.mergeStatus}
              uniqueCount={state.uniqueCount}
            />
          );
        }

        if (node.type === "filter") {
          return (
            <DagFilterNode
              key={node.id}
              node={node}
              status={state.filterStatus}
              filteredCount={state.filteredCount}
            />
          );
        }

        if (node.type === "persist") {
          return (
            <DagPersistNode
              key={node.id}
              node={node}
              status={state.persistStatus}
            />
          );
        }

        if (node.type === "enrich") {
          return (
            <DagEnrichNode
              key={node.id}
              node={node}
              status={state.enrichStatus}
              enrichedCount={state.enrichedCount}
              progress={state.enrichProgress}
            />
          );
        }

        if (node.type === "final") {
          return (
            <FinalNode
              key={node.id}
              node={node}
              visible={finalVisible}
              count={finalCount}
            />
          );
        }

        return null;
      })}
    </PipelineCanvas>
  );
}
