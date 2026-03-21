import { describe, expect, it, vi } from "vitest";

import { render, screen, fireEvent } from "../test-utils";
import { OperatorNode, StepNode, DagMergeNode, FinalNode } from "@/components/consultation/pipeline-node";
import type { LayoutNode } from "@/lib/pipeline-layout";

function makeNode(overrides: Partial<LayoutNode> = {}): LayoutNode {
  return {
    id: "test-node",
    type: "operator",
    row: 0,
    x: 0,
    y: 0,
    w: 160,
    h: 56,
    col: 0,
    operator: "op1",
    ...overrides,
  };
}

describe("OperatorNode", () => {
  it("renders with idle status", () => {
    render(<OperatorNode node={makeNode()} username="op1" status="idle" />);
    expect(screen.getByTestId("pipeline-node-op1")).toBeInTheDocument();
    expect(screen.getByText("op1")).toBeInTheDocument();
  });

  it("renders with success status and left border", () => {
    render(<OperatorNode node={makeNode()} username="op1" status="success" />);
    const el = screen.getByTestId("pipeline-node-op1");
    expect(el).toBeInTheDocument();
  });

  it("renders retry button on error", () => {
    const onRetry = vi.fn();
    render(<OperatorNode node={makeNode()} username="op1" status="error" error="Login failed" onRetry={onRetry} />);
    const retryBtn = screen.getByTestId("pipeline-retry-op1");
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("does not show retry button when no onRetry prop", () => {
    render(<OperatorNode node={makeNode()} username="op1" status="error" error="Err" />);
    expect(screen.queryByTestId("pipeline-retry-op1")).not.toBeInTheDocument();
  });

  it("applies staggered animation delay based on column", () => {
    const node = makeNode({ col: 3 });
    render(<OperatorNode node={node} username="op1" status="idle" />);
    const el = screen.getByTestId("pipeline-node-op1");
    expect(el.style.animationDelay).toBe("300ms");
  });
});

describe("StepNode", () => {
  it("renders login step in idle state", () => {
    const node = makeNode({ id: "op1-login", type: "login", col: 1 });
    render(<StepNode node={node} phase="login" operatorStatus="idle" />);
    expect(screen.getByTestId("pipeline-step-op1-login")).toBeInTheDocument();
    expect(screen.getByText("Login SisReg")).toBeInTheDocument();
  });

  it("renders search step as active when operator is searching", () => {
    const node = makeNode({ id: "op1-search", type: "search", col: 2 });
    render(<StepNode node={node} phase="search" operatorStatus="searching" />);
    expect(screen.getByTestId("pipeline-step-op1-search")).toBeInTheDocument();
  });

  it("renders results step with item count on success", () => {
    const node = makeNode({ id: "op1-results", type: "results", col: 3 });
    render(<StepNode node={node} phase="results" operatorStatus="success" itemCount={15} />);
    expect(screen.getByTestId("pipeline-step-op1-results")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
  });

  it("renders login step as success when operator is searching (login already done)", () => {
    const node = makeNode({ id: "op1-login", type: "login", col: 1 });
    render(<StepNode node={node} phase="login" operatorStatus="searching" />);
    // Should show checkmark (success state), not spinner
    expect(screen.getByTestId("pipeline-step-op1-login")).toBeInTheDocument();
  });

  it("renders error state for all steps when operator errors", () => {
    const node = makeNode({ id: "op1-search", type: "search", col: 2 });
    render(<StepNode node={node} phase="search" operatorStatus="error" />);
    expect(screen.getByTestId("pipeline-step-op1-search")).toBeInTheDocument();
  });
});

describe("DagMergeNode", () => {
  it("renders idle merge node", () => {
    const node = makeNode({ id: "merge", type: "merge", w: 140, h: 72, col: 4, operator: "" });
    render(<DagMergeNode node={node} status="idle" uniqueCount={0} />);
    expect(screen.getByTestId("pipeline-merge-node")).toBeInTheDocument();
    expect(screen.getByText("Merge + Dedup")).toBeInTheDocument();
  });

  it("renders success merge node with unique count", () => {
    const node = makeNode({ id: "merge", type: "merge", w: 140, h: 72, col: 4, operator: "" });
    render(<DagMergeNode node={node} status="success" uniqueCount={32} />);
    expect(screen.getByText("32")).toBeInTheDocument();
  });
});

describe("FinalNode", () => {
  it("renders invisible when not visible", () => {
    const node = makeNode({ id: "final", type: "final", w: 120, h: 56, col: 5, operator: "" });
    render(<FinalNode node={node} visible={false} count={0} />);
    expect(screen.getByTestId("pipeline-final-node")).toBeInTheDocument();
  });

  it("renders with count when visible", () => {
    const node = makeNode({ id: "final", type: "final", w: 120, h: 56, col: 5, operator: "" });
    render(<FinalNode node={node} visible={true} count={32} />);
    expect(screen.getByTestId("pipeline-final-node")).toBeInTheDocument();
    expect(screen.getByText("32")).toBeInTheDocument();
    expect(screen.getByText("32 unique")).toBeInTheDocument();
  });
});
