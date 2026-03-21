export type PipelineNodeStatus = "idle" | "connecting" | "searching" | "success" | "error" | "cancelled";

export type PipelineStepPhase = "login" | "search" | "results";

export interface OperatorPipelineState {
  username: string;
  status: PipelineNodeStatus;
  itemCount: number;
  error?: string;
}

export interface PipelineState {
  operators: OperatorPipelineState[];
  mergeStatus: "idle" | "active" | "success";
  filterStatus: "idle" | "active" | "success";
  enrichStatus: "idle" | "active" | "success" | "partial" | "skipped";
  cacheStatus: "idle" | "loading" | "done" | "skipped";
  cachedCount: number;
  persistStatus: "idle" | "saving" | "done" | "error" | "skipped";
  uniqueCount: number;
  droppedCount: number;
  filteredCount: number;
  enrichedCount: number;
  enrichFailedCount: number;
  enrichProgress: { done: number; total: number };
  isComplete: boolean;
  isCancelled: boolean;
}

export interface OperatorSearchResponse {
  operator: string;
  items: import("./appointment").AppointmentListing[];
  total: number;
}
