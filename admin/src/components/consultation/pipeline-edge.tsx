"use client";

import { cn } from "@/lib/utils";
import type { LayoutEdge } from "@/lib/pipeline-layout";

export type EdgeStatus = "idle" | "connecting" | "searching" | "success" | "error" | "cancelled";

interface PipelineEdgeProps {
  edge: LayoutEdge;
  status: EdgeStatus;
  /** Use thinner stroke for compact (many operators) layouts */
  compact?: boolean;
}

export function PipelineEdge({ edge, status, compact }: PipelineEdgeProps) {
  const { fromX, fromY, toX, toY } = edge;
  const dx = toX - fromX;
  const sw = compact ? 1.5 : 2;

  // Cubic bezier: horizontal first, curve in middle
  const cx1 = fromX + dx * 0.4;
  const cx2 = toX - dx * 0.4;
  const d = `M ${fromX} ${fromY} C ${cx1} ${fromY}, ${cx2} ${toY}, ${toX} ${toY}`;

  return (
    <g data-testid={`pipeline-edge-${edge.id}`}>
      {/* Background path (thicker, semi-transparent) */}
      <path
        d={d}
        fill="none"
        stroke="var(--glass-border-strong)"
        strokeWidth={sw}
        opacity={0.3}
      />

      {/* Main path */}
      <path
        d={d}
        fill="none"
        className={cn(
          "transition-all duration-500",
          status === "idle" && "stroke-[var(--glass-border-strong)] opacity-40 [stroke-dasharray:6_4]",
          status === "connecting" && "stroke-[var(--status-info)] opacity-70 [stroke-dasharray:8_4] animate-edge-dash",
          status === "searching" && "stroke-[var(--accent-indigo)] opacity-90",
          status === "success" && "stroke-[var(--status-success)] opacity-80 animate-edge-trace",
          status === "error" && "stroke-[var(--status-danger)] opacity-50",
          status === "cancelled" && "stroke-[var(--glass-border-strong)] opacity-30",
        )}
        strokeWidth={sw}
        strokeLinecap="round"
      />

      {/* Animated particle for searching status */}
      {status === "searching" && (
        <circle r={3} fill="var(--accent-indigo)" className="animate-particle-flow" opacity={0.9}>
          <animateMotion dur="1.5s" repeatCount="indefinite" path={d} />
        </circle>
      )}

      {/* Success particle trace */}
      {status === "success" && (
        <circle r={2.5} fill="var(--status-success)" opacity={0}>
          <animateMotion dur="0.8s" repeatCount="1" fill="freeze" path={d} />
          <animate attributeName="opacity" values="0;0.8;0" dur="0.8s" repeatCount="1" fill="freeze" />
        </circle>
      )}
    </g>
  );
}
