import { describe, expect, it, vi } from "vitest";

import { render, screen, fireEvent } from "../test-utils";
import { PipelineModal } from "@/components/consultation/pipeline-modal";
import type { PipelineState } from "@/types/pipeline";

describe("PipelineModal", () => {
  it("does not render when closed", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "idle", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    const { container } = render(
      <PipelineModal open={false} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders modal with DAG visualization when open", () => {
    const state: PipelineState = {
      operators: [
        { username: "op1", status: "searching", itemCount: 0 },
        { username: "op2", status: "connecting", itemCount: 0 },
      ],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />);

    expect(screen.getByTestId("pipeline-modal")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-visualization")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-canvas")).toBeInTheDocument();
    // Operator nodes
    expect(screen.getByTestId("pipeline-node-op1")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-node-op2")).toBeInTheDocument();
    // Step nodes
    expect(screen.getByTestId("pipeline-step-op1-login")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-step-op1-search")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-step-op1-results")).toBeInTheDocument();
    // Merge + Final
    expect(screen.getByTestId("pipeline-merge-node")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-final-node")).toBeInTheDocument();
  });

  it("shows progress counter while searching", () => {
    const state: PipelineState = {
      operators: [
        { username: "op1", status: "success", itemCount: 5 },
        { username: "op2", status: "searching", itemCount: 0 },
        { username: "op3", status: "idle", itemCount: 0 },
      ],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />);

    expect(screen.getByTestId("pipeline-progress")).toBeInTheDocument();
    expect(screen.getByText("1/3 done")).toBeInTheDocument();
  });

  it("shows zoom controls", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "idle", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />);

    expect(screen.getByTestId("pipeline-zoom-in")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-zoom-out")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-zoom-reset")).toBeInTheDocument();
  });

  it("shows confirm button when all operators complete successfully", () => {
    const state: PipelineState = {
      operators: [
        { username: "op1", status: "success", itemCount: 15 },
        { username: "op2", status: "success", itemCount: 20 },
      ],
      mergeStatus: "success",
      uniqueCount: 32,
      isComplete: true,
      isCancelled: false,
    };
    const onConfirm = vi.fn();
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={onConfirm} onCancel={() => {}} />);

    expect(screen.getByText("All operators completed successfully")).toBeInTheDocument();
    expect(screen.getByText("35 items found, 32 unique after deduplication")).toBeInTheDocument();

    const confirmBtn = screen.getByTestId("pipeline-confirm-btn");
    fireEvent.click(confirmBtn);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("shows failed operators with retry buttons on partial failure", () => {
    const state: PipelineState = {
      operators: [
        { username: "op1", status: "success", itemCount: 15 },
        { username: "op-fail", status: "error", itemCount: 0, error: "SisReg login failed" },
        { username: "op-fail2", status: "error", itemCount: 0, error: "Connection timeout" },
      ],
      mergeStatus: "success",
      uniqueCount: 15,
      isComplete: true,
      isCancelled: false,
    };
    const onRetry = vi.fn();
    render(<PipelineModal open={true} state={state} onRetryOperator={onRetry} onConfirm={() => {}} onCancel={() => {}} />);

    // Shows partial failure message
    expect(screen.getByText("1 of 3 operators succeeded")).toBeInTheDocument();

    // Shows failed operators section with details
    expect(screen.getByText("Failed operators")).toBeInTheDocument();
    expect(screen.getAllByText("op-fail").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("SisReg login failed").length).toBeGreaterThanOrEqual(1);

    // Retry buttons in the footer section
    const retryButtons = screen.getAllByText("Retry");
    expect(retryButtons.length).toBeGreaterThanOrEqual(2);

    // Click retry on footer retry button
    fireEvent.click(screen.getByTestId("pipeline-footer-retry-op-fail"));
    expect(onRetry).toHaveBeenCalledWith("op-fail");
  });

  it("shows view results button with unique count", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "success", itemCount: 10 }],
      mergeStatus: "success",
      uniqueCount: 10,
      isComplete: true,
      isCancelled: false,
    };
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />);

    expect(screen.getByText("View 10 results")).toBeInTheDocument();
  });

  it("shows retry button on operator node in DAG when error", () => {
    const state: PipelineState = {
      operators: [{ username: "op-err", status: "error", itemCount: 0, error: "Timeout" }],
      mergeStatus: "success",
      uniqueCount: 0,
      isComplete: true,
      isCancelled: false,
    };
    const onRetry = vi.fn();
    render(<PipelineModal open={true} state={state} onRetryOperator={onRetry} onConfirm={() => {}} onCancel={() => {}} />);

    // Retry button on the operator node in the DAG
    const dagRetry = screen.getByTestId("pipeline-retry-op-err");
    fireEvent.click(dagRetry);
    expect(onRetry).toHaveBeenCalledWith("op-err");
  });

  it("calls onCancel when cancel button is clicked", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "searching", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    const onCancel = vi.fn();
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={onCancel} />);

    const cancelBtn = screen.getByTestId("pipeline-cancel-btn");
    fireEvent.click(cancelBtn);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when Escape key is pressed", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "searching", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    const onCancel = vi.fn();
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={onCancel} />);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when backdrop is clicked", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "searching", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    const onCancel = vi.fn();
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={onCancel} />);

    // The backdrop is the first child inside the modal container
    const modal = screen.getByTestId("pipeline-modal");
    const backdrop = modal.querySelector(".bg-black\\/25");
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop!);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("does not show footer when cancelled", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "cancelled", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: true,
      isCancelled: true,
    };
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />);

    expect(screen.queryByTestId("pipeline-confirm-btn")).not.toBeInTheDocument();
  });

  it("has role=dialog and aria-modal attributes", () => {
    const state: PipelineState = {
      operators: [{ username: "op1", status: "idle", itemCount: 0 }],
      mergeStatus: "idle",
      uniqueCount: 0,
      isComplete: false,
      isCancelled: false,
    };
    render(<PipelineModal open={true} state={state} onRetryOperator={() => {}} onConfirm={() => {}} onCancel={() => {}} />);

    const modal = screen.getByTestId("pipeline-modal");
    expect(modal).toHaveAttribute("role", "dialog");
    expect(modal).toHaveAttribute("aria-modal", "true");
  });
});
