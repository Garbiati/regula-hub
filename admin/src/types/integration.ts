export interface IntegrationEndpoint {
  id: string;
  name: string;
  protocol: string;
  httpMethod: string | null;
  path: string;
  description: string | null;
  isActive: boolean;
}

export interface IntegrationSystem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  baseUrl: string | null;
  category: string | null;
  state: string | null;
  stateName: string | null;
  endpoints: IntegrationEndpoint[];
}

export interface IntegrationSystemListResponse {
  items: IntegrationSystem[];
  total: number;
}

export type IntegrationExecutionStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface IntegrationProgress {
  stage: string;
  fetchedCount: number;
  enrichedCount: number;
  pushedCount: number;
  failedCount: number;
}

export interface IntegrationExecution {
  id: string;
  status: IntegrationExecutionStatus;
  dateFrom: string;
  dateTo: string;
  totalFetched: number | null;
  totalEnriched: number | null;
  totalPushed: number | null;
  totalFailed: number | null;
  errorMessage: string | null;
  progressData: IntegrationProgress | null;
  startedAt: string | null;
  completedAt: string | null;
  triggeredBy: string | null;
  createdAt: string | null;
}

export interface ExecutionListResponse {
  items: IntegrationExecution[];
  total: number;
}

export interface TriggerExecutionRequest {
  systemCode: string;
  dateFrom: string;
  dateTo: string;
}
